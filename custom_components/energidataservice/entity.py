"""Base class for Energi Data Service entity."""
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, AREA_TO_TEXT


class EnergidataserviceEntity(Entity):
    """Base implementation for Energi Data Service."""

    def __init__(self, name, area):
        """Initialize Energi Data Service."""
        super().__init__()
        self._name = name
        self._area = area

    @property
    def device_info(self):
        """Return the device_info of the device."""
        return {
            "identifiers": {(DOMAIN, self._area)},
            "name": self._name,
            "manufacturer": None,
            "model": f"Spot prices {AREA_TO_TEXT[self._area]} ({self._area})",
        }

    @property
    def should_poll(self):
        """Do not poll."""
        return True
