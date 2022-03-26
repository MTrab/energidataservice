"""Support for Ally sensors."""
import logging

from homeassistant.const import (
    DEVICE_CLASS_MONETARY,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    DATA,
    DOMAIN,
    SIGNAL_ENERGIDATASERVICE_UPDATE_RECEIVED,
)
from .entity import EnergidataserviceEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up the Energi Data Service sensor platform."""
    _LOGGER.debug("Setting up Energi Data Service sensor")
    eds = hass.data[DOMAIN][entry.entry_id][DATA]
    entities = []

    entities.extend([EnergidataserviceSensor(eds)])
    async_add_entities(entities, True)


class EnergidataserviceSensor(EnergidataserviceEntity):
    """Representation of Energi Data Service data."""

    def __init__(self, eds):
        """Initialize Ally binary_sensor."""
        self.eds = eds
        self._name = f"Energi Data Service {eds._area}"
        super().__init__(self._name, eds._area)

        self._unique_id = f"energidataservice_data_{eds._area}"

        self._state = None
        self._state_attributes = None

        self._async_update_data()

    async def async_added_to_hass(self):
        """Register for sensor updates."""

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_ENERGIDATASERVICE_UPDATE_RECEIVED,
                self._async_update_callback,
            )
        )

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name}"

    @property
    def state(self):
        """Return sensor state."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._state_attributes

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "DKK"

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return DEVICE_CLASS_MONETARY

    @callback
    def _async_update_callback(self):
        """Update and write state."""
        self._async_update_data()
        self.async_write_ha_state()

    @callback
    def _async_update_data(self):
        """Load data."""
        _LOGGER.debug("Updating sensor")
        self._state = self.eds.eds.current
        # _LOGGER.debug()
