"""Persistence for named IR codes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY, STORAGE_VERSION


class IrCodeStore:
    """Wraps HA's Store helper to persist name -> raw IR code mappings."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store[dict[str, dict[str, Any]]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY
        )
        self._codes: dict[str, dict[str, Any]] = {}

    async def async_load(self) -> None:
        self._codes = await self._store.async_load() or {}

    @property
    def codes(self) -> dict[str, dict[str, Any]]:
        return self._codes

    def get(self, name: str) -> dict[str, Any] | None:
        return self._codes.get(name)

    async def async_save_code(
        self, name: str, code: list[int], source_device: str
    ) -> None:
        self._codes[name] = {
            "code": code,
            "source_device": source_device,
            "created": datetime.now(timezone.utc).isoformat(),
        }
        await self._store.async_save(self._codes)

    async def async_delete_code(self, name: str) -> bool:
        if name not in self._codes:
            return False
        del self._codes[name]
        await self._store.async_save(self._codes)
        return True
