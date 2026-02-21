"""EDS API."""

from __future__ import annotations

import datetime
import json
from functools import partial
from importlib import import_module
from logging import getLogger

import homeassistant.util.dt as dt_util
import voluptuous as vol
from aiohttp import ClientConnectorError, ServerDisconnectedError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later
from pytz import timezone

from .connectors import Connectors
from .const import (
    CONF_AREA,
    CONF_ENABLE_FORECAST,
    CONF_ENABLE_TARIFFS,
    CONF_TARIFF_CHARGE_OWNER,
)
from .forecasts import Forecast
from .tariffs import Tariff
from .utils.regionhandler import RegionHandler

RETRY_MINUTES = 5
MAX_RETRY_MINUTES = 60

CARNOT_UPDATE = datetime.timedelta(minutes=30)

EMPTY_SCHEME = vol.All(cv.make_entity_service_schema({}))

_LOGGER = getLogger(__name__)


class APIConnector:
    """An object to store Energi Data Service data."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        rand_min: int,
        rand_sec: int,
        version,
    ) -> None:
        """Initialize Energi Data Service Connector."""
        self._connectors = None
        self.forecasts = None
        self.tariffs = None
        self.hass = hass
        self._version = version
        self._last_tick = None
        self._tomorrow_valid = False
        self._entry_id = entry.entry_id
        self._config = entry

        self._rand_min: int = rand_min
        self._rand_sec: int = rand_sec

        self.master_uuid = None

        self.co2 = None
        self.co2_refresh = None
        self.has_co2 = False
        self.today = None
        self.api_today = None
        self.tomorrow = None
        self.api_tomorrow = None
        self.today_calculated = False
        self.tomorrow_calculated = False
        self.predictions = None
        self.api_predictions = None
        self.tariff_data = None
        self.tariff_connector = None
        self.predictions_calculated = False
        self.predictions_currency = None
        self.connector_currency = "EUR"
        self.forecast_currency = "EUR"
        self.listeners = []
        self.retry_unsubscribers = {}
        self.co2_update_listener = None
        self.carnot_update_listener = None
        self.is_unloading = False

        # Retry handling
        self.retry_count = {}
        self.next_retry_delay = RETRY_MINUTES

        self._client = async_get_clientsession(hass)
        self._region = RegionHandler(
            (entry.options.get(CONF_AREA) or entry.data.get(CONF_AREA)) or "FIXED"
        )
        self._tz = dt_util.get_default_time_zone()
        self._source = None
        self.forecast = entry.options.get(CONF_ENABLE_FORECAST) or False
        self.tariff = entry.options.get(CONF_ENABLE_TARIFFS) or False
        self._carnot_user = entry.options.get(CONF_EMAIL) or None
        self._carnot_apikey = entry.options.get(CONF_API_KEY) or None

    async def initialize(self) -> None:
        """Initialize the API connectors."""
        self._connectors = Connectors(hass=self.hass)
        await self._connectors.load_connectors()

        self.forecasts = Forecast(hass=self.hass)
        await self.forecasts.load_modules()

        self.tariffs = Tariff(hass=self.hass)
        await self.tariffs.load_modules()

    async def updateco2(self, dt=None, request_module=None) -> None:  # type: ignore pylint: disable=unused-argument
        """Fetch CO2 emissions from API."""
        _LOGGER.debug("Updating CO2 emissions for '%s'", self._region.region)
        connectors = self._connectors.get_connectors(self._region.region)
        _LOGGER.debug(
            "Valid connectors for '%s' is: %s", self._region.region, connectors
        )
        self.co2 = None

        try:
            for endpoint in connectors:
                module = await self.hass.async_add_executor_job(
                    import_module, endpoint.namespace, __name__.removesuffix(".api")
                )
                api = module.Connector(
                    self._region, self._client, self._tz, self._config, self._version
                )
                self.connector_currency = module.DEFAULT_CURRENCY
                # await api.async_get_spotprices()

                try:
                    await api.async_get_co2emissions()

                    if api.status != 200:
                        self.retry_update(endpoint.module + "_co2", self.updateco2)
                        continue
                    else:
                        self.clear_retry(endpoint.module + "_co2")

                    if api.co2data:
                        _LOGGER.debug(
                            "%s got CO2 values from %s (namespace='%s')",
                            self._region.region,
                            endpoint.module,
                            endpoint.namespace,
                        )
                        # _LOGGER.debug(api.co2data)
                        self.co2 = api.co2data
                except AttributeError:
                    _LOGGER.debug(
                        "CO2 values not available from %s (namespace='%s')",
                        endpoint.module,
                        endpoint.namespace,
                    )
        except:
            _LOGGER.debug("No CO2 data for this region")

    async def update(self, dt=None, request_module=None) -> None:  # type: ignore pylint: disable=unused-argument,invalid-name
        """Fetch latest prices from API."""
        _LOGGER.debug("Updating data for '%s'", self._region.region)
        connectors = self._connectors.get_connectors(self._region.region)
        _LOGGER.debug(
            "Valid connectors for '%s' is: %s", self._region.region, connectors
        )
        self.today = None
        self.tomorrow = None
        self.today_calculated = False
        self.tomorrow_calculated = False

        try:
            for endpoint in connectors:
                module = await self.hass.async_add_executor_job(
                    import_module, endpoint.namespace, __name__.removesuffix(".api")
                )
                api = module.Connector(
                    self._region, self._client, self._tz, self._config, self._version
                )
                self.connector_currency = module.DEFAULT_CURRENCY
                if (
                    isinstance(request_module, type(None))
                    or request_module == endpoint.module
                ):
                    await api.async_get_spotprices()

                    if api.status != 200:
                        self.retry_update(endpoint.module)
                        continue
                    else:
                        self.clear_retry(endpoint.module)

                    if len(api.result) == 0:
                        _LOGGER.debug("No data received from %s", endpoint.module)
                        continue

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

            if (
                isinstance(request_module, type(None))
                or request_module == endpoint.module
            ):
                if (not self.tomorrow or not self.api_tomorrow) or (
                    self.tomorrow is None or self.api_tomorrow is None
                ):
                    _LOGGER.debug("No data found for tomorrow")
                    self._tomorrow_valid = False
                    self.tomorrow = None
                    self.api_tomorrow = None

                    midnight = datetime.datetime.strptime("23:59:59", "%H:%M:%S")
                    refresh = datetime.datetime.strptime(
                        self.next_data_refresh, "%H:%M:%S"
                    )
                    now_local = dt_util.now(self._tz)

                    _LOGGER.debug(
                        "Now: %s:%s:%s (local time)",
                        f"{now_local.hour:02d}",
                        f"{now_local.minute:02d}",
                        f"{now_local.second:02d}",
                    )
                    _LOGGER.debug(
                        "Refresh: %s:%s:%s (local time)",
                        f"{refresh.hour:02d}",
                        f"{refresh.minute:02d}",
                        f"{refresh.second:02d}",
                    )
                    if (
                        f"{midnight.hour}:{midnight.minute}:{midnight.second}"
                        > f"{now_local.hour:02d}:{now_local.minute:02d}:{now_local.second:02d}"
                        and f"{refresh.hour:02d}:{refresh.minute:02d}:{refresh.second:02d}"
                        <= f"{now_local.hour:02d}:{now_local.minute:02d}:{now_local.second:02d}"
                    ):
                        self.retry_update(endpoint.module)
                    else:
                        _LOGGER.debug(
                            "Not forcing refresh, as we are past midnight and haven't reached next update time"  # pylint: disable=line-too-long
                        )
                else:
                    # _LOGGER.debug(
                    #     "Tomorrow:\n%s",
                    #     json.dumps(self.tomorrow, indent=2, default=str),
                    # )
                    self._tomorrow_valid = True

        except ServerDisconnectedError:
            _LOGGER.warning("Err.")
            self.retry_update(endpoint.module)

    async def update_carnot(self, dt=None, request_module=None) -> None:  # type: ignore pylint: disable=unused-argument,invalid-name
        """Update Carnot data if enabled."""
        if self.forecast:
            self.predictions_calculated = False
            forecast_endpoint = await self.forecasts.get_endpoint(self._region.region)
            forecast_module = await self.hass.async_add_executor_job(
                import_module,
                forecast_endpoint[0].namespace,
                __name__.removesuffix(".api"),
            )
            carnot = forecast_module.Connector(
                self._region, self._client, self._tz, self._version
            )
            self.predictions_currency = forecast_module.DEFAULT_CURRENCY
            try:
                self.predictions = await carnot.async_get_forecast(
                    self._carnot_apikey, self._carnot_user
                )
            except ClientConnectorError:
                _LOGGER.warning("Error fetching data from Carnot")

            if not isinstance(self.predictions, type(None)):
                self.predictions[:] = (
                    value
                    for value in self.predictions
                    if value.time.day
                    >= (datetime.datetime.now() + datetime.timedelta(days=1)).day
                    or value.time.month
                    > (datetime.datetime.now() + datetime.timedelta(days=1)).month
                    or value.time.year > datetime.datetime.now().year
                )

                if self._tomorrow_valid:
                    # Remove tomorrows predictions, as we have the actual values
                    self.predictions[:] = (
                        value
                        for value in self.predictions
                        if value.time.day
                        != (datetime.datetime.now() + datetime.timedelta(days=1)).day
                    )

                self.api_predictions = self.predictions

    async def async_get_tariffs(self, request_module=None) -> None:
        """Get tariff data."""

        if self.tariff:
            tariff_endpoint = await self.tariffs.get_endpoint(self._region.region)
            tariff_module = await self.hass.async_add_executor_job(
                import_module,
                tariff_endpoint[0].namespace,
                __name__.removesuffix(".api"),
            )

            tariff = tariff_module.Connector(
                self.hass,
                self._client,
                self._config.options.get(CONF_TARIFF_CHARGE_OWNER),
            )

            self.tariff_connector = tariff

            self.tariff_data = await tariff.async_get_tariffs()

            if self.tariff_data["status"] != 200:
                self.retry_update(
                    tariff_endpoint[0].module + "_tariff", self.async_get_tariffs
                )
            else:
                self.clear_retry(tariff_endpoint[0].module + "_tariff")

    @property
    def tomorrow_valid(self) -> bool:
        """Is tomorrows prices valid?."""
        return self._tomorrow_valid

    @property
    def source(self) -> str:
        """Who was the source for the data?."""
        return self._source

    @property
    def next_data_refresh(self) -> str:
        """When is next data update?."""
        return f"13:{self._rand_min:02d}:{self._rand_sec:02d}"

    @property
    def entry_id(self) -> str:
        """Return entry_id."""
        return self._entry_id

    def retry_update(self, module: str, update_function=None) -> None:
        """Retry update on error."""
        if self.is_unloading:
            return

        if module in self.retry_unsubscribers:
            self.retry_unsubscribers.pop(module)()

        retry_info = {
            module: {
                "count": (
                    self.retry_count[module]["count"] + 1
                    if module in self.retry_count
                    else 1
                ),
                "next_delay": min(
                    RETRY_MINUTES
                    * (
                        self.retry_count[module]["count"] + 1
                        if module in self.retry_count
                        else 1
                    ),
                    MAX_RETRY_MINUTES,
                ),
            }
        }
        self.retry_count.update(retry_info)
        self.next_retry_delay = self.retry_count[module]["next_delay"]
        if update_function is None:
            update_function = self.update

        _LOGGER.warning(
            "Couldn't get data from %s, retrying in %s minutes.",
            module,
            self.next_retry_delay,
        )

        now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            minutes=self.next_retry_delay
        )
        _LOGGER.debug(
            "Next retry: %s:%s:%s (UTC)",
            f"{now.hour:02d}",
            f"{now.minute:02d}",
            f"{now.second:02d}",
        )
        self.retry_unsubscribers[module] = async_call_later(
            self.hass,
            datetime.timedelta(minutes=self.next_retry_delay),
            partial(update_function, request_module=module),
        )

    def clear_retry(self, module: str) -> None:
        """Clear retry state and cancel any pending retry callback for module."""
        self.retry_count.pop(module, None)
        if module in self.retry_unsubscribers:
            self.retry_unsubscribers.pop(module)()

    def cancel_retry_updates(self) -> None:
        """Cancel all pending retry callbacks."""
        for retry_unsub in self.retry_unsubscribers.values():
            retry_unsub()
        self.retry_unsubscribers.clear()
        self.retry_count.clear()
