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

_CURRENCY = {
    "DKK": {
        "name": "DKK",
        "symbol": "Kr",
        "cent": "Øre",
    },
    "NOK": {
        "name": "NOK",
        "symbol": "Kr",
        "cent": "Øre",
    },
    "SEK": {
        "name": "SEK",
        "symbol": "Kr",
        "cent": "Öre",
    },
    "EUR": {
        "name": "EUR",
        "symbol": "€",
        "cent": "c",
    },
}

# Format:
#   "Region": [_CURRENCY, "Country", "Region description", VAT]
_REGIONS = {
    "DK1": [_CURRENCY["DKK"], "Denmark", "West of the great belt", 0.25],
    "DK2": [_CURRENCY["DKK"], "Denmark", "West of the great belt", 0.25],
    "FI": [_CURRENCY["EUR"], "Finland", "Finland", 0.24],
    "EE": [_CURRENCY["EUR"], "Estonia", "Estonia", 0.20],
    "LT": [_CURRENCY["EUR"], "Lithuania", "Lithuania", 0.21],
    "LV": [_CURRENCY["EUR"], "Latvia", "Latvia", 0.21],
    "NO1": [_CURRENCY["NOK"], "Norway", "Oslo", 0.25],
    "NO2": [_CURRENCY["NOK"], "Norway", "Kristiansand", 0.25],
    "NO3": [_CURRENCY["NOK"], "Norway", "Molde, Trondheim", 0.25],
    "NO4": [_CURRENCY["NOK"], "Norway", "Tromsø", 0.25],
    "NO5": [_CURRENCY["NOK"], "Norway", "Bergen", 0.25],
    "SE1": [_CURRENCY["SEK"], "Sweden", "Luleå", 0.25],
    "SE2": [_CURRENCY["SEK"], "Sweden", "Sundsvall", 0.25],
    "SE3": [_CURRENCY["SEK"], "Sweden", "Stockholm", 0.25],
    "SE4": [_CURRENCY["SEK"], "Sweden", "Malmö", 0.25],
    "FR": [_CURRENCY["EUR"], "France", "France", 0.055],
    "NL": [_CURRENCY["EUR"], "Netherlands", "Netherlands", 0.21],
    "BE": [_CURRENCY["EUR"], "Belgium", "Belgium", 0.21],
    "AT": [_CURRENCY["EUR"], "Austria", "Austria", 0.20],
    "DE": [_CURRENCY["EUR"], "Germany", "Germany", 0.19],
}

REGIONS = sorted(list(AREA_MAP.keys()))
CURRENCY = sorted(list(CURRENCIES.keys()))
