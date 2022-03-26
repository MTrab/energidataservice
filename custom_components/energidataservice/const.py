""" Energidataservice consts """
DOMAIN = "energidataservice"

CONF_AREA = "area"
CONF_VAT = "vat"
CONF_DECIMALS = "decimals"

LIMIT = "48"

AREA_EAST = "East of the great belt"
AREA_WEST = "West of the great belt"
DEFAULT_NAME = "Energidataservice"
DATA = "data"
SIGNAL_ENERGIDATASERVICE_UPDATE_RECEIVED = "energidataservice_update_received"
UNIQUE_ID = "unique_id"
UPDATE_LISTENER = "update_listener"
UPDATE_TRACK = "update_track"

AREA_MAP = {
    AREA_WEST: "DK1",
    AREA_EAST: "DK2",
}

AREA_TO_TEXT = {
    "DK1": AREA_WEST,
    "DK2": AREA_EAST,
}

PRICE_IN = {
    "kWh": 1000,
    "MWh": 0,
    "Wh": 1000 * 1000
}
