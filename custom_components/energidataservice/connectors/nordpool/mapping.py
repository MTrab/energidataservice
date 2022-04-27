"""Do some mappings for region naming."""
from ...utils.regionhandler import RegionHandler

_REGION_MAP = {
    "DE": "DE-LU",
    "NO1": "Oslo",
    "NO2": "Kr.Sand",
    "NO3": "Molde",
    "NO4": "Tromsø",
    "NO5": "Bergen",
    "LU": "DE-LU",
}


@staticmethod
def map_region(region: RegionHandler) -> RegionHandler():
    """Map integration region to API region."""
    if region.region in _REGION_MAP:
        region.set_api_region(_REGION_MAP[region.region])

    return region