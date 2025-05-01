"""Config flow for Samsung Soundbar Local."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_VERIFY_SSL, DOMAIN


class SoundbarLocalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Soundbar."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the step when user initiates a flow via the UI."""
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_HOST], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_VERIFY_SSL, default=False): bool,
                }
            ),
        )
