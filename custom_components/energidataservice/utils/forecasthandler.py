"""For handling forecasts."""

from __future__ import annotations

import logging

from ..forecasts import Forecast

_LOGGER = logging.getLogger(__name__)


class ForecastHandler:
    """Forecast handler."""

    @staticmethod
    def get_forecasts_connectors(
        region: str, sort: bool = False, descending: bool = False
    ) -> list:
        """Get a list of forecast connectors for this region."""
        connectors = Forecast().get_endpoint(region)
        _LOGGER.debug("Forecast connectors: %s", connectors)

        return connectors
