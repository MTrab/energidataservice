"""Utils for handling regions."""
import logging
from ..const import _REGIONS

_LOGGER = logging.getLogger(__name__)


class Currency:
    """Define currency class."""

    def __init__(self, currency: dict) -> None:
        """Initialize a new Currency object."""
        _LOGGER.debug(self)
        self._name = currency["name"]
        self._symbol = currency["symbol"]
        self._cent = currency["cent"]

    @property
    def name(self) -> str:
        """Return name of currency."""
        return self._name

    @property
    def symbol(self) -> str:
        """Return symbol for currency."""
        return self._symbol

    @property
    def cent(self) -> str:
        """Return cent unit for currency."""
        return self._cent


class RegionHandler:
    """Region handler class."""

    def __init__(self, region: str = None) -> None:
        """Initialize the handler."""
        self._country = None
        self.currency = None
        self._region = None
        self._description = None

        if region:
            self.set_region(region)

    def set_region(self, region: str) -> None:
        """Set region."""
        if " " in region:
            region = self.description_to_region(region)

        self._region = region
        self._country = self.country_from_region(region)
        self._currency = self.get_country_currency(self._country)
        self._description = self.region_to_description(region)
        self.currency = Currency(self._currency)

    # def currency(self):
    #     """Return currency."""
    #     _LOGGER.debug(self._currency)

    #     def name() -> str:
    #         return self._currency["name"]

    #     def symbol() -> str:
    #         return self._currency["symbol"]

    #     def cent() -> str:
    #         return self._currency["cent"]

    #     RegionHandler.currency.name = name()
    #     RegionHandler.currency.symbol = symbol()
    #     RegionHandler.currency.cent = cent()

    #     _LOGGER.debug("RH name: %s", RegionHandler.currency.name)

    # currency.name = None
    # currency.symbol = None
    # currency.cent = None

    @staticmethod
    def get_countries(sort: bool = False, descending: bool = False) -> list:
        """Get list of available countries."""
        countries = []

        for region in _REGIONS.items():
            country = region[1][1]
            if not country in countries:
                countries.append(country)

        return countries if not sort else sorted(countries, reverse=descending)

    @staticmethod
    def regions_in_country(country: str) -> str:
        """Get available regions in country."""
        regions = []

        for region in _REGIONS.items():
            if country == region[1][1]:
                regions.append(region[0])

        return regions

    @staticmethod
    def region_to_description(region: str) -> str:
        """Get normal human readable description from region."""
        for reg in _REGIONS.items():
            if reg[0] == region:
                return reg[1][2]

        return None

    @staticmethod
    def description_to_region(description: str) -> str:
        """Get normal human readable description from region."""
        for region in _REGIONS.items():
            if region[1][2] == description:
                return region[0]

        return None

    @staticmethod
    def country_from_region(region: str) -> str:
        """Resolve actual country from given region."""
        for reg in _REGIONS.items():
            if reg[0] == region:
                return reg[1][1]

        return None

    @staticmethod
    def get_country_currency(country: str) -> dict:
        """Get official currency of country."""
        for region in _REGIONS.items():
            if country == region[1][1]:
                return region[1][0]

        return None

    @staticmethod
    def get_country_vat(country: str) -> float:
        """Get VAT amount for country."""
        for region in _REGIONS.items():
            if country == region[1][1]:
                return region[1][3]

        return None

    @property
    def country(self) -> str:
        """Return country."""
        return self._country

    @property
    def description(self) -> str:
        """Return human understandable description for the region."""
        return self._description

    @property
    def name(self) -> str:
        """Returns the region name."""
        return self._region
