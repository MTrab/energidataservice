"""Define valid zones for Energi Data Service."""
from ...const import CURRENCY_LIST

REGIONS = {
    "DK1",
    "DK2",
    "SE3",
    "SE4",
    "NO2",
}

EXTRA_REGIONS = {
    "DK1": [CURRENCY_LIST["DKK"], "Denmark", "West of the great belt", 0.25],
}
