"""For handling tariffs."""

from __future__ import annotations

import logging
from importlib import import_module

from ..tariffs import Tariff

_LOGGER = logging.getLogger(__name__)


class TariffHandler:
    """Tariff handler."""

    @staticmethod
    async def get_chargeowners(
        region: str, hass, sort: bool = False, descending: bool = False
    ) -> list:
        """Get a list of chargeowners for this region."""
        chargeowners = []
        connectors = await Tariff(hass=hass).get_endpoint(region)
        _LOGGER.debug("Tariff connectors: %s", connectors)
        for endpoint in connectors:
            _LOGGER.debug("Getting chargeowner from '%s'", endpoint.namespace)
            module = await hass.async_add_executor_job(
                import_module, f"..{endpoint.namespace}", __name__
            )
            for chargeowner in module.CHARGEOWNERS:
                chargeowners.append(chargeowner)

        return chargeowners if not sort else sorted(chargeowners, reverse=descending)
