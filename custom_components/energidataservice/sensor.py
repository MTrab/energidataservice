"""Support for Ally sensors."""
import logging

from homeassistant.const import (
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_HUMIDITY,
    PERCENTAGE,
    TEMP_CELSIUS,

)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import (
    DATA,
    DOMAIN,
    SIGNAL_ALLY_UPDATE_RECEIVED,
)
from .entity import AllyDeviceEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    """Set up the Ally binary_sensor platform."""
    _LOGGER.debug("Setting up Danfoss Ally sensor entities")
    ally = hass.data[DOMAIN][entry.entry_id][DATA]
    entities = []

    for device in ally.devices:
        for sensor_type in ['battery', 'temperature', 'humidity']:
            if sensor_type in ally.devices[device]:
                _LOGGER.debug(f"Found {sensor_type} sensor for {ally.devices[device]['name']}")
                entities.extend(
                    [
                        AllySensor(
                            ally,
                            ally.devices[device]["name"],
                            device,
                            sensor_type
                        )
                    ]
                )

    if entities:
        async_add_entities(entities, True)


class AllySensor(AllyDeviceEntity):
    """Representation of an Ally sensor."""

    def __init__(self, ally, name, device_id, device_type):
        """Initialize Ally binary_sensor."""
        self._ally = ally
        self._device = ally.devices[device_id]
        self._device_id = device_id
        self._type = device_type
        super().__init__(name, device_id, device_type)

        _LOGGER.debug(
            "Device_id: %s --- Device: %s",
            self._device_id,
            self._device
        )

        self._type = device_type

        self._unique_id = f"{device_type}_{device_id}_ally"

        self._state = None
        self._state_attributes = None

        if self._type == "battery":
            self._state = self._device['battery']
        elif self._type == "temperature":
            self._state = self._device['temperature']
        elif self._type == "humidity":
            self._state = self._device['humidity']

    async def async_added_to_hass(self):
        """Register for sensor updates."""

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                SIGNAL_ALLY_UPDATE_RECEIVED,
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
        return f"{self._name} {self._type}"

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
        if self._type == "battery":
            return PERCENTAGE
        elif self._type == "temperature":
            return TEMP_CELSIUS
        elif self._type == "humidity":
            return PERCENTAGE
        return None

    @property
    def device_class(self):
        """Return the class of this sensor."""
        if self._type == "battery":
            return DEVICE_CLASS_BATTERY
        elif self._type == "temperature":
            return DEVICE_CLASS_TEMPERATURE
        elif self._type == "humidity":
            return DEVICE_CLASS_HUMIDITY
        return None

    @callback
    def _async_update_callback(self):
        """Update and write state."""
        self._async_update_data()
        self.async_write_ha_state()

    @callback
    def _async_update_data(self):
        """Load data."""
        _LOGGER.debug(
            "Loading new sensor data for device %s",
            self._device_id
        )
        self._device = self._ally.devices[self._device_id]

        if self._type == "battery":
            self._state = self._device['battery']
        elif self._type == "temperature":
            self._state = self._device['temperature']
        elif self._type == "humidity":
            self._state = self._device['humidity']
