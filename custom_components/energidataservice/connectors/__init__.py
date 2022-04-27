"""Dynamically load all available connectors."""
from __future__ import annotations

from collections import namedtuple
from os import listdir
from posixpath import dirname
from importlib import import_module
from logging import getLogger
from genericpath import isdir

from ..const import CURRENCY_LIST, REGIONS

_LOGGER = getLogger(__name__)


class Connectors:
    """Handle connector modules."""

    def __init__(self):
        """Initialize connector handler."""

        self._connectors = []
        for module in listdir(f"{dirname(__file__)}"):
            mod_path = f"{dirname(__file__)}/{module}"
            if isdir(mod_path) and not module.endswith("__pycache__"):
                Connector = namedtuple("Connector", "module namespace regions")
                _LOGGER.debug("Adding module %s", module)
                api_ns = f".{module}"
                mod = import_module(api_ns, __name__)
                con = Connector(module, f".connectors{api_ns}", mod.REGIONS)

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
            if region in connector.regions:
                Connector = namedtuple("Connector", "module namespace")
                connectors.append(Connector(connector.module, connector.namespace))

        return connectors
