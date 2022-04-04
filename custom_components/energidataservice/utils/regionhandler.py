"""Utils for handling regions."""
import logging

from currency_converter import CurrencyConverter

from ..const import _CURRENCY, _REGIONS

_LOGGER = logging.getLogger(__name__)


class Currency:
    """Define currency class."""

    _converter: CurrencyConverter

    def __init__(self, currency: dict) -> None:
        """Initialize a new Currency object."""
        self._name = currency["name"]
        self._symbol = currency["symbol"]
        self._cent = currency["cent"]
        self._converter = CurrencyConverter()

    def convert(
        self, value: float, to_currency: str, from_currency: str = "EUR"
    ) -> float:
        """Do the conversion."""
        try:
            return self._converter.convert(value, from_currency, to_currency)
        except ValueError:
            _LOGGER.warning(
                "Invalid currency for conversion, returning prices in %s", self._name
            )
            return value

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

    def set_region(self, region: str, currency_override: str = None) -> None:
        """Set region."""
        if " " in region:
            region = self.description_to_region(region)

        self._region = region
        self._country = self.country_from_region(region)
        self._currency = self.get_country_currency(self._country)
        self._description = self.region_to_description(region)
        if not currency_override is None:
            self.currency = Currency(_CURRENCY[currency_override])
        else:
            self.currency = Currency(self._currency)

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
