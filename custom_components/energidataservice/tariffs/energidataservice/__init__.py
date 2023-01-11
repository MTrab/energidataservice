"""Energi Data Service tariff connector"""
from __future__ import annotations

from datetime import datetime, timedelta
import json
from logging import getLogger

from .chargeowners import CHARGEOWNERS
from .regions import REGIONS

_LOGGER = getLogger(__name__)

SOURCE_NAME = "Energi Data Service Tariffer"

BASE_URL = "https://api.energidataservice.dk/dataset/DatahubPricelist"

# Source: https://energinet.dk/el/elmarkedet/tariffer/aktuelle-tariffer/
ADDITIONAL_TARIFFS = {
    "transmissions_net_tarif": 0.058,
    "system_tarif": 0.054,
    "el_afgift": 0.008,
}

__all__ = ["Connector", "REGIONS", "CHARGEOWNERS"]


class Connector:
    """Energi Data Service API"""

    def __init__(self, hass, client, chargeowner: str | None = None) -> None:
        """Init API connection to Energi Data Service"""
        self.hass = hass
        self.client = client
        self._chargeowner = chargeowner
        self._tariffs = {}
        self._result = {}

    @property
    def tariffs(self):
        """Return the tariff data."""
        _LOGGER.debug(self._tariffs)

        tariffs = {
            "additional_tariffs": ADDITIONAL_TARIFFS,
            "tariffs": self._tariffs,
        }

        return tariffs

    @staticmethod
    def _header() -> dict:
        """Create default request header"""
        data = {"Content-Type": "application/json"}
        return data

    def _prepare_url(self, url: str) -> str:
        """Prepare and format the URL for the API request."""
        chargeowner = CHARGEOWNERS[self._chargeowner]
        limit = "limit=500"
        objfilter = 'filter=%7B"note": {},"gln_number": ["{}"]%7D'.format(  # pylint: disable=consider-using-f-string
            str(chargeowner["note"]).replace("'", '"'), chargeowner["gln"]
        )
        sort = "sort=ValidFrom desc"

        out_url = f"{url}?{objfilter}&{sort}&{limit}"
        _LOGGER.debug("URL for tariff request: %s", out_url)
        return out_url

    async def async_get_tariffs(self):
        """Get tariff from Eloverblik API"""
        headers = self._header()
        url = self._prepare_url(BASE_URL)

        resp = await self.client.get(url, headers=headers)

        if resp.status == 400:
            _LOGGER.error("API returned error 400, Bad Request!")
            self._result = {}
        elif resp.status == 411:
            _LOGGER.error("API returned error 411, Invalid Request!")
            self._result = {}
        elif resp.status == 200:
            res = await resp.json()
            self._result = res["records"]
        else:
            _LOGGER.error("API returned error %s", str(resp.status))
            return

        check_date = (datetime.utcnow()).strftime("%Y-%m-%d")

        tariff_data = {}
        for entry in self._result:
            if (entry["ValidFrom"].split("T"))[0] <= check_date and (
                entry["ValidTo"] is None
                or (entry["ValidTo"].split("T"))[0] >= check_date
            ):
                _LOGGER.debug("Found possible dataset: %s", entry)
                baseprice = 0
                for key, val in entry.items():
                    if key == "Price1":
                        baseprice = val
                    if "Price" in key:
                        hour = str(int("".join(filter(str.isdigit, key))) - 1)

                        tariff_data.update({hour: val if val is not None else baseprice})

                if len(tariff_data) == 24:
                    self._tariffs = tariff_data
                    break

        _LOGGER.debug("Tariffs:\n%s", json.dumps(self.tariffs, indent=2, default=str))
        return self.tariffs
