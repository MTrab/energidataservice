""" Energidataservice consts """
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

PRICE_IN = {"kWh": 1000, "MWh": 0, "Wh": 1000 * 1000}

PRICE_TYPES = sorted(list(PRICE_IN.keys()))
REGIONS = sorted(list(AREA_MAP.keys()))
CURRENCY = sorted(list(CURRENCIES.keys()))
