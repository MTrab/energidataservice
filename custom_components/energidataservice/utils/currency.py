"""Implementation of currency converter."""
from currency_converter import CurrencyConverter
from homeassistant.core import HomeAssistant


class Currency:
    """Currency converter class."""

    _converter: CurrencyConverter

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize currency converter."""
        self._hass = hass
        self._converter = CurrencyConverter()

    def convert(
        self, value: float, to_currency: str, from_currency: str = "EUR"
    ) -> float:
        """Do the conversion."""
        return self._converter.convert(value, from_currency, to_currency)
