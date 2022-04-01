"""Implementation of currency converter."""
import os
import urllib.request
from datetime import date

from currency_converter import ECB_URL, CurrencyConverter
from homeassistant.core import HomeAssistant


class Currency:
    """Currency converter class."""

    _converter: CurrencyConverter

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize currency converter."""
        self._hass = hass
        self._basedir = ".storage/energidataservice"
        self._filename = f"{self._basedir}/ecb_{date.today():%Y%m%d}.zip"
        hass.add_job(self.refresh)

    async def refresh(self):
        """Update currencies."""
        await self._update_currencies()

    async def _update_currencies(self):
        """Refresh currency database file if no file exists for today"""
        if not os.path.isfile(self._filename):
            if not os.path.exists(self._basedir):
                os.makedirs(self._basedir)
            else:
                for file in os.listdir(self._basedir):
                    os.remove(os.path.join(self._basedir, file))

            await self._hass.async_add_executor_job(
                urllib.request.urlretrieve, ECB_URL, self._filename
            )
        self._converter = CurrencyConverter(self._filename)

    def convert(
        self, value: float, to_currency: str, from_currency: str = "EUR"
    ) -> float:
        """Do the conversion."""
        return self._converter.convert(value, from_currency, to_currency)
