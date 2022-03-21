"""Adds support for Energidatastyrelsen spot prices."""
from datetime import timedelta
import logging
import asyncio
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import async_track_time_interval
#from homeassistant.util import Throttle

from .api import Energidatastyrelsen

from .const import (
    CONF_AREA,
    DATA,
    DOMAIN,
    SIGNAL_ENERGIDATASTYRELSEN_UPDATE_RECEIVED,
    UPDATE_LISTENER,
    UPDATE_TRACK,
)

LOADED_COMPONENTS = ["sensor"]

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = 15

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [
                {
                    vol.Required(CONF_AREA): cv.string,
                }
            ],
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up Energidatastyrelsen component."""

    hass.data.setdefault(DOMAIN, {})

    if DOMAIN not in config:
        return True

    for conf in config[DOMAIN]:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=conf,
            )
        )

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Energidatastyrelsen from a config entry."""

    area = entry.data[CONF_AREA]

    eds_connector = EDSConnector(hass, area)

    await hass.async_add_executor_job(eds_connector.update)

    update_track = async_track_time_interval(
        hass,
        lambda now: eds_connector.update(),
        timedelta(seconds=SCAN_INTERVAL),
    )

    update_listener = entry.add_update_listener(_async_update_listener)

    hass.data[DOMAIN][entry.entry_id] = {
        DATA: eds_connector,
        UPDATE_TRACK: update_track,
        UPDATE_LISTENER: update_listener,
    }

    for component in LOADED_COMPONENTS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True

async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in LOADED_COMPONENTS
            ]
        )
    )

    hass.data[DOMAIN][entry.entry_id][UPDATE_TRACK]()
    hass.data[DOMAIN][entry.entry_id][UPDATE_LISTENER]()

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class EDSConnector:
    """An object to store the Danfoss Ally data."""

    def __init__(self, hass, area):
        """Initialize Danfoss Ally Connector."""
        self.hass = hass
        self._area = area
        self.eds = Energidatastyrelsen(self._area)

    def update(self, now=None):
        """Fetch latest prices from Energidatastyrelsen API"""
        _LOGGER.debug("Updating Energidatastyrelsen sensors")
        self.eds.get_spotprices()

        dispatcher_send(self.hass, SIGNAL_ENERGIDATASTYRELSEN_UPDATE_RECEIVED)
