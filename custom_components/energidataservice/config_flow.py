"""Config flow for Tado integration."""
import logging

import requests.exceptions
import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.core import callback
from pydanfossally import DanfossAlly

from .const import CONF_KEY, CONF_SECRET, UNIQUE_ID
from .const import DOMAIN  # pylint:disable=unused-import

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_KEY): str, vol.Required(CONF_SECRET): str}
)


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """

    ally = DanfossAlly()
    auth = await hass.async_add_executor_job(
        ally.initialize,
        data[CONF_KEY],
        data[CONF_SECRET]
    )
    if not auth:
        raise InvalidAuth

    return {"title": f"Danfoss Ally"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Danfoss Ally."""

    VERSION = 1
    
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            try:
                validated = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if "base" not in errors:
                return self.async_create_entry(
                    title=validated['title'],
                    data=user_input
                )

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate there is invalid auth."""
