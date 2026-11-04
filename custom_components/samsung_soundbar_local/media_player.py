"""Media Player entity for Samsung Soundbar Local."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.const import CONF_HOST, STATE_OFF, STATE_ON
from homeassistant.core import callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN
from .soundbar import AsyncSoundbar, SoundbarApiError

_LOGGER = logging.getLogger(__name__)

_SUPPORTED: MediaPlayerEntityFeature = (
    MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.SELECT_SOURCE
    | MediaPlayerEntityFeature.SELECT_SOUND_MODE
)

_SOURCES = [
    "HDMI_IN1",
    "HDMI_IN2",
    "E_ARC",
    "ARC",
    "D_IN",
    "BT",
    "WIFI_IDLE",
]

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
    """Set up the soundbar platform from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    soundbar: AsyncSoundbar = data["soundbar"]

    async_add_entities([SoundbarLocalEntity(coordinator, soundbar, entry)], True)


class SoundbarLocalEntity(CoordinatorEntity, MediaPlayerEntity):
    """Representation of the soundbar as a Media Player entity."""

    _attr_supported_features = _SUPPORTED
    _attr_source_list = _SOURCES
    _attr_sound_mode_list = _SOUND_MODES
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER

    def __init__(self, coordinator, soundbar: AsyncSoundbar, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._soundbar = soundbar
        self._entry = entry

        host = entry.data[CONF_HOST]
        self._attr_unique_id = host
        self._attr_name = f"Soundbar {host}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host)},
            manufacturer="Samsung",
            model="Soundbar",
            name=self._attr_name,
        )

    # ---------- control ----------
    async def async_turn_on(self) -> None:
        await self._soundbar.power_on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        await self._soundbar.power_off()
        await self.coordinator.async_request_refresh()

    async def async_volume_up(self) -> None:
        await self._soundbar.volume_up()
        await self._async_refresh_field("volume", self._soundbar.volume)

    async def async_volume_down(self) -> None:
        await self._soundbar.volume_down()
        await self._async_refresh_field("volume", self._soundbar.volume)

    async def async_set_volume_level(self, volume: float) -> None:
        level = round(volume * 100)
        await self._soundbar.set_volume(level)
        await self._async_refresh_field("volume", self._soundbar.volume)

    async def async_mute_volume(self, mute: bool) -> None:
        await self._soundbar.set_mute(mute)
        await self._async_refresh_field("mute", self._soundbar.is_muted)

    async def _async_refresh_field(
        self, field: str, read_value: Callable[[], Awaitable[Any]]
    ) -> None:
        """Read back a changed field without waiting for a full status poll."""
        try:
            value = await read_value()
        except (SoundbarApiError, KeyError, TypeError, ValueError):
            await self.coordinator.async_request_refresh()
        else:
            self.coordinator.async_set_updated_data({**self.coordinator.data, field: value})

    async def async_select_source(self, source: str) -> None:
        await self._soundbar.select_input(source)
        await self.coordinator.async_request_refresh()

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        await self._soundbar.set_sound_mode(sound_mode)
        await self.coordinator.async_request_refresh()

    # ---------- properties ----------
    @property
    def state(self):
        power = self.coordinator.data.get("power")
        return STATE_ON if power == "powerOn" else STATE_OFF

    @property
    def volume_level(self):
        volume = self.coordinator.data.get("volume")
        return volume / 100 if volume is not None else None

    @property
    def is_volume_muted(self):
        return self.coordinator.data.get("mute")

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
