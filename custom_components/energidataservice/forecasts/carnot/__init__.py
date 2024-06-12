"""Carnot forecast connector."""

from __future__ import annotations

from datetime import datetime
from logging import getLogger

import homeassistant.util.dt as dt_util

from ...const import INTERVAL
from .regions import REGIONS

_LOGGER = getLogger(__name__)

BASE_URL = "https://whale-app-dquqw.ondigitalocean.app/openapi/get_predict"

SOURCE_NAME = "Carnot"
DEFAULT_CURRENCY = "DKK"
DEFAULT_UNIT = "MWh"

__all__ = ["REGIONS", "Connector", "DEFAULT_CURRENCY", "DEFAULT_UNIT"]


def prepare_data(indata, tz) -> list | None:  # pylint: disable=invalid-name
    """Get today prices."""
    local_tz = dt_util.get_default_time_zone()
    reslist = []
    if not isinstance(indata, type(None)):
        now = datetime.now()
        for dataset in indata:
            tmpdate = (
                datetime.fromisoformat(dataset["utctime"])
                .replace(tzinfo=dt_util.UTC)
                .astimezone(local_tz)
            )
            if tmpdate.day != now.day:
                if tmpdate.month == now.month and tmpdate.day < now.day:
                    continue
                tmp = INTERVAL(dataset["prediction"], tmpdate)
                reslist.append(tmp)
        return reslist

    return None


class Connector:
    """Carnot forecast API."""

    def __init__(
        self, regionhandler, client, tz  # pylint: disable=invalid-name
    ) -> None:
        """Init API connection to Carnot."""
        self.regionhandler = regionhandler
        self.client = client
        self._result = {}
        self._tz = tz

    async def async_get_forecast(self, apikey: str, email: str) -> list | None:
        """Fetch forecast data from API."""
        self._result = None
        headers = self._header(apikey, email)
        url = self._prepare_url(BASE_URL)
        _LOGGER.debug(
            "Request for '%s' at Carnot API URL: '%s' with headers %s",
            self.regionhandler.region,
            url,
            headers,
        )
        resp = await self.client.get(url, headers=headers)

        if resp.status == 400:
            _LOGGER.error("API returned error 400, Bad request!")
        elif resp.status == 404:
            _LOGGER.error("API returned error 404, Not found!")
        elif resp.status == 422 or resp.status == 401:
            _LOGGER.error(
                "API returned error %s, Validation error - check your credentials!",
                str(resp.status),
            )
        elif resp.status == 200:
            res = await resp.json()
            self._result = res["predictions"]
        else:
            _LOGGER.error("API returned error %s", str(resp.status))

        return (
            prepare_data(self._result, self._tz)
            if not isinstance(self._result, type(None))
            else None
        )

    @staticmethod
    def _header(apikey: str, email: str) -> dict:
        """Create default request header."""
        data = {
            "User-Agent": "HomeAssistant/Energidataservice",
            "Content-Type": "application/json",
            "apikey": apikey,
            "username": email,
        }
        return data

    def _prepare_url(self, url: str) -> str:
        """Prepare and format the URL for the API request."""

        region = f"region={str(self.regionhandler.region).lower()}"
        return f"{url}?{region}&energysource=spotprice&daysahead=7"
