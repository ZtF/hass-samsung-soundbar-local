"""Config flow for Samsung Soundbar Local."""

from __future__ import annotations

from aiohttp import ClientError
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .const import CONF_VERIFY_SSL, DOMAIN
from .soundbar import AsyncSoundbar, SoundbarApiError


class SoundbarLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Soundbar."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the step when user initiates a flow via the UI."""
        errors = {}
        if user_input is not None:
            verify_ssl = user_input.get(CONF_VERIFY_SSL, False)
            session = aiohttp_client.async_get_clientsession(self.hass, verify_ssl=verify_ssl)
            soundbar = AsyncSoundbar(
                host=user_input[CONF_HOST], session=session, verify_ssl=verify_ssl
            )
            try:
                await soundbar.create_token()
                await soundbar.power_state()
            except (SoundbarApiError, ClientError, KeyError, TypeError, ValueError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)

        return self.async_show_form(
            step_id="user",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_VERIFY_SSL, default=False): bool,
                }
            ),
        )
