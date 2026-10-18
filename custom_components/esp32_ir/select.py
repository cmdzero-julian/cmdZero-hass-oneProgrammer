"""Select entity listing saved IR codes, for easy picking on a dashboard."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_CODES_UPDATED
from .storage import IrCodeStore


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    store: IrCodeStore = hass.data[DOMAIN]["store"]
    async_add_entities([Esp32IrSavedCodesSelect(entry, store)])


class Esp32IrSavedCodesSelect(SelectEntity):
    """Dropdown of currently saved IR code names.

    Selecting an option just sets this entity's state — it doesn't send
    anything by itself. Pair it with the esp32_ir.send_code service in a
    script/automation, e.g. targets using `{{ states(this.entity_id) }}`.
    """

    _attr_has_entity_name = True
    _attr_name = "Saved codes"
    _attr_icon = "mdi:remote"
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, store: IrCodeStore) -> None:
        self._store = store
        self._attr_unique_id = f"{DOMAIN}_saved_codes"
        self._attr_current_option = None
        self._attr_options = sorted(store.codes)
        self._attr_device_info = None
        self._entry = entry

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_CODES_UPDATED, self._async_codes_updated
            )
        )

    @callback
    def _async_codes_updated(self) -> None:
        self._attr_options = sorted(self._store.codes)
        if self._attr_current_option not in self._attr_options:
            self._attr_current_option = None
        self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        self._attr_current_option = option
        self.async_write_ha_state()
