"""Base entity for Samsung Soundbar Local."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DOMAIN
from .soundbar import AsyncSoundbar


class SoundbarBaseEntity(CoordinatorEntity):
    """Common base for all soundbar entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        soundbar: AsyncSoundbar,
        host: str,
    ) -> None:
        super().__init__(coordinator)
        self._soundbar = soundbar
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host)},
            manufacturer="Samsung",
            model="Soundbar",
            name=f"Soundbar {host}",
        )
