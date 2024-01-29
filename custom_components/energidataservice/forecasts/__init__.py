"""Dynamically load all available forecast providers."""

from __future__ import annotations

from collections import namedtuple
from importlib import import_module
from logging import getLogger
from os import listdir
from posixpath import dirname

from genericpath import isdir

from ..const import CURRENCY_LIST, REGIONS

_LOGGER = getLogger(__name__)


class Forecast:
    """Handle forecast modules."""

    def __init__(self):
        """Initialize forecast handler."""

        self._forecasts = []
        for module in sorted(listdir(f"{dirname(__file__)}")):
            mod_path = f"{dirname(__file__)}/{module}"
            if (
                isdir(mod_path)
                and not module.endswith("__pycache__")
                and not mod_path.endswith(".disabled")
            ):
                Endpoint = namedtuple("Endpoint", "module namespace regions")
                _LOGGER.debug("Adding module %s", module)
                api_ns = f".{module}"
                mod = import_module(api_ns, __name__)
                con = Endpoint(module, f".forecasts{api_ns}", mod.REGIONS)

                if hasattr(mod, "EXTRA_REGIONS"):
                    REGIONS.update(mod.EXTRA_REGIONS)

                if hasattr(mod, "EXTRA_CURRENCIES"):
                    CURRENCY_LIST.update(mod.EXTRA_CURRENCIES)

                self._forecasts.append(con)

    @property
    def forecast_endpoints(self) -> list:
        """Return valid forecast endpoints."""
        return self._forecasts

    def get_endpoint(self, region: str) -> list:
        """Get endpoint(s) of a specific zone."""
        endpoints = []

        for endpoint in self._forecasts:
            if region in endpoint.regions:
                ForecastEndpoint = namedtuple("Forecast", "module namespace")
                endpoints.append(ForecastEndpoint(endpoint.module, endpoint.namespace))

        return endpoints
