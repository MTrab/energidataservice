"""Nordpool connector."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

import homeassistant.util.dt as dt_util
import pytz

from ...const import INTERVAL
from .mapping import map_region
from .regions import REGIONS

_LOGGER = logging.getLogger(__name__)

# BASE_URL = (
#     "https://www.nordpoolgroup.com/api/marketdata/page/10?currency=EUR&endDate=%s"
# )

BASE_URL = "https://dataportal-api.nordpoolgroup.com/api/DayAheadPrices?currency=EUR&date={}&market=DayAhead&deliveryArea={}"

SOURCE_NAME = "Nord Pool"

DEFAULT_CURRENCY = "EUR"

TIMEZONE = pytz.timezone("Europe/Stockholm")

__all__ = ["REGIONS", "Connector", "DEFAULT_CURRENCY"]


def prepare_data(indata, date, tz) -> list:  # pylint: disable=invalid-name
    """Get today prices."""
    local_tz = dt_util.get_default_time_zone()
    reslist = []
    for dataset in indata:
        tmpdate = datetime.fromisoformat(dataset["HourUTC"]).astimezone(local_tz)
        tmp = INTERVAL(dataset["SpotPriceEUR"], tmpdate)
        if date in tmp.hour.strftime("%Y-%m-%d"):
            reslist.append(tmp)

    return reslist


class Connector:
    """Define Nordpool Connector Class."""

    def __init__(
        self, regionhandler, client, tz, config  # pylint: disable=invalid-name
    ) -> None:
        """Init API connection to Nordpool Group."""
        self.config = config
        self.regionhandler = regionhandler
        self.client = client
        self._result = {}
        self._tz = tz
        self.status = 200

    async def async_get_spotprices(self) -> None:
        """Fetch latest spotprices, excl. VAT and tariff."""
        # yesterday = datetime.now() - timedelta(days=1)
        yesterday = datetime.now() - timedelta(days=1)
        today = datetime.now()
        tomorrow = datetime.now() + timedelta(days=1)
        jobs = [
            self._fetch(yesterday),
            self._fetch(today),
            self._fetch(tomorrow),
        ]

        res = await asyncio.gather(*jobs)
        raw = []

        for i in res:
            raw = raw + self._parse_json(i)

        self._result = raw

        _LOGGER.debug("Dataset for %s:", self.regionhandler.region)
        _LOGGER.debug(self._result)

    async def _fetch(self, enddate: datetime) -> str:
        """Fetch data from API."""
        if self.regionhandler.api_region:
            region = self.regionhandler.api_region
        else:
            region = self.regionhandler.region

        url = BASE_URL.format(enddate.strftime("%Y-%m-%d"), region)

        _LOGGER.debug(
            "Request URL for %s via Nordpool: %s",
            (self.regionhandler.api_region or self.regionhandler.region),
            url,
        )
        resp = await self.client.get(url)

        if resp.status == 400:
            _LOGGER.error("API returned error 400, Bad Request!")
            return {}
        elif resp.status == 411:
            _LOGGER.error("API returned error 411, Invalid Request!")
            return {}
        elif resp.status == 200:
            res = await resp.json()
            _LOGGER.debug("Response for %s:", self.regionhandler.region)
            _LOGGER.debug(res)
            return res
        elif resp.status == 204:
            return {}
        elif resp.status == 500:
            _LOGGER.warning("Server blocked request")
        else:
            _LOGGER.error("API returned error %s", str(resp.status))
            return {}

    def _parse_json(self, data) -> list:
        """Parse json response."""
        # Timezone for data from Nord Pool Group are "Europe/Stockholm"

        if not "multiAreaEntries" in data:
            return []

        if self.regionhandler.api_region:
            region = self.regionhandler.api_region
        else:
            region = self.regionhandler.region

        region_data = []

        for entry in data["multiAreaEntries"]:
            start_hour = entry["deliveryStart"]
            value = entry["entryPerArea"][region]
            region_data.append(
                {
                    "HourUTC": start_hour,
                    "SpotPriceEUR": value,
                }
            )

        return region_data

    @staticmethod
    def _conv_to_float(value) -> float | None:
        """Convert numbers to float. Return infinity, if conversion fails."""
        try:
            return float(value.replace(",", ".").replace(" ", ""))
        except ValueError:
            return None

    @property
    def today(self) -> list:
        """Return raw dataset for today."""
        date = datetime.now().strftime("%Y-%m-%d")
        return prepare_data(self._result, date, self._tz)

    @property
    def tomorrow(self) -> list:
        """Return raw dataset for today."""
        date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        data = prepare_data(self._result, date, self._tz)
        if len(data) > 20:
            return data
        else:
            return None
