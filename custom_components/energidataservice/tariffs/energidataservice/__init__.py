"""Energi Data Service tariff connector"""
from __future__ import annotations
import asyncio
from datetime import datetime, timedelta
import json

from logging import getLogger
from typing import Any

import requests

from .regions import REGIONS
from .chargeowners import CHARGEOWNERS

_LOGGER = getLogger(__name__)

SOURCE_NAME = "Energi Data Service Tariffer"

BASE_URL = "https://api.energidataservice.dk/dataset/DatahubPricelist"

# Source: https://energinet.dk/el/elmarkedet/tariffer/aktuelle-tariffer/
ADDITIONAL_TARIFFS = {
    "transmissions_net_tarif": 0.058,
    "system_tarif": 0.054,
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
        start_date = (datetime.utcnow()).strftime("%Y-%m-%d")
        start = f"start={str(start_date)}"
        limit = "limit=100"
        objfilter = f"filter=%7B%22Note%22:%5B%22Nettarif C time%22%5D,%22ChargeOwner%22:%5B%22{self._chargeowner}%22%5D%7D"  # pylint disable=line-too-long
        sort = "sort=ValidFrom%20asc"

        return f"{url}?{start}&{objfilter}&{sort}&{limit}"

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

        tariff_data = {}
        for key, val in self._result[0].items():
            if "Price" in key:
                hour = str(int("".join(filter(str.isdigit, key))) - 1)
                if len(hour) == 1:
                    hour = f"0{hour}"

                tariff_data.update({hour: val})
        if len(tariff_data) == 24:
            self._tariffs = tariff_data

        _LOGGER.debug("Tariffs:\n%s", json.dumps(self.tariffs, indent=2, default=str))
        return self.tariffs
