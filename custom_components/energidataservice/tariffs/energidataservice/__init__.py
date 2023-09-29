"""Energi Data Service tariff connector."""
from __future__ import annotations

import json
from datetime import datetime
from logging import getLogger

from aiohttp import ClientSession
from async_retrying_ng import RetryError, retry
from homeassistant.util import slugify as util_slugify

from .chargeowners import CHARGEOWNERS
from .regions import REGIONS

_LOGGER = getLogger(__name__)

SOURCE_NAME = "Energi Data Service Tariffer"

BASE_URL = "https://api.energidataservice.dk/dataset/DatahubPricelist"

__all__ = ["Connector", "REGIONS", "CHARGEOWNERS"]


class Connector:
    """Energi Data Service API."""

    def __init__(
        self, hass, client: ClientSession, chargeowner: str | None = None
    ) -> None:
        """Init API connection to Energi Data Service."""
        self.hass = hass
        self.client = client
        self._chargeowner = chargeowner
        self._tariffs = {}
        self._additional_tariff = {}
        self._all_tariffs = {}
        self._all_additional_tariffs = {}

    @property
    def tariffs(self):
        """Return the tariff data."""
        _LOGGER.debug(self._tariffs)

        tariffs = {
            "additional_tariffs": self._additional_tariff,
            "tariffs": self._tariffs,
        }

        return tariffs

    @staticmethod
    def _header() -> dict:
        """Create default request header."""
        data = {"Content-Type": "application/json"}
        return data

    async def async_get_tariffs(self):
        """Get tariff from Eloverblik API."""
        await self.async_get_system_tariffs()

        try:
            chargeowner = CHARGEOWNERS[self._chargeowner]
            limit = "limit=500"
            objfilter = 'filter=%7B"chargetypecode": {},"gln_number": ["{}"]%7D'.format(  # pylint: disable=consider-using-f-string
                str(chargeowner["type"]).replace("'", '"'), chargeowner["gln"]
            )
            sort = "sort=ValidFrom desc"

            query = f"{objfilter}&{sort}&{limit}"
            resp = await self.async_call_api(query)

            if len(resp) == 0:
                _LOGGER.warning(
                    "Could not fetch tariff data from Energi Data Service DataHub!"
                )
                return
            else:
                # We got data from the DataHub - update the dataset
                self._all_tariffs = resp

            check_date = (datetime.utcnow()).strftime("%Y-%m-%d")

            tariff_data = {}
            for entry in self._all_tariffs:
                if self.__entry_in_range(entry, check_date):
                    _LOGGER.debug("Found possible dataset: %s", entry)
                    baseprice = 0
                    for key, val in entry.items():
                        if key == "Price1":
                            baseprice = val
                        if "Price" in key:
                            hour = str(int("".join(filter(str.isdigit, key))) - 1)

                            tariff_data.update(
                                {hour: val if val is not None else baseprice}
                            )

                    if len(tariff_data) == 24:
                        self._tariffs = tariff_data
                        break

            _LOGGER.debug(
                "Tariffs:\n%s", json.dumps(self.tariffs, indent=2, default=str)
            )
            return self.tariffs
        except KeyError:
            _LOGGER.error(
                "Error finding '%s' in the list of charge owners - "
                "please reconfigure your integration.",
                self._chargeowner,
            )
        except RetryError:
            _LOGGER.error("Retry attempts exceeded for tariffs request.")

    def get_dated_tariff(self, date: datetime) -> dict:
        """Get tariff for this specific date."""
        check_date = date.strftime("%Y-%m-%d")

        tariff_data = {}
        for entry in self._all_tariffs:
            if self.__entry_in_range(entry, check_date):
                baseprice = 0
                for key, val in entry.items():
                    if key == "Price1":
                        baseprice = val
                    if "Price" in key:
                        hour = str(int("".join(filter(str.isdigit, key))) - 1)

                        tariff_data.update(
                            {hour: val if val is not None else baseprice}
                        )

                if len(tariff_data) == 24:
                    return tariff_data

        return {}

    def get_dated_system_tariff(self, date: datetime) -> dict:
        """Get system tariffs for this specific date."""
        check_date = date.strftime("%Y-%m-%d")
        tariff_data = {}
        for entry in self._all_additional_tariffs:
            if self.__entry_in_range(entry, check_date):
                if entry["Note"] not in tariff_data:
                    tariff_data.update(
                        {util_slugify(entry["Note"]): float(entry["Price1"])}
                    )

        return tariff_data

    async def async_get_system_tariffs(self) -> dict:
        """Get additional system tariffs defined by the Danish government."""
        search_filter = '{"Note":["Elafgift","Systemtarif","Transmissions nettarif"]}'
        limit = 500

        query = f"filter={search_filter}&limit={limit}"

        try:
            dataset = await self.async_call_api(query)

            if len(dataset) == 0:
                _LOGGER.warning(
                    "Could not fetch tariff data from Energi Data Service DataHub!"
                )
                return
            else:
                self._all_additional_tariffs = dataset

            check_date = (datetime.utcnow()).strftime("%Y-%m-%d")
            tariff_data = {}
            for entry in self._all_additional_tariffs:
                if self.__entry_in_range(entry, check_date):
                    if entry["Note"] not in tariff_data:
                        tariff_data.update(
                            {util_slugify(entry["Note"]): float(entry["Price1"])}
                        )

            self._additional_tariff = tariff_data
        except RetryError:
            _LOGGER.error("Retry attempts exceeded for retrieving system tariffs.")

    @retry(attempts=10, delay=10, max_delay=3600, backoff=1.5)
    async def async_call_api(self, query: str) -> dict:
        """Make the API calls."""
        try:
            headers = self._header()
            resp = await self.client.get(f"{BASE_URL}?{query}", headers=headers)
            resp.raise_for_status()

            if resp.status == 400:
                _LOGGER.error("API returned error 400, Bad Request!")
                return {}
            elif resp.status == 411:
                _LOGGER.error("API returned error 411, Invalid Request!")
                return {}
            elif resp.status == 200:
                res = await resp.json()
                return res["records"]
            else:
                _LOGGER.error("API returned error %s", str(resp.status))
                return {}
        except Exception as exc:
            _LOGGER.error("Error during API request: %s", exc)
            raise

    def __entry_in_range(self, entry, check_date) -> bool:
        """Check if an entry is witin the date range."""
        return (entry["ValidFrom"].split("T"))[0] <= check_date and (
            entry["ValidTo"] is None or (entry["ValidTo"].split("T"))[0] > check_date
        )
