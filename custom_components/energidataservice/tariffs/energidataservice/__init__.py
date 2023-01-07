"""Energi Data Service tariff connector"""
from __future__ import annotations
import asyncio
from datetime import datetime, timedelta

from logging import getLogger
from typing import Any

import requests

from .regions import REGIONS
from .chargeowners import CHARGEOWNERS

_LOGGER = getLogger(__name__)

SOURCE_NAME = "Energi Data Service Tariffer"

BASE_URL = "https://api.energidataservice.dk/dataset/DatahubPricelist"

__all__ = ["Connector", "REGIONS", "CHARGEOWNERS"]


class Connector:
    """Energi Data Service API"""

    def __init__(self, hass, client, chargeowner: str | None = None) -> None:
        """Init API connection to Energi Data Service"""
        self.hass = hass
        self.client = client
        self._chargeowner = chargeowner
        self._tariff_data = None
        self._result = {}

    @property
    def tariffs(self):
        """Return the tariff data."""
        _LOGGER.debug(self._tariff_data)
        return self._tariff_data

    @staticmethod
    def _header() -> dict:
        """Create default request header"""
        data = {"Content-Type": "application/json"}
        return data

    def _prepare_url(self, url: str) -> str:
        """Prepare and format the URL for the API request."""
        start_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (datetime.utcnow() + timedelta(days=10)).strftime("%Y-%m-%d")
        start = f"start={str(start_date)}"
        end = f"end={str(end_date)}"
        limit = "limit=100"
        objfilter = f"filter=%7B%22Note%22:%5B%22Nettarif C time%22%5D,%22ChargeOwner%22:%5B%22{self._chargeowner}%22%5D%7D"
        sort = "sort=ValidFrom%20asc"

        return f"{url}?{start}&{end}&{objfilter}&{sort}&{limit}"

    async def async_get_data(
        self, url: str, headers: dict | None = None, body: dict | str | None = None
    ) -> Any:
        """Make the call to the API."""
        return None

    async def async_get_tariffs(self):
        """Get tariff from Eloverblik API"""
        headers = self._header()
        url = self._prepare_url(BASE_URL)
