"""Adds support for Energi Data Service spot prices."""

from __future__ import annotations

from datetime import timedelta
from logging import getLogger
from random import randint

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_call_later, async_track_time_change
from homeassistant.loader import async_get_integration

from .api import APIConnector
from .const import CONF_ENABLE_FORECAST, DOMAIN, STARTUP, UPDATE_EDS

RETRY_MINUTES = 5
MAX_RETRY_MINUTES = 60

CARNOT_UPDATE = timedelta(minutes=30)

DEBUG = False

_LOGGER = getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the component."""

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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Energi Data Service from a config entry."""
    _LOGGER.debug("Entry data: %s", entry.data)
    _LOGGER.debug("Entry options: %s", entry.options)
    result = await _setup(hass, entry)

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    return result


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")

    if unload_ok:
        for unsub in hass.data[DOMAIN][entry.entry_id].listeners:
            unsub()
        hass.data[DOMAIN].pop(entry.entry_id)

        return True

    return False


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def _setup(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Do the integration setup from a config entry."""
    integration = await async_get_integration(hass, DOMAIN)
    _LOGGER.info(STARTUP, integration.version)
    rand_min = randint(5, 40)
    rand_sec = randint(0, 59)
    api = APIConnector(hass, entry, rand_min, rand_sec)
    hass.data[DOMAIN][entry.entry_id] = api
    use_forecast = entry.options.get(CONF_ENABLE_FORECAST) or False

    async def new_day(n):  # type: ignore pylint: disable=unused-argument, invalid-name
        """Handle data on new day."""
        _LOGGER.debug("New day function called")

        api.today = api.api_tomorrow
        api.today_calculated = False
        api.api_today = api.api_tomorrow
        api.tomorrow = None
        api.api_tomorrow = None
        api._tomorrow_valid = False  # pylint: disable=protected-access
        api.tomorrow_calculated = False
        async_dispatcher_send(hass, UPDATE_EDS.format(entry.entry_id))

    async def new_hour(n):  # type: ignore pylint: disable=unused-argument, invalid-name
        """Tell the sensor to update to a new hour."""
        _LOGGER.debug("New hour, updating state")
        async_dispatcher_send(hass, UPDATE_EDS.format(entry.entry_id))

    async def get_new_data(n):  # type: ignore pylint: disable=unused-argument, invalid-name
        """Fetch new data for tomorrows prices at 13:00ish CET."""
        _LOGGER.debug("Getting latest dataset")
        await api.update()
        await api.update_carnot()
        await api.async_get_tariffs()

        async_dispatcher_send(hass, UPDATE_EDS.format(entry.entry_id))

    async def update_carnot(n):  # type: ignore pylint: disable=unused-argument, invalid-name
        """Fetch new data from Carnot every 30 minutes."""
        _LOGGER.debug("Getting latest Carnot forecast")
        await api.update_carnot()

        async_call_later(hass, CARNOT_UPDATE, update_carnot)
        async_dispatcher_send(hass, UPDATE_EDS.format(entry.entry_id))

    # Handle dataset updates
    update_tomorrow = async_track_time_change(
        hass,
        get_new_data,
        hour=13,  # LOCAL time!!
        minute=rand_min,
        second=rand_sec,
    )

    update_new_day = async_track_time_change(
        hass,
        new_day,
        hour=0,  # LOCAL time!!
        minute=0,
        second=0,
    )

    update_new_hour = async_track_time_change(hass, new_hour, minute=0, second=1)

    if use_forecast:
        async_call_later(hass, CARNOT_UPDATE, update_carnot)

    api.listeners.append(update_new_day)
    api.listeners.append(update_new_hour)
    api.listeners.append(update_tomorrow)

    await api.async_get_tariffs()

    return True
