"""Energi Data Service connector."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from logging import getLogger

import homeassistant.util.dt as dt_util

from ...const import CO2INTERVAL, INTERVAL
from .regions import CO2REGIONS, REGIONS

_LOGGER = getLogger(__name__)

BASE_URL = "https://api.energidataservice.dk/dataset/"

SOURCE_NAME = "Energi Data Service"

DEFAULT_CURRENCY = "EUR"

__all__ = ["REGIONS", "Connector", "DEFAULT_CURRENCY"]


def prepare_data(indata, date, tz) -> list:  # pylint: disable=invalid-name
    """Get today prices."""
    local_tz = dt_util.get_default_time_zone()
    reslist = []
    for dataset in indata:
        tmpdate = (
            datetime.fromisoformat(dataset["HourUTC"])
            .replace(tzinfo=dt_util.UTC)
            .astimezone(local_tz)
        )
        tmp = INTERVAL(dataset["SpotPriceEUR"], tmpdate)
        if date in tmp.hour.strftime("%Y-%m-%d"):
            reslist.append(tmp)

    return reslist


def prepare_co2_data(indata, date, tz) -> list:  # pylint: disable=invalid-name
    """Prepare the CO2 data and return a list."""
    local_tz = dt_util.get_default_time_zone()
    reslist = []
    for dataset in indata:
        tmpdate = (
            datetime.fromisoformat(dataset["Minutes5UTC"])
            .replace(tzinfo=dt_util.UTC)
            .astimezone(local_tz)
        )
        tmp = CO2INTERVAL(dataset["CO2Emission"], tmpdate)
        if date in tmp.hour.strftime("%Y-%m-%d"):
            reslist.append(tmp)

    return reslist


class Connector:
    """Energi Data Service API."""

    def __init__(
        self, regionhandler, client, tz, config  # pylint: disable=invalid-name
    ) -> None:
        """Init API connection to Energi Data Service."""
        self.config = config
        self.regionhandler = regionhandler
        self.client = client
        self._result = {}
        self._co2_result = {}
        self._tz = tz

    async def async_get_spotprices(self) -> None:
        """Fetch latest spotprices, excl. VAT and tariff."""
        headers = self._header()
        url = self._prepare_url(BASE_URL + "elspotprices")
        _LOGGER.debug(
            "Request body for %s via Energi Data Service API URL: %s",
            self.regionhandler.region,
            url,
        )
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

            _LOGGER.debug(
                "Response for %s:\n%s",
                self.regionhandler.region,
                json.dumps(self._result, indent=2, default=str),
            )
        else:
            _LOGGER.error("API returned error %s", str(resp.status))

    async def async_get_co2emissions(self) -> None:
        """Fetch CO2 emissions."""

        if self.regionhandler.region in CO2REGIONS:
            headers = self._header()
            url = self._prepare_url(BASE_URL + "CO2EmisProg", True)
            _LOGGER.debug(
                "CO2 Request body for %s via Energi Data Service API URL: %s",
                self.regionhandler.region,
                url,
            )
            resp = await self.client.get(url, headers=headers)

            if resp.status == 400:
                _LOGGER.error("API returned error 400, Bad Request!")
                self._result = {}
            elif resp.status == 411:
                _LOGGER.error("API returned error 411, Invalid Request!")
                self._result = {}
            elif resp.status == 200:
                res = await resp.json()
                self._co2_result = res["records"]

                _LOGGER.debug(
                    "Response for %s CO2:\n%s",
                    self.regionhandler.region,
                    json.dumps(self._co2_result, indent=2, default=str),
                )
            else:
                _LOGGER.error("API returned error %s", str(resp.status))
        else:
            _LOGGER.debug("CO2 values not found for this region")

    @staticmethod
    def _header() -> dict:
        """Create default request header."""
        data = {"Content-Type": "application/json"}
        return data

    def _prepare_url(self, url: str, co2: bool = False) -> str:
        """Prepare and format the URL for the API request."""
        if not co2:
            start_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
            end_date = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
            start = f"start={str(start_date)}"
            end = f"end={str(end_date)}"
            limit = "limit=150"
            objfilter = (
                f"filter=%7B%22PriceArea%22:%22{str(self.regionhandler.region)}%22%7D"
            )
            sort = "sort=HourUTC%20asc"
            columns = "columns=HourUTC,SpotPriceEUR"

            return f"{url}?{start}&{end}&{objfilter}&{sort}&{columns}&{limit}"
        else:
            start_date = (datetime.utcnow()).strftime("%Y-%m-%d")
            start = f"start={str(start_date)}"
            sort = "sort=Minutes5UTC%20ASC"
            objfilter = (
                f"filter=%7B%22PriceArea%22:[%22{str(self.regionhandler.region)}%22]%7D"
            )
            return f"{url}?{start}&{sort}&{objfilter}"

    @property
    def today(self) -> list:
        """Return raw dataset for today."""
        date = datetime.now().strftime("%Y-%m-%d")
        return prepare_data(self._result, date, self._tz)

    @property
    def tomorrow(self) -> list:
        """Return raw dataset for today."""
        date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        return prepare_data(self._result, date, self._tz)

    @property
    def co2data(self) -> list:
        """Return raw CO2 dataset."""
        date = datetime.now().strftime("%Y-%m-%d")
        return prepare_co2_data(self._co2_result, date, self._tz)
