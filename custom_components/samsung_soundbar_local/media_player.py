"""Media Player entity for Samsung Soundbar Local."""

from __future__ import annotations

import logging

from homeassistant.components.media_player import MediaPlayerEntity
from homeassistant.components.media_player.const import (
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_SELECT_SOUND_MODE,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
)
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .soundbar import AsyncSoundbar

_LOGGER = logging.getLogger(__name__)

_SUPPORTED = (
    SUPPORT_TURN_ON
    | SUPPORT_TURN_OFF
    | SUPPORT_VOLUME_STEP
    | SUPPORT_VOLUME_SET
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_SELECT_SOURCE
    | SUPPORT_SELECT_SOUND_MODE
)

_SOURCES = ["HDMI1", "E_ARC", "ARC", "DIG", "BT", "Wifi"]
_SOUND_MODES = [
    "STANDARD",
    "SURROUND",
    "GAME",
    "MOVIE",
    "MUSIC",
    "CLEARVOICE",
    "DTS_VIRTUAL_X",
    "ADAPTIVE",
]


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    soundbar: AsyncSoundbar = data["soundbar"]

    async_add_entities([SoundbarLocalEntity(coordinator, soundbar, entry)], True)


class SoundbarLocalEntity(CoordinatorEntity, MediaPlayerEntity):
    """Representation of the soundbar as Media Player."""

    _attr_supported_features = _SUPPORTED
    _attr_source_list = _SOURCES
    _attr_sound_mode_list = _SOUND_MODES

    def __init__(self, coordinator, soundbar: AsyncSoundbar, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._soundbar = soundbar
        self._entry = entry

        host = entry.data["host"]
        self._attr_unique_id = host
        self._attr_name = f"Soundbar {host}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host)},
            manufacturer="Samsung",
            model="Soundbar",
            name=self._attr_name,
        )

    # ---------- control ----------
    async def async_turn_on(self):
        await self._soundbar.power_on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self):
        await self._soundbar.power_off()
        await self.coordinator.async_request_refresh()

    async def async_volume_up(self):
        await self._soundbar.volume_up()
        await self.coordinator.async_request_refresh()

    async def async_volume_down(self):
        await self._soundbar.volume_down()
        await self.coordinator.async_request_refresh()

    async def async_set_volume_level(self, volume: float):
        await self._soundbar.set_volume(int(volume * 100))
        await self.coordinator.async_request_refresh()

    async def async_mute_volume(self, mute: bool):
        if mute != self.is_volume_muted:
            await self._soundbar.mute_toggle()
            await self.coordinator.async_request_refresh()

    async def async_select_source(self, source: str):
        await self._soundbar.select_input(source)
        await self.coordinator.async_request_refresh()

    async def async_select_sound_mode(self, sound_mode: str):
        await self._soundbar.set_sound_mode(sound_mode)
        await self.coordinator.async_request_refresh()

    # ---------- properties ----------
    @property
    def state(self):
        power = self.coordinator.data.get("power")
        return STATE_ON if power == "powerOn" else STATE_OFF

    @property
    def volume_level(self):
        return self.coordinator.data.get("volume", 0) / 100

    @property
    def is_volume_muted(self):
        return self.coordinator.data.get("mute", False)

    @property
    def source(self):
        return self.coordinator.data.get("input")

    @property
    def sound_mode(self):
        return self.coordinator.data.get("sound_mode")

    # ---------- coordinator update ----------
    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
