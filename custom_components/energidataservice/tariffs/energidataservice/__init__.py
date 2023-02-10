"""Energi Data Service tariff connector"""
from __future__ import annotations

from datetime import datetime, timedelta
import json
from logging import getLogger

from homeassistant.util import slugify as util_slugify

from .chargeowners import CHARGEOWNERS
from .regions import REGIONS

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
        self._tariffs = {}
        self._result = {}
        self._additional_tariff = {}

        # dt_now = datetime.now()
        # for elafgift in FM_EL_AFGIFT:
        #     if elafgift["from"] <= dt_now and elafgift["to"] > dt_now:
        #         self._additional_tariff.update({"el_afgift": elafgift["value"]})
        #         break

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
        """Create default request header"""
        data = {"Content-Type": "application/json"}
        return data

    def _prepare_url(self, url: str) -> str:
        """Prepare and format the URL for the API request."""
        chargeowner = CHARGEOWNERS[self._chargeowner]
        limit = "limit=500"
        objfilter = 'filter=%7B"note": {},"gln_number": ["{}"]%7D'.format(  # pylint: disable=consider-using-f-string
            str(chargeowner["note"]).replace("'", '"'), chargeowner["gln"]
        )
        sort = "sort=ValidFrom desc"

        out_url = f"{url}?{objfilter}&{sort}&{limit}"
        _LOGGER.debug("URL for tariff request: %s", out_url)
        return out_url

    async def async_get_tariffs(self):
        """Get tariff from Eloverblik API"""
        await self.async_get_system_tariffs()
        try:
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

            check_date = (datetime.utcnow()).strftime("%Y-%m-%d")

            tariff_data = {}
            for entry in self._result:
                if (entry["ValidFrom"].split("T"))[0] <= check_date and (
                    entry["ValidTo"] is None
                    or (entry["ValidTo"].split("T"))[0] >= check_date
                ):
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
                "Error finding '%s' in the list of charge owners - please reconfigure your integration.",
                self._chargeowner,
            )

    async def async_get_system_tariffs(self) -> dict:
        """Get additional system tariffs defined by the Danish government."""
        search_filter = '{"Note":["Elafgift","Systemtarif","Transmissions nettarif"]}'
        limit = 500
        headers = self._header()
        tariff_url = f"{BASE_URL}?filter={search_filter}&limit={limit}"

        resp = await self.client.get(tariff_url, headers=headers)

        if resp.status == 400:
            _LOGGER.error("API returned error 400, Bad Request!")
            dataset = {}
        elif resp.status == 411:
            _LOGGER.error("API returned error 411, Invalid Request!")
            dataset = {}
        elif resp.status == 200:
            res = await resp.json()
            dataset = res["records"]
        else:
            _LOGGER.error("API returned error %s", str(resp.status))
            return

        check_date = (datetime.utcnow()).strftime("%Y-%m-%d")
        tariff_data = {}
        for entry in dataset:
            if (entry["ValidFrom"].split("T"))[0] <= check_date and (
                entry["ValidTo"] is None
                or (entry["ValidTo"].split("T"))[0] >= check_date
            ):
                if not entry["Note"] in tariff_data:
                    tariff_data.update(
                        {util_slugify(entry["Note"]): float(entry["Price1"])}
                    )

        self._additional_tariff = tariff_data
