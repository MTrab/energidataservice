"""Energi Data Service API handler"""
import requests
import logging

from currency_converter import CurrencyConverter
from datetime import datetime, timedelta, timezone
from .const import LIMIT

_LOGGER = logging.getLogger(__name__)


class Energidataservice:
    """Energi Data Service API"""

    def __init__(self, area):
        """Init API connection to Energi Data Service"""
        self._area = area
        self._result = {}

    def get_spotprices(self):
        """Fetch latest spotprices, excl. VAT and tariff."""
        try:
            headers = self._header()
            body = self._body()
            # url = (
            #    "https://api.energidataservice.dk/datastore_search?resource_id=elspotprices&limit="
            #    + LIMIT
            #    + '&filters={"PriceArea":"'
            #    + self._area
            #    + '"}&sort=HourUTC desc'
            # )
            url = "https://data-api.energidataservice.dk/v1/graphql"
            _LOGGER.debug("API URL: %s", url)
            _LOGGER.debug("Request header: %s", headers[0])
            _LOGGER.debug("Request body: %s", body)
            resp = requests.post(url, headers=headers[0], data=body, timeout=10)
            self._result = resp.json()

            _LOGGER.debug("Response:")
            _LOGGER.debug(self._result)

        except Exception as ex:
            raise Exception(str(ex))

    def _header(self):
        """Create default request header"""

        data = {"Content-Type": "application/json"}

        return [data]

    def _body(self):
        """Create GraphQL request body"""

        today = datetime.utcnow().strftime("%Y-%m-%d")
        tomorrow = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
        data = (
            '{"query": "query Dataset {elspotprices(where: {HourUTC: {_gte: \\"'
            + today
            + '\\", _lt: \\"'
            + tomorrow
            + '\\"}PriceArea: {_eq: \\"'
            + self._area
            + '\\"}} order_by: {HourUTC: asc} limit: 100 offset: 0){HourUTC SpotPriceEUR }}"}'
        )

        return data

    def _currency(self, currency_from, currency_to, value):
        """Convert currency"""
        c = CurrencyConverter()
        return c.convert(value, currency_from, currency_to)

    @property
    def raw_data(self):
        """Return the raw JSON result"""
        return self._result

    @property
    def today(self):
        """Return array of prices for today"""

    @property
    def tomorrow(self):
        """Return array of prices for tomorrow"""

    @property
    def current(self):
        """Return price for current hour"""
        now = datetime.utcnow()
        current_state_time = (
            now.replace(tzinfo=timezone.utc)
            .replace(microsecond=0)
            .replace(second=0)
            .replace(minute=0)
            .isoformat()
        )

        mwh_price = None

        for dataset in self._result["data"]["elspotprices"]:
            if dataset["HourUTC"] == current_state_time:
                mwh_price = dataset["SpotPriceEUR"]
                _LOGGER.debug("Found MWh price %f EUR", dataset["SpotPriceEUR"])
                break

        if not mwh_price is None:
            kwh_price = mwh_price / 1000
        else:
            kwh_price = None
            _LOGGER.warning(
                "OOPS! Something went very wrong! Couldn't find current price"
            )

        return self._currency("EUR", "DKK", kwh_price)
