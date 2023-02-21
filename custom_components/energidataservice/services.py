"""Services for debugging."""
# pylint: disable=protected-access
from __future__ import annotations

from dataclasses import dataclass
from logging import getLogger

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.device_registry import DeviceEntry
import voluptuous as vol

from .api import APIConnector
from .const import (
    DOMAIN,
    SERVICE_RELOAD_DATA,
    SERVICE_RELOAD_DAY,
    SERVICE_RELOAD_HOUR,
    UPDATE_EDS,
)

EMPTY_SCHEME = vol.All(cv.make_entity_service_schema({}))

_LOGGER = getLogger(__name__)


@dataclass
class EDSServiceDescription:
    """A class that describes Home Assistant entities."""

    # This is the key identifier for this entity
    key: str
    schema: str = EMPTY_SCHEME


SUPPORTED_SERVICES = [
    EDSServiceDescription(key=SERVICE_RELOAD_HOUR, schema=EMPTY_SCHEME),
    EDSServiceDescription(key=SERVICE_RELOAD_DAY, schema=EMPTY_SCHEME),
    EDSServiceDescription(key=SERVICE_RELOAD_DATA, schema=EMPTY_SCHEME),
]


@callback
async def async_setup_services(hass: HomeAssistant, config: ConfigEntry) -> None:
    """Set up services for Landroid Cloud integration."""

    async def async_call_service(service_call: ServiceCall) -> None:
        """Call day update routine."""
        service = service_call.service
        service_data = service_call.data
        _LOGGER.debug(service)

        device_registry = dr.async_get(hass)
        entity_registry = er.async_get(hass)

        devices: DeviceEntry = []

        if CONF_DEVICE_ID in service_data:
            if isinstance(service_data[CONF_DEVICE_ID], str):
                devices.append(device_registry.async_get(service_data[CONF_DEVICE_ID]))
            else:
                for entry in service_data[CONF_DEVICE_ID]:
                    devices.append(device_registry.async_get(entry))
        else:
            for entry in service_data[CONF_ENTITY_ID]:
                devices.append(
                    device_registry.async_get(
                        entity_registry.entities.get(entry).device_id
                    )
                )

        for device in devices:
            entry_id = list(device.config_entries)[0]
            api: APIConnector = hass.data[DOMAIN][entry_id]

            if service == SERVICE_RELOAD_HOUR:
                _LOGGER.debug("Forcing new hour state update")
            elif service == SERVICE_RELOAD_DAY:
                _LOGGER.debug("Forcing new day states")

                await api.async_get_tariffs()

                api.today = api.api_tomorrow
                api.today_calculated = False
                api.api_today = api.api_tomorrow
                api.tomorrow = None
                api.api_tomorrow = None
                api._tomorrow_valid = False  # pylint: disable=protected-access
                api.tomorrow_calculated = False
            elif service == SERVICE_RELOAD_DATA:
                _LOGGER.debug("Forcing data refresh from API endpoint(s)")
                await api.update()
                await api.update_carnot()

            async_dispatcher_send(hass, UPDATE_EDS.format(entry_id))

    for service in SUPPORTED_SERVICES:
        if not hass.services.has_service(DOMAIN, service.key):
            _LOGGER.debug("Adding %s", service.key)
            hass.services.async_register(
                DOMAIN, service.key, async_call_service, schema=service.schema
            )
