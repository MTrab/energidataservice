"""Energi Data Service connector"""
from collections import namedtuple
from datetime import datetime, timedelta
import logging

import pytz

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://data-api.energidataservice.dk/v1/graphql"

SOURCE_NAME = "Energi Data Service"


def prepare_data(indata, date, tz) -> list:  # pylint: disable=invalid-name
    """Get today prices."""
    local_tz = pytz.timezone(tz)
    reslist = []
    for dataset in indata:
        Interval = namedtuple("Interval", "price hour")
        tmpdate = (
            datetime.fromisoformat(dataset["HourUTC"])
            .replace(tzinfo=pytz.utc)
            .astimezone(local_tz)
        )
        tmp = Interval(dataset["SpotPriceEUR"], local_tz.normalize(tmpdate))
        if date in tmp.hour.strftime("%Y-%m-%d"):
            reslist.append(tmp)

    return reslist


class Connector:
    """Energi Data Service API"""

    def __init__(self, regionhandler, client, tz):  # pylint: disable=invalid-name
        """Init API connection to Energi Data Service"""
        self.regionhandler = regionhandler
        self.client = client
        self._result = {}
        self._tz = tz

    async def get_spotprices(self) -> None:
        """Fetch latest spotprices, excl. VAT and tariff."""
        headers = self._header()
        body = self._body()
        url = BASE_URL
        _LOGGER.debug(
            "Request body for %s via Energi Data Service: %s",
            self.regionhandler.region,
            body,
        )
        resp = await self.client.post(url, data=body, headers=headers)

        if resp.status == 400:
            _LOGGER.error("API returned error 400, Bad Request!")
            self._result = {}
        elif resp.status == 411:
            _LOGGER.error("API returned error 411, Invalid Request!")
            self._result = {}
        elif resp.status == 200:
            res = await resp.json()
            self._result = res["data"]["elspotprices"]

            _LOGGER.debug("Response for %s:", self.regionhandler.region)
            _LOGGER.debug(self._result)
        else:
            _LOGGER.error("API returned error %s", str(resp.status))

    @staticmethod
    def _header():
        """Create default request header"""
        data = {"Content-Type": "application/json"}
        return data

    def _body(self):
        """Create GraphQL request body"""
        date_from = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        date_to = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
        _LOGGER.debug("Start Date: %s", date_from)
        _LOGGER.debug("End Data: %s", date_to)
        data = (
            '{"query": "query Dataset {elspotprices(where: {HourUTC: {_gte: \\"'
            + str(date_from)
            + '\\", _lt: \\"'
            + str(date_to)
            + '\\"} PriceArea: {_eq: \\"'
            + str(self.regionhandler.region)
            + '\\"}} order_by: {HourUTC: asc} limit: 100 offset: 0){HourUTC SpotPriceEUR }}"}'
        )
        return data

    @property
    def today(self):
        """Return raw dataset for today."""
        date = datetime.now().strftime("%Y-%m-%d")
        return prepare_data(self._result, date, self._tz)

    @property
    def tomorrow(self):
        """Return raw dataset for today."""
        date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        return prepare_data(self._result, date, self._tz)
