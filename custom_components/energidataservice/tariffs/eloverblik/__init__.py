"""Eloverblik tariff connector"""
from __future__ import annotations

from logging import getLogger
import sys

from homeassistant.config_entries import ConfigEntry
from pyeloverblik.eloverblik import Eloverblik
import requests
import voluptuous as vol

from ...const import CONF_METERING_POINT, CONF_REFRESH_TOKEN
from .regions import REGIONS

_LOGGER = getLogger(__name__)

SOURCE_NAME = "eloverblik"


__all__ = ["Connector"]


class Connector:
    """Eloverblik API"""

    def __init__(self, hass, refresh_token: str, metering_point: str) -> None:
        """Init API connection to Eloverblik"""
        self.hass = hass
        self.client = Eloverblik(refresh_token)
        self._metering_point = metering_point
        self._tariff_data = None

    @property
    def tariffs(self):
        """Return the tariff data."""
        _LOGGER.debug(self._tariff_data)
        return self._tariff_data

    async def async_get_tariffs(self):
        """Get tariff from Eloverblik API"""
        try:
            tariff_data = await self.hass.async_add_executor_job(
                self.client.get_tariffs, self._metering_point
            )

            if tariff_data.status == 200:
                self._tariff_data = tariff_data
            else:
                _LOGGER.warning(
                    "Error from eloverblik when getting tariff data: %s - %s",
                    tariff_data.status,
                    tariff_data.detailed_status,
                )
        except requests.exceptions.HTTPError as err:
            message = None
            if err.response.status_code == 401:
                message = "Unauthorized error while accessing the Eloverblik API!"
            else:
                exc = sys.exc_info()[1]
                message = f"Exception: {exc}"

            _LOGGER.warning(message)
        except:  # pylint: disable=bare-except
            exc = sys.exc_info()[1]
            _LOGGER.warning("Exception: %s", exc)

        _LOGGER.debug("Done fetching tariff data from Eloverblik")
        _LOGGER.debug("Tariffs: %s", self._tariff_data.charges)

        return self._tariff_data.charges.values()
