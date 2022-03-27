"""Adds support for Energi Data Service spot prices."""
import logging

from random import randint
from pytz import timezone

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_change

from .events import async_track_time_change_in_tz

from .api import Energidataservice
from .const import (
    AREA_MAP,
    CONF_AREA,
    CONF_VAT,
    CONF_DECIMALS,
    CONF_TEMPLATE,
    CONF_PRICETYPE,
    DOMAIN,
    UPDATE_EDS,
    REGIONS,
    PRICE_TYPES,
)

RANDOM_MINUTE = randint(0, 10)
RANDOM_SECOND = randint(0, 59)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(
            CONF_AREA,
            default=None,
        ): vol.In(REGIONS),
        vol.Required(CONF_VAT, default=True): bool,
        vol.Optional(CONF_DECIMALS, default=3): vol.Coerce(int),
        vol.Optional(CONF_PRICETYPE, default="kWh"): vol.In(PRICE_TYPES),
        vol.Optional(CONF_TEMPLATE, default=""): str,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Energi Data Service from a config entry."""
    _LOGGER.debug("Entry data: %s", entry.data)
    result = await _setup(hass, entry.data)

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    return result


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")

    if unload_ok:
        for unsub in hass.data[DOMAIN].listeners:
            unsub()
        hass.data.pop(DOMAIN)

        return True

    return False


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def _setup(hass: HomeAssistant, config: Config) -> bool:
    """Setup the integration using a config entry."""

    if DOMAIN not in hass.data:
        api = EDSConnector(hass, AREA_MAP[config.get(CONF_AREA)])
        hass.data[DOMAIN] = api

        # await api.update()

        async def new_day(indata):
            """Handle data on new day."""
            _LOGGER.debug("New day function called")
            api.today = api.tomorrow
            api.tomorrow = None
            api._tomorrow_valid = False
            async_dispatcher_send(hass, UPDATE_EDS)

        async def new_hour(indata):
            """Callback to tell the sensors to update on a new hour."""
            _LOGGER.debug("New hour, updating state")
            async_dispatcher_send(hass, UPDATE_EDS)

        async def get_new_data(indata):
            """Fetch new data for tomorrows prices at 1300 CET."""
            _LOGGER.debug("Getting latest dataset")
            await api.update()
            async_dispatcher_send(hass, UPDATE_EDS)

        # Handle dataset updates
        update_tomorrow = async_track_time_change_in_tz(
            hass,
            get_new_data,
            hour=13,
            minute=RANDOM_MINUTE,
            second=RANDOM_SECOND,
            tz=timezone("Europe/Copenhagen"),
        )

        # update_new_day = async_track_time_change(
        #     hass, new_day, hour=0, minute=0, second=0
        # )

        update_new_hour = async_track_time_change(hass, new_hour, minute=0, second=0)

        api.listeners.append(update_tomorrow)
        api.listeners.append(update_new_hour)
        # api.listeners.append(update_new_day)

        return True


class EDSConnector:
    """An object to store Energi Data Service data."""

    def __init__(self, hass, area):
        """Initialize Energi Data Service Connector."""
        self._hass = hass
        self._last_tick = None
        self._tomorrow_valid = False
        self.today = None
        self.tomorrow = None
        self.listeners = []
        # self.data = defaultdict(dict)
        client = async_get_clientsession(hass)
        self._eds = Energidataservice(area, client, hass.config.time_zone)
        _LOGGER.debug("Initializing Energi Data Service for area %s", area)

    async def update(self, dt=None):
        """Fetch latest prices from Energi Data Service API"""
        eds = self._eds

        await eds.get_spotprices()
        # data = eds.raw_data
        self.today = eds.today
        self.tomorrow = eds.tomorrow

        if not self.tomorrow:
            self._tomorrow_valid = False
            self.tomorrow = None
        else:
            self._tomorrow_valid = True

        # if data:
        #     self.data["json"] = data
        # else:
        #     _LOGGER.warning(
        #         "Couldn't get data from Energi Data Service, retrying later."
        #     )
        #     async_call_later(hass, 60, partial(self.update))

    @property
    def tomorrow_valid(self):
        """Is tomorrows prices valid?"""
        return self._tomorrow_valid