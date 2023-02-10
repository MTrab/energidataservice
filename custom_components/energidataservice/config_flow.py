"""Config flow for Energi Data Service spot prices."""
from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_utils
from jinja2 import pass_context
import voluptuous as vol

from . import async_setup_entry, async_unload_entry
from .connectors import Connectors
from .const import (
    CONF_AREA,
    CONF_COUNTRY,
    CONF_ENABLE_FORECAST,
    CONF_ENABLE_TARIFFS,
    CONF_FIXED_PRICE_VALUE,
    CONF_TEMPLATE,
    DEFAULT_TEMPLATE,
    DOMAIN,
)
from .forecasts import Forecast
from .utils.configuration_schema import (
    energidataservice_config_option_carnot_credentials,
    energidataservice_config_option_extras,
    energidataservice_config_option_info_schema,
    energidataservice_config_option_initial_schema,
    energidataservice_config_option_tariff_settings,
)
from .utils.forecasthandler import ForecastHandler
from .utils.regionhandler import RegionHandler
from .utils.tariffhandler import TariffHandler

_LOGGER = logging.getLogger(__name__)


def get_options(area) -> list:
    """Get available options for a given region."""

    options = []

    region = RegionHandler.description_to_region(area)
    tariff_connectors = TariffHandler.get_chargeowners(region)
    forecast_connectors = ForecastHandler.get_forecasts_connectors(region)

    if len(tariff_connectors) > 0:
        options.append("tariff")

    if len(forecast_connectors) > 0:
        options.append("forecast")

    return options


class EnergidataserviceOptionsFlowHandler(config_entries.OptionsFlow):
    """Energidataservice config flow options handler."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize Energidataservice options flow."""
        self.connectors = Connectors()
        self.forecasts = Forecast()
        self.config_entry = config_entry
        self._errors = {}
        # Cast from MappingProxy to dict to allow update.
        self.options = dict(config_entry.options)
        config = self.config_entry.options or self.config_entry.data
        _LOGGER.debug("Config: %s", config)
        _LOGGER.debug("Options: %s", self.options)

    def get_country(self) -> str:
        """Get country value."""
        return self.config_entry.options.get(
            CONF_COUNTRY,
            RegionHandler.country_from_region(self.config_entry.options.get(CONF_AREA))
            or RegionHandler.country_from_region(
                RegionHandler.description_to_region(
                    self.config_entry.options.get(CONF_AREA)
                )
            ),
        )

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Handle options flow."""
        schema = energidataservice_config_option_info_schema(self.config_entry.options)

        return self.async_show_form(
            step_id="region",
            data_schema=vol.Schema(schema),
            errors=self._errors,
            description_placeholders={
                "name": self.config_entry.data[CONF_NAME],
                "country": self.get_country(),
            },
        )

    async def _do_update(
        self, *args, **kwargs  # pylint: disable=unused-argument
    ) -> None:
        """Update after settings change."""
        await async_unload_entry(self.hass, self.config_entry)
        await async_setup_entry(self.hass, self.config_entry)

    async def async_step_enable_extras(
        self, user_input: Any | None = None
    ) -> FlowResult:
        """Handle extras options flow."""

        self._errors = {}
        _LOGGER.debug("Options: %s", self.options)

        if user_input is not None:
            self.options.update(user_input)
            _LOGGER.debug(
                "Forecast selected: %s",
                user_input[CONF_ENABLE_FORECAST]
                if CONF_ENABLE_FORECAST in user_input
                else "Unavailable",
            )
            _LOGGER.debug(
                "Tariffs selected: %s",
                user_input[CONF_ENABLE_TARIFFS]
                if CONF_ENABLE_TARIFFS in user_input
                else "Unavailable",
            )
            if CONF_ENABLE_FORECAST in user_input or CONF_ENABLE_TARIFFS in user_input:
                if (
                    CONF_ENABLE_FORECAST in user_input
                    and user_input[CONF_ENABLE_FORECAST]
                ):
                    creds = energidataservice_config_option_carnot_credentials(
                        self.options
                    )
                    return self.async_show_form(
                        step_id="carnot_credentials",
                        data_schema=vol.Schema(creds),
                        errors=self._errors,
                        description_placeholders={
                            "name": self.config_entry.data[CONF_NAME],
                            "country": self.get_country(),
                        },
                    )
                elif (
                    CONF_ENABLE_TARIFFS in user_input
                    and user_input[CONF_ENABLE_TARIFFS]
                ):
                    creds = energidataservice_config_option_tariff_settings(
                        self.options
                    )
                    return self.async_show_form(
                        step_id="tariff_settings",
                        data_schema=vol.Schema(creds),
                        errors=self._errors,
                        description_placeholders={
                            "name": self.config_entry.options[CONF_NAME],
                            "country": self.get_country(),
                        },
                    )
                else:
                    async_call_later(self.hass, 2, self._do_update)
                    return self.async_create_entry(
                        title=self.options.get(CONF_NAME),
                        data=self.options,
                    )
            else:
                async_call_later(self.hass, 2, self._do_update)
                return self.async_create_entry(
                    title=self.options.get(CONF_NAME),
                    data=self.options,
                )

        options = get_options(self.config_entry.options.get(CONF_AREA))
        enable_extra_schema = energidataservice_config_option_extras(
            self.config_entry.options, options
        )
        return self.async_show_form(
            step_id="enable_extras",
            data_schema=vol.Schema(enable_extra_schema),
            errors=self._errors,
            description_placeholders={
                "name": self.config_entry.options[CONF_NAME],
                "country": self.get_country(),
            },
        )

    async def async_step_carnot_credentials(
        self, user_input: Any | None = None
    ) -> FlowResult:
        """Handle Carnot credentials."""

        self._errors = {}

        if user_input is not None:
            self.options.update(user_input)
            _LOGGER.debug(self.options)

            if self.options.get(CONF_ENABLE_TARIFFS):
                creds = energidataservice_config_option_tariff_settings(self.options)
                return self.async_show_form(
                    step_id="tariff_settings",
                    data_schema=vol.Schema(creds),
                    errors=self._errors,
                    description_placeholders={
                        "name": self.options.get(CONF_NAME),
                        "country": self.options.get(CONF_COUNTRY),
                    },
                )
            else:
                async_call_later(self.hass, 2, self._do_update)
                return self.async_create_entry(
                    title=self.options.get(CONF_NAME),
                    data=self.options,
                )

        creds = energidataservice_config_option_carnot_credentials(
            self.config_entry.options
        )
        return self.async_show_form(
            step_id="carnot_credentials",
            data_schema=vol.Schema(creds),
            errors=self._errors,
            description_placeholders={
                "name": self.config_entry.data[CONF_NAME],
                "country": self.get_country(),
            },
        )

    async def async_step_tariff_settings(
        self, user_input: Any | None = None
    ) -> FlowResult:
        """Handle Tariff Settings."""
        self._errors = {}

        if user_input is not None:
            self.options.update(user_input)
            _LOGGER.debug(self.options)

            async_call_later(self.hass, 2, self._do_update)
            return self.async_create_entry(
                title=self.options.get(CONF_NAME),
                data=self.options,
            )

        _LOGGER.debug(self.config_entry.options)
        creds = energidataservice_config_option_tariff_settings(
            self.config_entry.options
        )
        return self.async_show_form(
            step_id="tariff_settings",
            data_schema=vol.Schema(creds),
            errors=self._errors,
            description_placeholders={
                "name": self.config_entry.data[CONF_NAME],
                "country": self.get_country(),
            },
        )

    async def async_step_region(self, user_input: Any | None = None) -> FlowResult:
        """Handle region options flow."""

        self._errors = {}

        if user_input is not None:
            if CONF_FIXED_PRICE_VALUE in user_input:
                user_input[CONF_FIXED_PRICE_VALUE] = (
                    user_input[CONF_FIXED_PRICE_VALUE] * 1000
                )

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
            if template_ok:
                options = get_options(self.config_entry.options.get(CONF_AREA))
                if len(options) > 0:
                    enable_extra_schema = energidataservice_config_option_extras(
                        self.options, options
                    )
                    return self.async_show_form(
                        step_id="enable_extras",
                        data_schema=vol.Schema(enable_extra_schema),
                        errors=self._errors,
                        description_placeholders={
                            "name": self.config_entry.data[CONF_NAME],
                            "country": self.get_country(),
                        },
                    )
                else:
                    async_call_later(self.hass, 2, self._do_update)
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
                "country": self.get_country(),
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

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.connectors = Connectors()
        self.forecasts = Forecast()
        self._errors = {}
        self.user_input = {}

    async def async_step_user(self, user_input: Any | None = None) -> FlowResult:
        """Handle the initial config flow step."""
        self._errors = {}

        if user_input is not None:
            self.user_input = user_input
            return await self.async_step_region()

        schema = energidataservice_config_option_initial_schema()
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(schema), errors=self._errors
        )

    async def async_step_region(self, user_input: Any | None = None) -> FlowResult:
        """Handle step 2, setting region and templates."""
        self._errors = {}

        if user_input is not None:
            if CONF_FIXED_PRICE_VALUE in user_input:
                user_input[CONF_FIXED_PRICE_VALUE] = (
                    user_input[CONF_FIXED_PRICE_VALUE] * 1000
                )

            user_input = {**user_input, **self.user_input}
            self.user_input = user_input
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
                options = get_options(self.user_input.get(CONF_AREA))
                if len(options) > 0:
                    enable_extra_schema = energidataservice_config_option_extras(
                        self.user_input, options
                    )
                    return self.async_show_form(
                        step_id="enable_extras",
                        data_schema=vol.Schema(enable_extra_schema),
                        errors=self._errors,
                        description_placeholders={
                            "name": self.user_input[CONF_NAME],
                            "country": self.user_input[CONF_COUNTRY],
                        },
                    )
                else:
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
            description_placeholders={
                "name": self.user_input[CONF_NAME],
                "country": self.user_input[CONF_COUNTRY],
            },
        )

    async def async_step_enable_extras(
        self, user_input: Any | None = None
    ) -> FlowResult:
        """Handle step 3, should we enable extras."""
        self._errors = {}

        if user_input is not None:
            user_input = {**user_input, **self.user_input}
            self.user_input = user_input
            if CONF_ENABLE_FORECAST in user_input and user_input[CONF_ENABLE_FORECAST]:
                creds = energidataservice_config_option_carnot_credentials(user_input)
                return self.async_show_form(
                    step_id="carnot_credentials",
                    data_schema=vol.Schema(creds),
                    errors=self._errors,
                    description_placeholders={
                        "name": self.user_input[CONF_NAME],
                        "country": self.user_input[CONF_COUNTRY],
                    },
                )
            elif CONF_ENABLE_TARIFFS in user_input and user_input[CONF_ENABLE_TARIFFS]:
                creds = energidataservice_config_option_tariff_settings(user_input)
                return self.async_show_form(
                    step_id="tariff_settings",
                    data_schema=vol.Schema(creds),
                    errors=self._errors,
                    description_placeholders={
                        "name": self.user_input[CONF_NAME],
                        "country": self.user_input[CONF_COUNTRY],
                    },
                )
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={"name": user_input[CONF_NAME]},
                    options=user_input,
                )

        options = get_options(self.user_input.get(CONF_AREA))
        enable_extra_schema = energidataservice_config_option_extras(
            self.user_input, options
        )
        return self.async_show_form(
            step_id="enable_extras",
            data_schema=vol.Schema(enable_extra_schema),
            errors=self._errors,
            description_placeholders={
                "name": self.user_input[CONF_NAME],
                "country": self.user_input[CONF_COUNTRY],
            },
        )

    async def async_step_carnot_credentials(
        self, user_input: Any | None = None
    ) -> FlowResult:
        """Handle Carnot credentials."""

        self._errors = {}

        if user_input is not None:
            user_input = {**user_input, **self.user_input}
            self.user_input = user_input
            if user_input[CONF_ENABLE_TARIFFS]:
                creds = energidataservice_config_option_tariff_settings(user_input)
                return self.async_show_form(
                    step_id="tariff_settings",
                    data_schema=vol.Schema(creds),
                    errors=self._errors,
                    description_placeholders={
                        "name": self.user_input[CONF_NAME],
                        "country": self.user_input[CONF_COUNTRY],
                    },
                )
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={"name": user_input[CONF_NAME]},
                    options=user_input,
                )

        creds = energidataservice_config_option_carnot_credentials(self.user_input)
        return self.async_show_form(
            step_id="carnot_credentials",
            data_schema=vol.Schema(creds),
            errors=self._errors,
            description_placeholders={
                "name": self.user_input[CONF_NAME],
                "country": self.user_input[CONF_COUNTRY],
            },
        )

    async def async_step_tariff_settings(
        self, user_input: Any | None = None
    ) -> FlowResult:
        """Handle Eloverblik credentials."""
        self._errors = {}

        if user_input is not None:
            user_input = {**user_input, **self.user_input}
            self.user_input = user_input
            _LOGGER.debug(user_input)

            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={"name": user_input[CONF_NAME]},
                options=user_input,
            )

        creds = energidataservice_config_option_tariff_settings(self.user_input)
        return self.async_show_form(
            step_id="tariff_settings",
            data_schema=vol.Schema(creds),
            errors=self._errors,
            description_placeholders={
                "name": self.user_input[CONF_NAME],
                "country": self.user_input[CONF_COUNTRY],
            },
        )

    async def async_step_import(
        self, user_input: Any | None  # pylint: disable=unused-argument
    ) -> Any:
        """Import a config entry.
        Special type of import, we're not actually going to store any data.
        Instead, we're going to rely on the values that are in config file.
        """
        return self.async_create_entry(
            title="Imported from configuration.yaml", data={}
        )


async def _validate_template(hass: HomeAssistant, user_template: Any) -> bool:
    """Validate template to eliminate most user errors."""
    try:

        def faker():
            def inner(*_, **__):
                return dt_utils.now()

            return pass_context(inner)

        _LOGGER.debug("Template:")
        _LOGGER.debug(user_template)
        user_template = Template(user_template, hass).async_render(
            now=faker(),
            current_tariff=0,
            current_price=0,
            el_afgift=0,
        )
        return bool(isinstance(user_template, float))
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.error(err)

    return False
