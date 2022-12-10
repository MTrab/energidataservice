"""Dynamically load all available tariff providers."""
from __future__ import annotations

from collections import namedtuple
from importlib import import_module
from logging import getLogger
from os import listdir
from posixpath import dirname

from genericpath import isdir

_LOGGER = getLogger(__name__)


class Forecast:
    """Handle tariff modules."""

    def __init__(self):
        """Initialize tariff handler."""

        self._tariffs = []
        for module in sorted(listdir(f"{dirname(__file__)}")):
            mod_path = f"{dirname(__file__)}/{module}"
            if (
                isdir(mod_path)
                and not module.endswith("__pycache__")
                and not mod_path.endswith(".disabled")
            ):
                Endpoint = namedtuple("Endpoint", "module namespace config_scheme")
                _LOGGER.debug("Adding module %s", module)
                api_ns = f".{module}"
                mod = import_module(api_ns, __name__)
                con = Endpoint(module, f".tariffs{api_ns}", mod.config_scheme)

                self._tariffs.append(con)

    @property
    def tariff_endpoints(self) -> list:
        """Return valid tariff endpoints."""
        return self._tariffs
