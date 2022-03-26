"""Adds support for Energi Data Service spot prices."""
from datetime import timedelta, datetime, time
import logging
import asyncio
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.event import async_track_time_interval

# from homeassistant.util import Throttle

from .api import Energidataservice

from .const import (
    CONF_AREA,
    CONF_VAT,
    CONF_DECIMALS,
    AREA_EAST,
    AREA_WEST,
    AREA_MAP,
    DATA,
    DOMAIN,
    SIGNAL_ENERGIDATASERVICE_UPDATE_RECEIVED,
    UPDATE_LISTENER,
    UPDATE_TRACK,
)

LOADED_COMPONENTS = ["sensor"]

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = 60

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_AREA,
            default=AREA_WEST,
        ): vol.In([AREA_WEST, AREA_EAST]),
        vol.Required(CONF_VAT, default=True): bool,
        vol.Optional(CONF_DECIMALS, default=3): vol.Coerce(int),
    }
)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up Energi Data Service component."""

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
    """Set up Energi Data Service from a config entry."""

    area = AREA_MAP[entry.data[CONF_AREA]]

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
    """An object to store Energi Data Service data."""

    def __init__(self, hass, area):
        """Initialize Energi Data Service Connector."""
        self.hass = hass
        self._area = area
        self._last_update = 0
        self._next_update = 0
        self._json = {}
        _LOGGER.debug("Setting up sensor for area %s", area)
        self.eds = Energidataservice(self._area)

    def update(self, now=None):
        """Fetch latest prices from Energi Data Service API"""
        ts_now = int(datetime.now().timestamp())
        if ts_now > self._next_update:
            _LOGGER.debug("Updating Energi Data Service data")
            self.eds.get_spotprices()
            self._json = self.eds.raw_data
            self._last_update = ts_now
            self._next_update = int(
                (
                    datetime.combine(
                        datetime.today(), datetime.strptime("13:00", "%H:%M").time()
                    )
                ).timestamp()
            )
        else:
            _LOGGER.debug(
                "Skipping data refresh, last refresh: %s - next refresh: %s",
                datetime.fromtimestamp(self._last_update).strftime("%d-%m-%Y %H:%M"),
                datetime.fromtimestamp(self._next_update).strftime("%d-%m-%Y %H:%M"),
            )

        dispatcher_send(self.hass, SIGNAL_ENERGIDATASERVICE_UPDATE_RECEIVED)
