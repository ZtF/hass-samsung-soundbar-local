"""Woofer level select entity for Samsung Soundbar Local."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_WOOFER_LEVEL, DOMAIN, WOOFER_LEVELS
from .soundbar import AsyncSoundbar, SoundbarApiError

_LOGGER = logging.getLogger(__name__)

# Delay between WOOFER_PLUS/WOOFER_MINUS key presses.
KEY_PRESS_DELAY = 0.15


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    """Set up the woofer level select entity from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [SoundbarWooferSelect(data["coordinator"], data["soundbar"], entry.data[CONF_HOST])]
    )


class SoundbarWooferSelect(CoordinatorEntity, RestoreEntity, SelectEntity):
    """Woofer level, set by stepping WOOFER_PLUS/WOOFER_MINUS.

    The local API cannot read the woofer level, so the entity tracks the last
    level it set and restores it after a restart. Changing the level with the
    physical remote or the SmartThings app makes the tracked value drift.
    """

    _attr_options = WOOFER_LEVELS
    _attr_icon = "mdi:speaker"
    _attr_assumed_state = True

    def __init__(self, coordinator, soundbar: AsyncSoundbar, host: str) -> None:
        super().__init__(coordinator)
        self._soundbar = soundbar
        self._level = DEFAULT_WOOFER_LEVEL
        self._lock = asyncio.Lock()
        self._attr_unique_id = f"{host}_woofer_level"
        self._attr_name = f"Soundbar {host} Woofer Level"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host)},
            manufacturer="Samsung",
            model="Soundbar",
            name=f"Soundbar {host}",
        )

    async def async_added_to_hass(self) -> None:
        """Restore the last level this entity set."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in WOOFER_LEVELS:
            self._level = last_state.state

    @property
    def current_option(self) -> str:
        """Return the tracked woofer level."""
        return self._level

    async def async_select_option(self, option: str) -> None:
        """Step the woofer level to the selected option."""
        if option not in WOOFER_LEVELS:
            raise HomeAssistantError(f"Invalid woofer level: {option}")

        async with self._lock:
            current = WOOFER_LEVELS.index(self._level)
            target = WOOFER_LEVELS.index(option)
            press = self._soundbar.sub_plus if target > current else self._soundbar.sub_minus
            step = 1 if target > current else -1

            try:
                for i in range(abs(target - current)):
                    if i:
                        await asyncio.sleep(KEY_PRESS_DELAY)
                    await press()
                    current += step
                    self._level = WOOFER_LEVELS[current]
            except SoundbarApiError as err:
                raise HomeAssistantError(f"Failed to set woofer level: {err}") from err
            finally:
                self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
