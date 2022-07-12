"""Energi Data Service connector"""
from __future__ import annotations

from datetime import datetime, timedelta
from logging import getLogger

import pytz

from ...const import INTERVAL
from .regions import REGIONS

_LOGGER = getLogger(__name__)

BASE_URL = "https://api.energidataservice.dk/dataset/elspotprices"

SOURCE_NAME = "Energi Data Service"

__all__ = ["REGIONS", "Connector"]


def prepare_data(indata, date, tz) -> list:  # pylint: disable=invalid-name
    """Get today prices."""
    local_tz = pytz.timezone(tz)
    reslist = []
    for dataset in indata:
        tmpdate = (
            datetime.fromisoformat(dataset["HourUTC"])
            .replace(tzinfo=pytz.utc)
            .astimezone(local_tz)
        )
        tmp = INTERVAL(dataset["SpotPriceEUR"], local_tz.normalize(tmpdate))
        if date in tmp.hour.strftime("%Y-%m-%d"):
            reslist.append(tmp)

    return reslist


class Connector:
    """Energi Data Service API"""

    def __init__(
        self, regionhandler, client, tz  # pylint: disable=invalid-name
    ) -> None:
        """Init API connection to Energi Data Service"""
        self.regionhandler = regionhandler
        self.client = client
        self._result = {}
        self._tz = tz

    async def async_get_spotprices(self) -> None:
        """Fetch latest spotprices, excl. VAT and tariff."""
        headers = self._header()
        url = self._prepare_url(BASE_URL)
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

            _LOGGER.debug("Response for %s:", self.regionhandler.region)
            _LOGGER.debug(self._result)
        else:
            _LOGGER.error("API returned error %s", str(resp.status))

    @staticmethod
    def _header() -> dict:
        """Create default request header"""
        data = {"Content-Type": "application/json"}
        return data

    def _prepare_url(self, url: str) -> str:
        """Prepare and format the URL for the API request."""
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
