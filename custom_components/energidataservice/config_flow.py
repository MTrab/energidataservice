"""Config flow for Energi Data Service spot prices."""
from __future__ import annotations

import logging
import re

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.template import Template
import voluptuous as vol

from . import async_setup_entry, async_unload_entry
from .const import (
    CONF_AREA,
    CONF_COUNTRY,
    CONF_TEMPLATE,
    DEFAULT_TEMPLATE,
    DOMAIN,
)
from .utils.configuration_schema import (
    energidataservice_config_option_initial_schema,
    energidataservice_config_option_info_schema,
)
from .utils.regionhandler import RegionHandler

_LOGGER = logging.getLogger(__name__)


class EnergidataserviceOptionsFlowHandler(config_entries.OptionsFlow):
    """Energidataservice config flow options handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize Energidataservice options flow."""
        self.config_entry = config_entry
        self._errors = {}
        # Cast from MappingProxy to dict to allow update.
        self.options = dict(config_entry.options)
        config = self.config_entry.options or self.config_entry.data
        _LOGGER.debug("Config: %s", config)

    async def async_step_init(self, user_input=None):
        """Handle options flow."""
        schema = energidataservice_config_option_info_schema(self.config_entry.options)
        country = self.config_entry.options.get(
            CONF_COUNTRY,
            RegionHandler.country_from_region(self.config_entry.options.get(CONF_AREA))
            or RegionHandler.country_from_region(
                RegionHandler.description_to_region(
                    self.config_entry.options.get(CONF_AREA)
                )
            ),
        )
        return self.async_show_form(
            step_id="region",
            data_schema=vol.Schema(schema),
            errors=self._errors,
            description_placeholders={
                "name": self.config_entry.data[CONF_NAME],
                "country": country,
            },
        )

    async def async_step_region(self, user_input=None):
        """Handle region options flow."""

        async def _do_update(_=None):
            """Update after settings change."""
            await async_unload_entry(self.hass, self.config_entry)
            await async_setup_entry(self.hass, self.config_entry)

        self._errors = {}

        if user_input is not None:
            self.options.update(user_input)
            _LOGGER.debug(self.options)
            template_ok = False
            if user_input[CONF_TEMPLATE] in (None, ""):
                user_input[CONF_TEMPLATE] = DEFAULT_TEMPLATE
            else:
                # Check if template for additional costs is valid or not
                user_input[CONF_TEMPLATE] = re.sub(
                    r"\s{2,}", "", user_input[CONF_TEMPLATE]
                )

            template_ok = await _validate_template(self.hass, user_input[CONF_TEMPLATE])
            # self._async_abort_entries_match({CONF_NAME: user_input[CONF_NAME]})
            if template_ok:
                async_call_later(self.hass, 2, _do_update)
                return self.async_create_entry(
                    title=self.options.get(CONF_NAME),
                    data=self.options,
                )
            else:
                self._errors["base"] = "invalid_template"
        schema = energidataservice_config_option_info_schema(self.config_entry.options)
        return self.async_show_form(
            step_id="region",
            data_schema=vol.Schema(schema),
            errors=self._errors,
            description_placeholders={
                "name": self.config_entry.data[CONF_NAME],
                "country": self.config_entry.options[CONF_COUNTRY],
            },
        )


class EnergidataserviceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Energi Data Service"""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> EnergidataserviceOptionsFlowHandler:
        """Get the options flow for this handler."""
        return EnergidataserviceOptionsFlowHandler(config_entry)

    def __init__(self):
        """Initialize the config flow."""
        self._errors = {}

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial config flow step."""
        self._errors = {}

        if user_input is not None:
            self.user_input = user_input
            return await self.async_step_region()

        schema = energidataservice_config_option_initial_schema()
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(schema), errors=self._errors
        )

    async def async_step_region(self, user_input=None) -> FlowResult:
        """Handle step 2, setting region and templates."""
        self._errors = {}

        if user_input is not None:
            user_input = {**user_input, **self.user_input}
            await self.async_set_unique_id(user_input[CONF_NAME])

            _LOGGER.debug(user_input)

            template_ok = False
            if user_input[CONF_TEMPLATE] in (None, ""):
                user_input[CONF_TEMPLATE] = DEFAULT_TEMPLATE
            else:
                # Check if template for additional costs is valid or not
                user_input[CONF_TEMPLATE] = re.sub(
                    r"\s{2,}", "", user_input[CONF_TEMPLATE]
                )

            template_ok = await _validate_template(self.hass, user_input[CONF_TEMPLATE])
            self._async_abort_entries_match({CONF_NAME: user_input[CONF_NAME]})
            if template_ok:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={"name": user_input[CONF_NAME]},
                    options=user_input,
                )
            else:
                self._errors["base"] = "invalid_template"

        schema = energidataservice_config_option_info_schema(self.user_input)
        return self.async_show_form(
            step_id="region",
            data_schema=vol.Schema(schema),
            errors=self._errors,
            last_step=True,
            description_placeholders={
                "name": self.user_input[CONF_NAME],
                "country": self.user_input[CONF_COUNTRY],
            },
        )

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
