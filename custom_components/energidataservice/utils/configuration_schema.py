"""Define config schema."""
# pylint: disable=dangerous-default-value
import voluptuous as vol

from homeassistant.const import CONF_NAME

from ..const import (
    CONF_AREA,
    REGIONS,
    CONF_VAT,
    CONF_DECIMALS,
    CONF_PRICETYPE,
    CONF_TEMPLATE,
    PRICE_TYPES,
)


def energidataservice_config_option_schema(
    options: dict = {},
) -> dict:
    """Return a shcema for HACS configuration options."""
    if not options:
        options = {
            CONF_NAME: "Energi Data Service",
            CONF_AREA: None,
            CONF_VAT: True,
            CONF_DECIMALS: 3,
            CONF_PRICETYPE: "kWh",
            CONF_TEMPLATE: "",
        }
    return {
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
