"""Do some mappings for region naming."""

from __future__ import annotations

from ...utils.regionhandler import RegionHandler

_REGION_MAP = {
    "LU": "DE-LU",
    "DE": "GER",
}


def map_region(region: RegionHandler) -> RegionHandler():
    """Map integration region to API region."""
    if region.region in _REGION_MAP:
        region.set_api_region(_REGION_MAP[region.region])

    return region
