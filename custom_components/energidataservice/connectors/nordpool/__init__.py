"""Nordpool connector."""
from __future__ import annotations

import asyncio
import logging

from datetime import datetime, timedelta
from dateutil.parser import parse as parse_dt

import pytz

from .mapping import map_region
from .regions import REGIONS
from ...const import INTERVAL

_LOGGER = logging.getLogger(__name__)

BASE_URL = (
    "https://www.nordpoolgroup.com/api/marketdata/page/10?currency=EUR&endDate=%s"
)

SOURCE_NAME = "Nord Pool"


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
    """Define Nordpool Connector Class."""

    def __init__(self, regionhandler, client, tz):  # pylint: disable=invalid-name
        """Init API connection to Nordpool Group"""
        self.regionhandler = map_region(regionhandler)
        self.client = client
        self._result = {}
        self._tz = tz

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

        _LOGGER.debug("Response for %s:", self.regionhandler.region)
        _LOGGER.debug(self._result)

    async def _fetch(self, enddate: datetime) -> str:
        """Fetch data from API."""
        url = BASE_URL % enddate.strftime("%d-%m-%Y")
        _LOGGER.debug(
            "Request URL for %s via Nordpool: %s",
            (self.regionhandler.api_region or self.regionhandler.region),
            url,
        )
        resp = await self.client.get(url)

        if resp.status == 400:
            _LOGGER.error("API returned error 400, Bad Request!")
            raise BadRequest from None
        elif resp.status == 411:
            _LOGGER.error("API returned error 411, Invalid Request!")
            raise InvalidRequest from None

        res = await resp.json()
        return res

    def _parse_json(self, data):
        """Parse json response"""

        if not "data" in data:
            return []

        # All relevant data is in data['data']
        data = data["data"]

        region_data = []

        if self.regionhandler.api_region:
            region = self.regionhandler.api_region
        else:
            region = self.regionhandler.region

        # Loop through response rows
        for row in data["Rows"]:
            row_start_time = row["StartTime"]

            # Loop through columns
            for col in row["Columns"]:
                name = col["Name"]
                # If areas is defined and name isn't in areas, skip column
                if region and name not in region:
                    continue

                value = self._conv_to_float(col["Value"])
                if not value:
                    continue

                region_data.append(
                    {
                        "HourUTC": f"{row_start_time}+00:00",
                        "SpotPriceEUR": value,
                    }
                )

        return region_data

    @staticmethod
    def _conv_to_float(value):
        """Convert numbers to float. Return infinity, if conversion fails."""
        try:
            return float(value.replace(",", ".").replace(" ", ""))
        except ValueError:
            return None

    @property
    def today(self):
        """Return raw dataset for today."""
        date = datetime.now().strftime("%Y-%m-%d")
        return prepare_data(self._result, date, self._tz)

    @property
    def tomorrow(self):
        """Return raw dataset for today."""
        date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        data = prepare_data(self._result, date, self._tz)
        if len(data) > 20:
            return data
        else:
            return None


class BadRequest(Exception):
    """Representation of a Bad Request exception."""

    pass


class InvalidRequest(Exception):
    """Representation of an Invalid Request."""

    pass
