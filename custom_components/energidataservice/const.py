""" Energidataservice consts """
STARTUP = """
-------------------------------------------------------------------
Energi Data Service integration

Version: %s
This is a custom integration
If you have any issues with this you need to open an issue here:
https://github.com/mtrab/energidataservice/issues
-------------------------------------------------------------------
"""

DOMAIN = "energidataservice"

CONF_AREA = "area"
CONF_VAT = "vat"
CONF_DECIMALS = "decimals"
CONF_TEMPLATE = "cost_template"
CONF_PRICETYPE = "pricetype"

DEFAULT_TEMPLATE = "{{0.0|float}}"

LIMIT = "48"

AREA_EAST = "East of the great belt"
AREA_WEST = "West of the great belt"
DEFAULT_NAME = "Energidataservice"
DATA = "data"
UNIQUE_ID = "unique_id"
UPDATE_EDS = "eds_update"

AREA_MAP = {
    AREA_WEST: "DK1",
    AREA_EAST: "DK2",
}

AREA_TO_TEXT = {
    "DK1": AREA_WEST,
    "DK2": AREA_EAST,
}

CURRENCIES = {
    "Danske Kroner": "DKK",
    "Euro": "EUR",
}

UNIT_TO_MULTIPLIER = {"MWh": 0, "kWh": 1000, "Wh": 1000000}
MULTIPLIER_TO_UNIT = {0: "MWh", 1000: "kWh", 1000000: "Wh"}

REGIONS = sorted(list(AREA_MAP.keys()))
CURRENCY = sorted(list(CURRENCIES.keys()))
