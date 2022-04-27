"""Dynamically load all connectors."""
# from os.path import dirname, basename, isfile, join
# import glob

# modules = glob.glob(join(dirname(__file__), "*.py"))
# __all__ = [
#     basename(f)[:-3] for f in modules if isfile(f) and not f.endswith("__init__.py")
# ]
# import os

# for module in os.listdir(os.path.dirname(__file__)):
#     if module == "__init__.py" or module[-3:] != ".py":
#         continue
#     __import__(module[:-3], locals(), globals())
# del module


import importlib
import logging
import os

from collections import namedtuple

_LOGGER = logging.getLogger(__name__)


class Connectors:
    """Handle connector modules."""

    def __init__(self):
        """Initialize connector handler."""

        self._connectors = []
        for module in os.listdir(f"{os.path.dirname(__file__)}"):
            mod_path = f"{os.path.dirname(__file__)}/{module}"
            if os.path.isdir(mod_path) and not module.endswith("__pycache__"):
                Connector = namedtuple("Connector", "module namespace regions")
                _LOGGER.debug("Adding module %s", module)
                api_ns = f".{module}"
                mod = importlib.import_module(api_ns, __name__)
                con = Connector(module, f".connectors{api_ns}", mod.REGIONS)

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
