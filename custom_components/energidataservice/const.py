"""Energidataservice consts."""

from collections import namedtuple

STARTUP = """
-------------------------------------------------------------------
Energi Data Service integration

Version: %s
This is a custom integration
If you have any issues with this you need to open an issue here:
https://github.com/mtrab/energidataservice/issues
-------------------------------------------------------------------
"""

ATTR_CURRENT_PRICE = "current_price"
ATTR_UNIT = "unit"
ATTR_CURRENCY = "currency"
ATTR_REGION = "region"
ATTR_REGION_CODE = "region_code"
ATTR_TOMORROW_VALID = "tomorrow_valid"
ATTR_NEXT_DATA_UPDATE = "next_data_update"
ATTR_TODAY = "today"
ATTR_TOMORROW = "tomorrow"
ATTR_RAW_TODAY = "raw_today"
ATTR_RAW_TOMORROW = "raw_tomorrow"
ATTR_TODAY_MIN = "today_min"
ATTR_TODAY_MAX = "today_max"
ATTR_TODAY_MEAN = "today_mean"
ATTR_TOMORROW_MIN = "tomorrow_min"
ATTR_TOMORROW_MAX = "tomorrow_max"
ATTR_TOMORROW_MEAN = "tomorrow_mean"
ATTR_USE_CENT = "use_cent"
ATTR_ATTRIBUTION = "attribution"
ATTR_FORECAST = "forecast"
ATTR_NET_OPERATOR = "net_operator"
ATTR_TARIFFS = "tariffs"

CONF_AREA = "area"
CONF_COUNTRY = "country"
CONF_CURRENCY_IN_CENT = "in_cent"
CONF_DECIMALS = "decimals"
CONF_PRICETYPE = "pricetype"
CONF_TEMPLATE = "cost_template"
CONF_VAT = "vat"
CONF_ENABLE_FORECAST = "enable_forecast"
CONF_ENABLE_HELPER_BEFORE = "enable_helper_before"
CONF_ENABLE_HELPER_DURATION = "enable_helper_duration"
CONF_ENABLE_TARIFFS = "enable_tariffs"
CONF_FIXED_PRICE = "fixed_price"
CONF_FIXED_PRICE_VALUE = "fixed_value"
CONF_FIXED_PRICE_VAT = "fixed_vat"
CONF_TARIFF_CHARGE_OWNER = "tariff_charge_owner"

DATA = "data"
DEFAULT_NAME = "Energidataservice"
DEFAULT_TEMPLATE = "{{0.0|float}}"
DOMAIN = "energidataservice"

INTERVAL = namedtuple("Interval", "price time")
CO2INTERVAL = namedtuple("CO2Interval", "value time")

UNIQUE_ID = "unique_id"
UPDATE_EDS = "eds_update_{}"
UPDATE_EDS_5MIN = "eds_5m_update_{}"

# Multiplier mappings
UNIT_TO_MULTIPLIER = {"MWh": 0, "kWh": 1000, "Wh": 1000000}
MULTIPLIER_TO_UNIT = {0: "MWh", 1000: "kWh", 1000000: "Wh"}
CENT_MULTIPLIER = 100

# Currency settings
CURRENCY_LIST = {
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
    "USD": {
        "name": "USD",
        "symbol": "$",
        "cent": "¢",
    },
    "NONE": {
        "name": "NONE",
        "symbol": "NONE",
        "cent": "NONE",
    },
}

# Regions
# Format:
#   "Region": [CURRENCY_LIST, "Country", "Region description", VAT]
REGIONS = {
    "DK1": [CURRENCY_LIST["DKK"], "Denmark", "West of the great belt", 0.25],
    "DK2": [CURRENCY_LIST["DKK"], "Denmark", "East of the great belt", 0.25],
    "FI": [CURRENCY_LIST["EUR"], "Finland", "Finland", 0.24],
    "EE": [CURRENCY_LIST["EUR"], "Estonia", "Estonia", 0.20],
    "LT": [CURRENCY_LIST["EUR"], "Lithuania", "Lithuania", 0.21],
    "LV": [CURRENCY_LIST["EUR"], "Latvia", "Latvia", 0.21],
    "NO1": [CURRENCY_LIST["NOK"], "Norway", "Oslo", 0.25],
    "NO2": [CURRENCY_LIST["NOK"], "Norway", "Kristiansand", 0.25],
    "NO3": [CURRENCY_LIST["NOK"], "Norway", "Molde, Trondheim", 0.25],
    "NO4": [CURRENCY_LIST["NOK"], "Norway", "Tromsø", 0.25],
    "NO5": [CURRENCY_LIST["NOK"], "Norway", "Bergen", 0.25],
    "SE1": [CURRENCY_LIST["SEK"], "Sweden", "Luleå", 0.25],
    "SE2": [CURRENCY_LIST["SEK"], "Sweden", "Sundsvall", 0.25],
    "SE3": [CURRENCY_LIST["SEK"], "Sweden", "Stockholm", 0.25],
    "SE4": [CURRENCY_LIST["SEK"], "Sweden", "Malmö", 0.25],
    "FR": [CURRENCY_LIST["EUR"], "France", "France", 0.055],
    "NL": [CURRENCY_LIST["EUR"], "Netherlands", "Netherlands", 0.21],
    "BE": [CURRENCY_LIST["EUR"], "Belgium", "Belgium", 0.21],
    "AT": [CURRENCY_LIST["EUR"], "Austria", "Austria", 0.20],
    "DE": [CURRENCY_LIST["EUR"], "Germany", "Germany", 0.19],
    "LU": [CURRENCY_LIST["EUR"], "Luxemburg", "Luxemburg", 0.08],
    "FIXED": [CURRENCY_LIST["NONE"], "Fixed Price", "Fixed Price", 0.0],
}

SERVICE_RELOAD_HOUR = "hour_update"
SERVICE_RELOAD_DAY = "day_update"
SERVICE_RELOAD_DATA = "data_update"
