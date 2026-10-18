"""Config flow for the ESP32 IR Blaster integration."""

from __future__ import annotations

from typing import Any

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class Esp32IrConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Single-instance confirm flow.

    This integration has no connection of its own — it calls services on
    and listens for events from devices already set up via the stock
    ESPHome integration — so there are no fields to collect.
    """

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="ESP32 IR Blaster", data={})

        return self.async_show_form(step_id="user")
