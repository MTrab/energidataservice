"""Define config schema."""
# pylint: disable=dangerous-default-value
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
import voluptuous as vol

from ..const import (
    CONF_AREA,
    CONF_DECIMALS,
    CONF_PRICETYPE,
    CONF_TEMPLATE,
    CONF_VAT,
    PRICE_TYPES,
    REGIONS,
)

_LOGGER = logging.getLogger(__name__)


def list_to_str(data: list[Any]) -> str:
    """Convert an int list to a string."""
    return " ".join([str(i) for i in data])


def energidataservice_config_option_schema(
    options: ConfigEntry = {},
) -> dict:
    """Return a shcema for HACS configuration options."""
    _LOGGER.debug("Options initial: %s", options)
    if not options:
        options = {
            CONF_NAME: "Energi Data Service",
            CONF_AREA: None,
            CONF_VAT: True,
            CONF_DECIMALS: 3,
            CONF_PRICETYPE: "kWh",
            CONF_TEMPLATE: "",
        }

    schema = {
        vol.Optional(CONF_NAME, default=options.get(CONF_NAME)): str,
        vol.Required(CONF_AREA, default=options.get(CONF_AREA)): vol.In(REGIONS),
        vol.Required(CONF_VAT, default=options.get(CONF_VAT)): bool,
        vol.Optional(CONF_DECIMALS, default=options.get(CONF_DECIMALS)): vol.Coerce(
            int
        ),
        vol.Optional(CONF_PRICETYPE, default=options.get(CONF_PRICETYPE)): vol.In(
            PRICE_TYPES
        ),
        vol.Optional(CONF_TEMPLATE, default=options.get(CONF_TEMPLATE)): str,
    }
    _LOGGER.debug("Options: %s", options[CONF_AREA])
    _LOGGER.debug("Schema: %s", schema)
    return schema
