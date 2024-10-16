"""Dynamically load all available connectors."""

from __future__ import annotations

import importlib
from asyncio import get_running_loop
from collections import namedtuple
from logging import getLogger
from os import listdir
from posixpath import dirname

from genericpath import isdir

from ..const import CURRENCY_LIST, REGIONS

_LOGGER = getLogger(__name__)


class Connectors:
    """Handle connector modules."""

    def __init__(self, hass):
        """Initialize connector handler."""

        self.hass = hass
        self._connectors = []

    async def load_connectors(self) -> None:
        """Load available connectors."""
        loop = get_running_loop()
        modules = await loop.run_in_executor(None, listdir, f"{dirname(__file__)}")
        for module in sorted(modules):
            mod_path = f"{dirname(__file__)}/{module}"
            if isdir(mod_path) and not module.endswith("__pycache__"):
                Connector = namedtuple(
                    "Connector", "module namespace regions co2regions"
                )
                _LOGGER.debug("Adding module %s in path %s", module, mod_path)
                api_ns = f".{module}"

                mod = await self.hass.async_add_executor_job(
                    importlib.import_module, api_ns, __name__
                )
                con = Connector(
                    module, f".connectors{api_ns}", mod.REGIONS, mod.CO2REGIONS
                )

                if hasattr(mod, "EXTRA_REGIONS"):
                    REGIONS.update(mod.EXTRA_REGIONS)

                if hasattr(mod, "EXTRA_CURRENCIES"):
                    CURRENCY_LIST.update(mod.EXTRA_CURRENCIES)

                self._connectors.append(con)

    @property
    def connectors(self) -> list:
        """Return valid connectors."""
        return self._connectors

    def get_connectors(self, region: str) -> list:
        """Get connector(s) of a specific zone."""
        connectors = []

        for connector in self._connectors:
            _LOGGER.debug("%s = %s", connector, connector.regions)
            if region in connector.regions:
                Connector = namedtuple("Connector", "module namespace co2regions")
                connectors.append(
                    Connector(
                        connector.module, connector.namespace, connector.co2regions
                    )
                )

        return connectors
