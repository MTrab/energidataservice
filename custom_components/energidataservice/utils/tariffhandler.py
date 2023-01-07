"""For handling tariffs."""
from __future__ import annotations

from importlib import import_module
import logging

from ..tariffs import Tariff

_LOGGER = logging.getLogger(__name__)


class TariffHandler:
    """Tariff handler."""

    @staticmethod
    def get_chargeowners(
        region: str, sort: bool = False, descending: bool = False
    ) -> list:
        """Get a list of chargeowners for this region."""
        chargeowners = []
        connectors = Tariff().get_endpoint(region)
        _LOGGER.debug("Tariff connectors: %s", connectors)
        for endpoint in connectors:
            _LOGGER.debug("Getting chargeowner from '%s'", endpoint.namespace)
            module = import_module(f"..{endpoint.namespace}", __name__)
            chargeowners += module.CHARGEOWNERS

        return chargeowners if not sort else sorted(chargeowners, reverse=descending)
