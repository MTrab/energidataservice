"""Config flow for Energi Data Service spot prices."""
import logging
import re

from homeassistant import config_entries
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.template import Template
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from .utils.configuration_schema import energidataservice_config_option_schema

from .const import CONF_TEMPLATE, DEFAULT_TEMPLATE, DOMAIN

_LOGGER = logging.getLogger(__name__)


class EnergidataserviceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Energi Data Service"""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize the config flow."""
        self._errors = {}

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial config flow step."""
        self._errors = {}

        if user_input is not None:
            template_ok = False
            name_ok = False
            if user_input[CONF_TEMPLATE] in (None, ""):
                user_input[CONF_TEMPLATE] = DEFAULT_TEMPLATE
            else:
                # Check if template for additional costs is valid or not
                user_input[CONF_TEMPLATE] = re.sub(
                    r"\s{2,}", "", user_input[CONF_TEMPLATE]
                )

            template_ok = await _validate_template(self.hass, user_input[CONF_TEMPLATE])
            name_ok = await _check_name(self.hass, user_input[CONF_NAME])
            if template_ok and name_ok:
                return self.async_create_entry(
                    title="Energi Data Service", data=user_input
                )
            elif not template_ok:
                self._errors["base"] = "invalid_template"
            elif not name_ok:
                self._errors["base"] = "invalid_name"

        schema = energidataservice_config_option_schema(user_input)
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(schema), errors=self._errors
        )

    # @staticmethod
    # @callback
    # def async_get_options_flow(config_entry):
    #     """Get the options flow for this handler."""
    #     return EnergidataserviceOptionsFlowHandler(config_entry)

    async def async_step_import(self, user_input):  # pylint: disable=unused-argument
        """Import a config entry.
        Special type of import, we're not actually going to store any data.
        Instead, we're going to rely on the values that are in config file.
        """
        return self.async_create_entry(
            title="Imported from configuration.yaml", data={}
        )


async def _validate_template(hass, user_template):
    """Validate template to eliminate most user errors."""
    try:
        _LOGGER.debug("Template:")
        _LOGGER.debug(user_template)
        user_template = Template(user_template, hass).async_render()
        return bool(isinstance(user_template, float))
    except Exception as err:
        _LOGGER.error(err)

    return False


async def _check_name(hass, name):
    """Checks if a device with the same name exists in this domain"""
    try:
        _LOGGER.debug("Device name:")
        _LOGGER.debug(name)
        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device
        _LOGGER.debug(device)

    except Exception as err:
        _LOGGER.error(err)

    return False


class EnergidataserviceOptionsFlowHandler(config_entries.OptionsFlow):
    """Energidataservice config flow options handler."""

    def __init__(self, config_entry):
        """Initialize Energidataservice options flow."""
        self.config_entry = config_entry
        self._errors = {}

    async def async_step_init(self, _user_input=None):
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        self._errors = {}

        if user_input is not None:
            template_ok = False
            name_ok = False
            if user_input[CONF_TEMPLATE] in (None, ""):
                user_input[CONF_TEMPLATE] = DEFAULT_TEMPLATE
            else:
                # Check if template for additional costs is valid or not
                user_input[CONF_TEMPLATE] = re.sub(
                    r"\s{2,}", "", user_input[CONF_TEMPLATE]
                )

            template_ok = await _validate_template(self.hass, user_input[CONF_TEMPLATE])
            name_ok = await _check_name(self.hass, user_input[CONF_NAME])
            if template_ok and name_ok:
                return self.async_create_entry(
                    title="Energi Data Service", data=user_input
                )
            elif not template_ok:
                self._errors["base"] = "invalid_template"
            elif not name_ok:
                self._errors["base"] = "invalid_name"

        schema = energidataservice_config_option_schema(user_input)

        schema = energidataservice_config_option_schema(self.config_entry.options)
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(schema), errors=self._errors
        )
