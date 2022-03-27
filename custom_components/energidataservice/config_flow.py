"""Config flow for Energi Data Service spot prices."""
import logging
import re

from homeassistant import config_entries
from homeassistant.helpers.template import Template

from . import DATA_SCHEMA
from .const import CONF_TEMPLATE, DEFAULT_TEMPLATE, DOMAIN

_LOGGER = logging.getLogger(__name__)


class EnergidataserviceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Energi Data Service"""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize the config flow."""
        self._errors = {}

    async def async_step_user(self, user_input=None):
        """Handle the initial config flow step."""
        self._errors = {}

        if user_input is not None:
            template_ok = False
            if user_input[CONF_TEMPLATE] in (None, ""):
                user_input[CONF_TEMPLATE] = DEFAULT_TEMPLATE
            else:
                # Check if template for additional costs is valid or not
                user_input[CONF_TEMPLATE] = re.sub(
                    r"\s{2,}", "", user_input[CONF_TEMPLATE]
                )

            template_ok = await self._validate_template(user_input[CONF_TEMPLATE])
            if template_ok:
                return self.async_create_entry(
                    title="Energi Data Service", data=user_input
                )
            else:
                self._errors["base"] = "invalid_template"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=self._errors
        )

    async def _validate_template(self, user_template):
        """Validate template to eliminate most user errors."""
        try:
            _LOGGER.debug(user_template)
            user_template = Template(user_template, self.hass).async_render()
            return bool(isinstance(user_template, float))
        except Exception as err:
            _LOGGER.error(err)

        return False

    async def async_step_import(self, user_input):  # pylint: disable=unused-argument
        """Import a config entry.
        Special type of import, we're not actually going to store any data.
        Instead, we're going to rely on the values that are in config file.
        """
        return self.async_create_entry(title="configuration.yaml", data={})
