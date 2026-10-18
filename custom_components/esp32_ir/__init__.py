"""The ESP32 IR Blaster integration.

Rides on top of the stock ESPHome integration rather than talking to
devices directly: sending calls the `send_ir_code` API service ESPHome
already exposes per sender device, and learning listens for the
`esphome.esp32_ir_code_captured` event fired by a receiver device's
`on_raw` handler (see esphome/packages/).
"""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    Event,
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.util import slugify

from .const import (
    CONF_NAME,
    CONF_OVERWRITE,
    CONF_RECEIVER_DEVICE_ID,
    CONF_TARGETS,
    CONF_TIMEOUT,
    DEFAULT_LEARN_TIMEOUT,
    DOMAIN,
    EVENT_CODE_CAPTURED,
    SERVICE_DELETE_CODE,
    SERVICE_LEARN_CODE,
    SERVICE_LIST_CODES,
    SERVICE_SEND_CODE,
    SIGNAL_CODES_UPDATED,
)
from .storage import IrCodeStore

PLATFORMS = ["select"]

LEARN_CODE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Optional(CONF_RECEIVER_DEVICE_ID): cv.string,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_LEARN_TIMEOUT): cv.positive_int,
        vol.Optional(CONF_OVERWRITE, default=False): cv.boolean,
    }
)

SEND_CODE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_TARGETS): vol.All(cv.ensure_list, [cv.string]),
    }
)

DELETE_CODE_SCHEMA = vol.Schema({vol.Required(CONF_NAME): cv.string})
LIST_CODES_SCHEMA = vol.Schema({})


def _device_slug(hass: HomeAssistant, device_id: str) -> str | None:
    """Slugify a device registry entry's name.

    ESPHome registers its per-device API services under a slug of the
    device's name, and fires learn events with its raw `name:` substitution
    value — these happen to slugify to the same thing whenever
    friendly_name mirrors name (true for our devices today), which is what
    lets us match an HA device_id to an ESPHome service/event without the
    user having to type the raw ESPHome node name anywhere.
    """
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return None
    name = device.name_by_user or device.name
    return slugify(name) if name else None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ESP32 IR Blaster from a config entry."""
    store = IrCodeStore(hass)
    await store.async_load()
    hass.data.setdefault(DOMAIN, {})["store"] = store

    async def _async_learn_code(call: ServiceCall) -> ServiceResponse:
        name = call.data[CONF_NAME]
        timeout = call.data[CONF_TIMEOUT]
        overwrite = call.data[CONF_OVERWRITE]
        receiver_device_id = call.data.get(CONF_RECEIVER_DEVICE_ID)

        if not overwrite and store.get(name) is not None:
            raise HomeAssistantError(
                f"A code named '{name}' already exists. Pass overwrite: true to replace it."
            )

        expected_slug = (
            _device_slug(hass, receiver_device_id) if receiver_device_id else None
        )

        capture: asyncio.Future[Event] = hass.loop.create_future()

        @callback
        def _on_event(event: Event) -> None:
            if expected_slug and slugify(event.data.get("device", "")) != expected_slug:
                return
            if not capture.done():
                capture.set_result(event)

        remove_listener = hass.bus.async_listen(EVENT_CODE_CAPTURED, _on_event)
        try:
            event = await asyncio.wait_for(capture, timeout=timeout)
        except TimeoutError as err:
            raise HomeAssistantError(
                f"Timed out after {timeout}s waiting for an IR code to be captured."
            ) from err
        finally:
            remove_listener()

        raw = event.data.get("code", "")
        source_device = event.data.get("device", "unknown")
        try:
            code = [int(value) for value in raw.split(",") if value]
        except ValueError as err:
            raise HomeAssistantError(f"Received malformed IR code data: {raw}") from err

        if not code:
            raise HomeAssistantError("Captured an empty IR code.")

        await store.async_save_code(name, code, source_device)
        async_dispatcher_send(hass, SIGNAL_CODES_UPDATED)

        return {"name": name, "code": code, "source_device": source_device}

    async def _async_send_code(call: ServiceCall) -> ServiceResponse:
        name = call.data[CONF_NAME]
        target_device_ids = call.data[CONF_TARGETS]

        saved = store.get(name)
        if saved is None:
            raise HomeAssistantError(f"No saved IR code named '{name}'.")
        code = saved["code"]

        results: dict[str, Any] = {}
        for device_id in target_device_ids:
            slug = _device_slug(hass, device_id)
            if slug is None:
                results[device_id] = {"success": False, "error": "Device not found"}
                continue

            service = f"{slug}_send_ir_code"
            if not hass.services.has_service("esphome", service):
                results[device_id] = {
                    "success": False,
                    "error": (
                        f"Service 'esphome.{service}' not found — is this an "
                        "IR sender device, and is it online?"
                    ),
                }
                continue

            try:
                await hass.services.async_call(
                    "esphome", service, {"code": code}, blocking=True
                )
                results[device_id] = {"success": True}
            except Exception as err:  # noqa: BLE001 - isolate failures per target
                results[device_id] = {"success": False, "error": str(err)}

        return {"name": name, "results": results}

    async def _async_delete_code(call: ServiceCall) -> ServiceResponse:
        name = call.data[CONF_NAME]
        if not await store.async_delete_code(name):
            raise HomeAssistantError(f"No saved IR code named '{name}'.")
        async_dispatcher_send(hass, SIGNAL_CODES_UPDATED)
        return {"deleted": name}

    async def _async_list_codes(call: ServiceCall) -> ServiceResponse:
        return {"codes": store.codes}

    hass.services.async_register(
        DOMAIN,
        SERVICE_LEARN_CODE,
        _async_learn_code,
        schema=LEARN_CODE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_CODE,
        _async_send_code,
        schema=SEND_CODE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_CODE,
        _async_delete_code,
        schema=DELETE_CODE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_CODES,
        _async_list_codes,
        schema=LIST_CODES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        for service in (
            SERVICE_LEARN_CODE,
            SERVICE_SEND_CODE,
            SERVICE_DELETE_CODE,
            SERVICE_LIST_CODES,
        ):
            hass.services.async_remove(DOMAIN, service)
        hass.data.pop(DOMAIN, None)
    return unloaded
