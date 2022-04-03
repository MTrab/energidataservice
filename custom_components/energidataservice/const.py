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

AREA_DK_EAST = "East of the great belt"
AREA_DK_WEST = "West of the great belt"

DEFAULT_NAME = "Energidataservice"
DATA = "data"
UNIQUE_ID = "unique_id"
UPDATE_EDS = "eds_update"

AREA_MAP = {
    AREA_DK_WEST: "DK1",
    AREA_DK_EAST: "DK2",
}

AREA_TO_TEXT = {
    "DK1": AREA_DK_WEST,
    "DK2": AREA_DK_EAST,
}

CURRENCIES = {
    "Danske Kroner": "DKK",
    "Euro": "EUR",
}

UNIT_TO_MULTIPLIER = {"MWh": 0, "kWh": 1000, "Wh": 1000000}
MULTIPLIER_TO_UNIT = {0: "MWh", 1000: "kWh", 1000000: "Wh"}

_CENT_MULTIPLIER = 100
_CURRENTY_TO_CENTS = {"DKK": "Øre", "NOK": "Øre", "SEK": "Öre", "EUR": "c"}

_REGIONS = {
    "DK1": ["DKK", "Denmark", "West of the great belt", 0.25],
    "DK2": ["DKK", "Denmark", "West of the great belt", 0.25],
    "FI": ["EUR", "Finland", "Finland", 0.24],
    "EE": ["EUR", "Estonia", "Estonia", 0.20],
    "LT": ["EUR", "Lithuania", "Lithuania", 0.21],
    "LV": ["EUR", "Latvia", "Latvia", 0.21],
    "NO1": ["NOK", "Norway", "Oslo", 0.25],
    "NO2": ["NOK", "Norway", "Kristiansand", 0.25],
    "NO3": ["NOK", "Norway", "Molde, Trondheim", 0.25],
    "NO4": ["NOK", "Norway", "Tromsø", 0.25],
    "NO5": ["NOK", "Norway", "Bergen", 0.25],
    "SE1": ["SEK", "Sweden", "Luleå", 0.25],
    "SE2": ["SEK", "Sweden", "Sundsvall", 0.25],
    "SE3": ["SEK", "Sweden", "Stockholm", 0.25],
    "SE4": ["SEK", "Sweden", "Malmö", 0.25],
    "FR": ["EUR", "France", "France", 0.055],
    "NL": ["EUR", "Netherlands", "Netherlands", 0.21],
    "BE": ["EUR", "Belgium", "Belgium", 0.21],
    "AT": ["EUR", "Austria", "Austria", 0.20],
    "DE": ["EUR", "Germany", "Germany", 0.19],
}

REGIONS = sorted(list(AREA_MAP.keys()))
CURRENCY = sorted(list(CURRENCIES.keys()))
