"""Adds support for Energi Data Service spot prices."""
from __future__ import annotations

from datetime import datetime, timedelta
from functools import partial
from importlib import import_module
import json
from logging import getLogger
from random import randint

from aiohttp import ServerDisconnectedError
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_time_change,
    async_track_utc_time_change,
)
from homeassistant.loader import async_get_integration

from .connectors import Connectors
from .const import (
    CONF_AREA,
    CONF_ENABLE_FORECAST,
    CONF_ENABLE_TARIFFS,
    CONF_TARIFF_CHARGE_OWNER,
    DOMAIN,
    STARTUP,
    UPDATE_EDS,
)
from .forecasts import Forecast
from .tariffs import Tariff
from .utils.regionhandler import RegionHandler

RANDOM_MINUTE = randint(5, 40)
RANDOM_SECOND = randint(0, 59)

RETRY_MINUTES = 5
MAX_RETRY_MINUTES = 60

CARNOT_UPDATE = timedelta(minutes=30)

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
    """Setup the integration using a config entry."""
    integration = await async_get_integration(hass, DOMAIN)
    _LOGGER.info(STARTUP, integration.version)

    api = APIConnector(
        hass,
        entry,
    )
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
        async_dispatcher_send(hass, UPDATE_EDS)

    async def new_hour(n):  # type: ignore pylint: disable=unused-argument, invalid-name
        """Callback to tell the sensors to update on a new hour."""
        _LOGGER.debug("New hour, updating state")
        async_dispatcher_send(hass, UPDATE_EDS)

    async def get_new_data(n):  # type: ignore pylint: disable=unused-argument, invalid-name
        """Fetch new data for tomorrows prices at 13:00ish CET."""
        _LOGGER.debug("Getting latest dataset")
        await api.update()
        await api.update_carnot()
        async_dispatcher_send(hass, UPDATE_EDS)

    async def update_carnot(n):  # type: ignore pylint: disable=unused-argument, invalid-name
        """Fetch new data from Carnot every 30 minutes."""
        _LOGGER.debug("Getting latest Carnot forecast")
        await api.update_carnot()

        async_call_later(hass, CARNOT_UPDATE, update_carnot)
        async_dispatcher_send(hass, UPDATE_EDS)

    # Handle dataset updates
    update_tomorrow = async_track_utc_time_change(
        hass,
        get_new_data,
        hour=12,  # UTC time!!
        minute=RANDOM_MINUTE,
        second=RANDOM_SECOND,
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

    return True


class APIConnector:
    """An object to store Energi Data Service data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize Energi Data Service Connector."""
        self._connectors = Connectors()
        self.forecasts = Forecast()
        self.tariffs = Tariff()
        self.hass = hass
        self._last_tick = None
        self._tomorrow_valid = False
        self._entry_id = entry.entry_id
        self._config = entry

        self.today = None
        self.api_today = None
        self.tomorrow = None
        self.api_tomorrow = None
        self.today_calculated = False
        self.tomorrow_calculated = False
        self.predictions = None
        self.api_predictions = None
        self.tariff_data = None
        self.predictions_calculated = False
        self.predictions_currency = None
        self.connector_currency = "EUR"
        self.forecast_currency = "EUR"
        self.listeners = []

        self.next_retry_delay = RETRY_MINUTES
        self.retry_count = 0

        self._client = async_get_clientsession(hass)
        self._region = RegionHandler(
            (entry.options.get(CONF_AREA) or entry.data.get(CONF_AREA)) or "FIXED"
        )
        self._tz = hass.config.time_zone
        self._source = None
        self.forecast = entry.options.get(CONF_ENABLE_FORECAST) or False
        self.tariff = entry.options.get(CONF_ENABLE_TARIFFS) or False
        self._carnot_user = entry.options.get(CONF_EMAIL) or None
        self._carnot_apikey = entry.options.get(CONF_API_KEY) or None

    async def update(self, dt=None) -> None:  # type: ignore pylint: disable=unused-argument,invalid-name
        """Fetch latest prices from API"""
        _LOGGER.debug("Updating data for '%s'", self._region.region)
        connectors = self._connectors.get_connectors(self._region.region)
        _LOGGER.debug(
            "Valid connectors for '%s' is: %s", self._region.region, connectors
        )
        self.today = None
        self.tomorrow = None
        self.today_calculated = False
        self.tomorrow_calculated = False

        self.tariff_data = None

        try:
            for endpoint in connectors:
                module = import_module(endpoint.namespace, __name__)
                api = module.Connector(
                    self._region, self._client, self._tz, self._config
                )
                self.connector_currency = module.DEFAULT_CURRENCY
                await api.async_get_spotprices()
                if api.today and not self.today:
                    self.today = api.today
                    self.api_today = api.today
                    _LOGGER.debug(
                        "%s got values from %s (namespace='%s')",
                        self._region.region,
                        endpoint.module,
                        endpoint.namespace,
                    )
                    self._source = module.SOURCE_NAME

                if api.tomorrow and not self.tomorrow:
                    self.today = api.today
                    self.api_today = api.today
                    self.tomorrow = api.tomorrow
                    self.api_tomorrow = api.tomorrow

                    _LOGGER.debug(
                        "%s got values from %s (namespace='%s')",
                        self._region.region,
                        endpoint.module,
                        endpoint.namespace,
                    )

                    self._source = module.SOURCE_NAME
                    break

            if (not self.tomorrow or not self.api_tomorrow) or (
                self.tomorrow is None or self.api_tomorrow is None
            ):
                _LOGGER.debug("No data found for tomorrow")
                self._tomorrow_valid = False
                self.tomorrow = None
                self.api_tomorrow = None

                midnight = datetime.strptime("23:59:59", "%H:%M:%S")
                refresh = datetime.strptime(self.next_data_refresh, "%H:%M:%S")
                now = datetime.utcnow()

                _LOGGER.debug(
                    "Now: %s:%s:%s (UTC)",
                    f"{now.hour:02d}",
                    f"{now.minute:02d}",
                    f"{now.second:02d}",
                )
                _LOGGER.debug(
                    "Refresh: %s:%s:%s (local time)",
                    f"{refresh.hour:02d}",
                    f"{refresh.minute:02d}",
                    f"{refresh.second:02d}",
                )
                if (
                    f"{midnight.hour}:{midnight.minute}:{midnight.second}"
                    > f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}"
                    and f"{refresh.hour:02d}:{refresh.minute:02d}:{refresh.second:02d}"
                    <= f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}"
                ):
                    retry_update(self)
                else:
                    _LOGGER.debug(
                        "Not forcing refresh, as we are past midnight and haven't reached next update time"  # pylint: disable=line-too-long
                    )
            else:
                _LOGGER.debug(
                    "Tomorrow:\n%s", json.dumps(self.tomorrow, indent=2, default=str)
                )
                self.retry_count = 0
                self._tomorrow_valid = True

            await self.async_get_tariffs()
        except ServerDisconnectedError:
            _LOGGER.warning("Err.")
            retry_update(self)

    async def update_carnot(self, dt=None) -> None:  # type: ignore pylint: disable=unused-argument,invalid-name
        """Update Carnot data if enabled."""
        if self.forecast:
            self.predictions_calculated = False
            forecast_endpoint = self.forecasts.get_endpoint(self._region.region)
            forecast_module = import_module(forecast_endpoint[0].namespace, __name__)
            carnot = forecast_module.Connector(self._region, self._client, self._tz)
            self.predictions_currency = forecast_module.DEFAULT_CURRENCY
            self.predictions = await carnot.async_get_forecast(
                self._carnot_apikey, self._carnot_user
            )

            self.predictions[:] = (
                value
                for value in self.predictions
                if value.hour.day >= (datetime.now() + timedelta(days=1)).day
                or value.hour.month > (datetime.now() + timedelta(days=1)).month
                or value.hour.year > datetime.now().year
            )

            if self._tomorrow_valid:
                # Remove tomorrows predictions, as we have the actual values
                self.predictions[:] = (
                    value
                    for value in self.predictions
                    if value.hour.day != (datetime.now() + timedelta(days=1)).day
                )

            self.api_predictions = self.predictions

    async def async_get_tariffs(self) -> None:
        """Get tariff data."""
        if self.tariff:
            tariff_endpoint = self.tariffs.get_endpoint(self._region.region)
            tariff_module = import_module(tariff_endpoint[0].namespace, __name__)
            tariff = tariff_module.Connector(
                self.hass,
                self._client,
                self._config.options.get(CONF_TARIFF_CHARGE_OWNER),
            )

            self.tariff_data = await tariff.async_get_tariffs()

    @property
    def tomorrow_valid(self) -> bool:
        """Is tomorrows prices valid?"""
        return self._tomorrow_valid

    @property
    def source(self) -> str:
        """Who was the source for the data?"""
        return self._source

    @property
    def next_data_refresh(self) -> str:
        """When is next data update?"""
        return f"13:{RANDOM_MINUTE:02d}:{RANDOM_SECOND:02d}"

    @property
    def entry_id(self) -> str:
        """Return entry_id."""
        return self._entry_id


def retry_update(self) -> None:
    """Retry update on error."""
    self.retry_count += 1
    self.next_retry_delay = RETRY_MINUTES * self.retry_count
    if self.next_retry_delay > MAX_RETRY_MINUTES:
        self.next_retry_delay = MAX_RETRY_MINUTES

    _LOGGER.warning(
        "Couldn't get data from Energi Data Service, retrying in %s minutes.",
        self.next_retry_delay,
    )

    now = datetime.utcnow() + timedelta(minutes=self.next_retry_delay)
    _LOGGER.debug(
        "Next retry: %s:%s:%s (UTC)",
        f"{now.hour:02d}",
        f"{now.minute:02d}",
        f"{now.second:02d}",
    )
    async_call_later(
        self.hass,
        timedelta(minutes=self.next_retry_delay),
        partial(self.update),
    )
