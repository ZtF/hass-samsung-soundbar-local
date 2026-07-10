"""Button entities for Samsung Soundbar Local."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .entity import SoundbarBaseEntity
from .soundbar import AsyncSoundbar


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities from a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    soundbar: AsyncSoundbar = data["soundbar"]
    host = entry.data[CONF_HOST]

    async_add_entities(
        [
            SoundbarWooferButton(
                coordinator,
                soundbar,
                host,
                "woofer_plus",
                "Woofer +",
                soundbar.sub_plus,
            ),
            SoundbarWooferButton(
                coordinator,
                soundbar,
                host,
                "woofer_minus",
                "Woofer -",
                soundbar.sub_minus,
            ),
        ]
    )


class SoundbarWooferButton(SoundbarBaseEntity, ButtonEntity):
    """Representation of a woofer control button."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        soundbar: AsyncSoundbar,
        host: str,
        unique_suffix: str,
        label: str,
        action: Callable[[], Awaitable[None]],
    ) -> None:
        super().__init__(coordinator, soundbar, host)
        self._attr_unique_id = f"{DOMAIN}_{host}_{unique_suffix}"
        self._attr_name = label
        self._action = action

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._action()
        await self.coordinator.async_request_refresh()
