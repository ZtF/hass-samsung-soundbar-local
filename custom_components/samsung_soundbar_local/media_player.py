"""Media Player entity for Samsung Soundbar Local."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .entity import SoundbarBaseEntity
from .soundbar import AsyncSoundbar

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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the soundbar platform from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    soundbar: AsyncSoundbar = data["soundbar"]

    async_add_entities([SoundbarLocalEntity(coordinator, soundbar, entry)])


class SoundbarLocalEntity(SoundbarBaseEntity, MediaPlayerEntity):
    """Representation of the soundbar as a Media Player entity."""

    _attr_supported_features = _SUPPORTED
    _attr_source_list = _SOURCES
    _attr_sound_mode_list = _SOUND_MODES
    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_name = None

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        soundbar: AsyncSoundbar,
        entry: ConfigEntry,
    ) -> None:
        host = entry.data[CONF_HOST]
        super().__init__(coordinator, soundbar, host)
        self._attr_unique_id = f"{DOMAIN}_{host}"

    # ---------- control ----------
    async def async_turn_on(self) -> None:
        await self._soundbar.power_on()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        await self._soundbar.power_off()
        await self.coordinator.async_request_refresh()

    async def async_volume_up(self) -> None:
        await self._soundbar.volume_up()
        await self.coordinator.async_request_refresh()

    async def async_volume_down(self) -> None:
        await self._soundbar.volume_down()
        await self.coordinator.async_request_refresh()

    async def async_set_volume_level(self, volume: float) -> None:
        await self._soundbar.set_volume(round(volume * 100))
        await self.coordinator.async_request_refresh()

    async def async_mute_volume(self, mute: bool) -> None:
        if mute != self.is_volume_muted:
            await self._soundbar.mute_toggle()
            await self.coordinator.async_request_refresh()

    async def async_select_source(self, source: str) -> None:
        await self._soundbar.select_input(source)
        await self.coordinator.async_request_refresh()

    async def async_select_sound_mode(self, sound_mode: str) -> None:
        await self._soundbar.set_sound_mode(sound_mode)
        await self.coordinator.async_request_refresh()

    # ---------- properties ----------
    @property
    def state(self) -> MediaPlayerState | None:
        if self.coordinator.data is None:
            return None
        power = self.coordinator.data.get("power")
        return (
            MediaPlayerState.ON if power == "powerOn" else MediaPlayerState.OFF
        )

    @property
    def volume_level(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("volume", 0) / 100

    @property
    def is_volume_muted(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("mute", False)

    @property
    def source(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("input")

    @property
    def sound_mode(self) -> str | None:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("sound_mode")

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.coordinator.data is None:
            return None
        return {
            "codec": self.coordinator.data.get("codec"),
            "identifier": self.coordinator.data.get("identifier"),
        }
