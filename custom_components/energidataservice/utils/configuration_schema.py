"""Define config schema."""
# pylint: disable=dangerous-default-value
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_EMAIL, CONF_NAME

from ..const import (
    CONF_AREA,
    CONF_COUNTRY,
    CONF_CURRENCY_IN_CENT,
    CONF_DECIMALS,
    CONF_ENABLE_FORECAST,
    CONF_ENABLE_TARIFFS,
    CONF_FIXED_PRICE_VALUE,
    CONF_FIXED_PRICE_VAT,
    CONF_PRICETYPE,
    CONF_TARIFF_CHARGE_OWNER,
    CONF_TEMPLATE,
    CONF_VAT,
    UNIT_TO_MULTIPLIER,
)
from .regionhandler import RegionHandler
from .tariffhandler import TariffHandler

_LOGGER = logging.getLogger(__name__)


def list_to_str(data: list[Any]) -> str:
    """Convert an int list to a string."""
    return " ".join([str(i) for i in data])


def energidataservice_config_option_initial_schema(options: ConfigEntry = {}) -> dict:
    """Return a shcema for initial configuration options."""
    if not options:
        options = {
            CONF_NAME: "Energi Data Service",
            CONF_COUNTRY: None,
        }

    schema = {
        vol.Optional(CONF_NAME, default=options.get(CONF_NAME)): str,
        vol.Required(CONF_COUNTRY, default=options.get(CONF_COUNTRY)): vol.In(
            RegionHandler.get_countries(True)
        ),
    }

    _LOGGER.debug("Schema: %s", schema)
    return schema


def energidataservice_config_option_info_schema(options: ConfigEntry = {}) -> dict:
    """Return a schema for info configuration options."""
    _LOGGER.debug("Selected country: %s", options.get(CONF_COUNTRY))
    _LOGGER.debug("Selected area: %s", options.get(CONF_AREA))
    if options.get(CONF_COUNTRY) == "Fixed Price":
        info_options = {
            CONF_NAME: options.get(CONF_NAME),
            CONF_COUNTRY: options.get(CONF_COUNTRY) or None,
            CONF_FIXED_PRICE_VALUE: float(options.get(CONF_FIXED_PRICE_VALUE) / 1000)
            if CONF_FIXED_PRICE_VALUE in options
            else 0,
            CONF_FIXED_PRICE_VAT: float(options.get(CONF_FIXED_PRICE_VAT))
            if CONF_FIXED_PRICE_VAT in options
            else 0,
            CONF_CURRENCY_IN_CENT: options.get(CONF_CURRENCY_IN_CENT)
            if not isinstance(options.get(CONF_CURRENCY_IN_CENT), type(None))
            else False,
            CONF_DECIMALS: options.get(CONF_DECIMALS)
            if CONF_DECIMALS in options
            else 3,
            CONF_PRICETYPE: options.get(CONF_PRICETYPE)
            if CONF_PRICETYPE in options
            else "kWh",
            CONF_TEMPLATE: options.get(CONF_TEMPLATE)
            if CONF_TEMPLATE in options
            else "",
        }

        schema = {
            vol.Required(
                CONF_FIXED_PRICE_VALUE, default=info_options.get(CONF_FIXED_PRICE_VALUE)
            ): vol.Coerce(float),
            vol.Required(
                CONF_FIXED_PRICE_VAT, default=info_options.get(CONF_FIXED_PRICE_VAT)
            ): vol.Coerce(float),
            vol.Required(
                CONF_CURRENCY_IN_CENT,
                default=info_options.get(CONF_CURRENCY_IN_CENT) or False,
            ): bool,
            vol.Optional(
                CONF_DECIMALS, default=info_options.get(CONF_DECIMALS)
            ): vol.Coerce(int),
            vol.Optional(
                CONF_PRICETYPE, default=info_options.get(CONF_PRICETYPE)
            ): vol.In(list(UNIT_TO_MULTIPLIER.keys())),
            vol.Optional(CONF_TEMPLATE, default=info_options.get(CONF_TEMPLATE)): str,
        }
    else:
        _LOGGER.debug("Not Fixed Price so doing what is needed")
        info_options = {
            CONF_NAME: options.get(CONF_NAME),
            CONF_COUNTRY: (
                options.get(CONF_COUNTRY)
                or RegionHandler.country_from_region(options.get(CONF_AREA))
            )
            or RegionHandler.country_from_region(
                RegionHandler.description_to_region(options.get(CONF_AREA))
            )
            or None,
            CONF_AREA: options.get(CONF_AREA) if CONF_AREA in options else None,
            CONF_CURRENCY_IN_CENT: options.get(CONF_CURRENCY_IN_CENT)
            if not isinstance(options.get(CONF_CURRENCY_IN_CENT), type(None))
            else False,
            CONF_DECIMALS: options.get(CONF_DECIMALS)
            if CONF_DECIMALS in options
            else 3,
            CONF_PRICETYPE: options.get(CONF_PRICETYPE)
            if CONF_PRICETYPE in options
            else "kWh",
            CONF_TEMPLATE: options.get(CONF_TEMPLATE)
            if CONF_TEMPLATE in options
            else "",
            CONF_VAT: options.get(CONF_VAT)
            if not isinstance(options.get(CONF_VAT), type(None))
            else True,
        }

        schema = {
            vol.Required(CONF_AREA, default=info_options.get(CONF_AREA)): vol.In(
                RegionHandler.get_regions(info_options.get(CONF_COUNTRY), True)
            ),
            vol.Required(CONF_VAT, default=info_options.get(CONF_VAT)): bool,
            vol.Required(
                CONF_CURRENCY_IN_CENT,
                default=info_options.get(CONF_CURRENCY_IN_CENT) or False,
            ): bool,
            vol.Optional(
                CONF_DECIMALS, default=info_options.get(CONF_DECIMALS)
            ): vol.Coerce(int),
            vol.Optional(
                CONF_PRICETYPE, default=info_options.get(CONF_PRICETYPE)
            ): vol.In(list(UNIT_TO_MULTIPLIER.keys())),
            vol.Optional(CONF_TEMPLATE, default=info_options.get(CONF_TEMPLATE)): str,
        }

    _LOGGER.debug("Schema: %s", schema)
    return schema


def energidataservice_config_option_extras(
    options: ConfigEntry = {}, selections: list = ["ALL"]
) -> dict:
    """Return a schema for enabling forecasts."""
    _LOGGER.debug(options)

    if "ALL" in selections:
        selections = ["forecast", "tariff"]

    if not options:
        options = {
            CONF_ENABLE_FORECAST: False,
            CONF_ENABLE_TARIFFS: False,
        }

    schema = {}

    if "forecast" in selections:
        schema.update(
            {
                vol.Required(
                    CONF_ENABLE_FORECAST,
                    default=options.get(CONF_ENABLE_FORECAST) or False,
                ): bool
            }
        )

    if "tariff" in selections:
        schema.update(
            {
                vol.Required(
                    CONF_ENABLE_TARIFFS,
                    default=options.get(CONF_ENABLE_TARIFFS) or False,
                ): bool
            }
        )

    _LOGGER.debug("Schema: %s", schema)
    return schema


def energidataservice_config_option_carnot_credentials(
    options: ConfigEntry = {},
) -> dict:
    """Return a schema for Carnot credentials."""
    if not options:
        options = {CONF_EMAIL: None, CONF_API_KEY: None}

    schema = {
        vol.Required(CONF_EMAIL, default=options.get(CONF_EMAIL) or None): str,
        vol.Required(CONF_API_KEY, default=options.get(CONF_API_KEY) or None): str,
    }

    _LOGGER.debug("Schema: %s", schema)
    return schema


def energidataservice_config_option_tariff_settings(
    options: ConfigEntry = None,
) -> dict:
    """Return a schema for Eloverblik API configuration."""
    _LOGGER.debug("EDS options: %s", options)
    if options is None:
        options = {CONF_TARIFF_CHARGE_OWNER: None}

    schema = {
        vol.Required(
            CONF_TARIFF_CHARGE_OWNER,
            default=options.get(CONF_TARIFF_CHARGE_OWNER),
        ): vol.In(
            TariffHandler.get_chargeowners(
                RegionHandler.description_to_region(options.get(CONF_AREA)), True
            )
        ),
    }

    _LOGGER.debug("Schema: %s", schema)
    return schema
