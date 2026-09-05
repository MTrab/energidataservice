"""Support for Energi Data Service sensor."""

from __future__ import annotations

import asyncio
import logging
from collections import namedtuple
from datetime import datetime, timedelta

import homeassistant.helpers.config_validation as cv
from homeassistant.components import sensor
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_EMAIL, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_utils
from homeassistant.util import slugify as util_slugify
from jinja2 import pass_context

from .const import (
    ATTR_ATTRIBUTION,
    ATTR_CURRENCY,
    ATTR_CURRENT_PRICE,
    ATTR_CURRENT_PRICE_BREAKDOWN,
    ATTR_FORECAST,
    ATTR_NET_OPERATOR,
    ATTR_NEXT_DATA_UPDATE,
    ATTR_RAW_TODAY,
    ATTR_RAW_TOMORROW,
    ATTR_REGION,
    ATTR_REGION_CODE,
    ATTR_TARIFFS,
    ATTR_TODAY,
    ATTR_TODAY_MAX,
    ATTR_TODAY_MEAN,
    ATTR_TODAY_MIN,
    ATTR_TODAY_REMAINING_MAX,
    ATTR_TODAY_REMAINING_MEAN,
    ATTR_TODAY_REMAINING_MIN,
    ATTR_TOMORROW,
    ATTR_TOMORROW_MAX,
    ATTR_TOMORROW_MEAN,
    ATTR_TOMORROW_MIN,
    ATTR_TOMORROW_VALID,
    ATTR_UNIT,
    ATTR_USE_CENT,
    CENT_MULTIPLIER,
    CONF_AREA,
    CONF_COUNTRY,
    CONF_CURRENCY_IN_CENT,
    CONF_DECIMALS,
    CONF_ENABLE_FORECAST,
    CONF_ENABLE_TARIFFS,
    CONF_FIXED_PRICE_VAT,
    CONF_PRICETYPE,
    CONF_RESOLUTION,
    CONF_TARIFF_CHARGE_OWNER,
    CONF_TEMPLATE,
    CONF_VAT,
    DEFAULT_TEMPLATE,
    DOMAIN,
    UNIT_TO_MULTIPLIER,
    UPDATE_EDS,
    UPDATE_EDS_5MIN,
)
from .utils.regionhandler import RegionHandler

_LOGGER = logging.getLogger(__name__)


def show_with_vat(dataset: dict, vat: float, decimals: int = 3) -> dict:
    """Add vat to the dataset."""
    _LOGGER.debug("Tariff dataset before VAT: %s", dataset)

    out_set = {"additional_tariffs": {}, "tariffs": {}}
    for key, _ in dataset.items():
        if key == "additional_tariffs":
            out_set.update({"additional_tariffs": {}})
            for add_key, add_value in dataset[key].items():
                out_set["additional_tariffs"].update(
                    {add_key: round(add_value * float(1 + vat), decimals)}
                )
        elif key == "tariffs":
            for t_key, t_value in dataset[key].items():
                out_set["tariffs"].update(
                    {t_key: round(t_value * float(1 + vat), decimals)}
                )

    _LOGGER.debug("Tariff dataset after VAT: %s", out_set)
    return out_set


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_devices):
    """Do the sensor platform setup from a config entry."""
    config = config_entry
    _setup(hass, config, async_add_devices)
    return True


def mean(data: list) -> float:
    """Calculate mean value of list."""
    val = 0
    num = 0

    for i in data:
        val += i.price
        num += 1

    return val / num


def _setup(hass, config: ConfigEntry, add_devices):
    """Do the platform setup."""
    area = config.options.get(CONF_AREA) or config.data.get(CONF_AREA)
    if area is None:
        area = "FIXED"
    region = RegionHandler(area)
    _LOGGER.debug("Timezone set in ha %s", hass.config.time_zone)
    _LOGGER.debug("Currency set in ha %s", hass.config.currency)
    _LOGGER.debug("Country: %s", region.country)
    _LOGGER.debug("Region: %s", region.name)
    _LOGGER.debug("Region description: %s", region.description)
    _LOGGER.debug("Region currency %s", region.currency.name)
    _LOGGER.debug(
        "Show in cent: %s", config.options.get(CONF_CURRENCY_IN_CENT) or False
    )
    _LOGGER.debug(
        "Get AI predictions? %s", config.options.get(CONF_ENABLE_FORECAST) or False
    )
    _LOGGER.debug(
        "Automatically try fetching tariffs? %s",
        config.options.get(CONF_ENABLE_TARIFFS) or False,
    )
    _LOGGER.debug("Domain %s", DOMAIN)

    if region.currency.name != hass.config.currency:
        if area != "FIXED":
            _LOGGER.warning(
                "Official currency for %s is %s but Home Assistant reports %s from config and will show prices in %s",  # pylint: disable=line-too-long
                region.country,
                region.currency.name,
                hass.config.currency,
                hass.config.currency,
            )
        region.set_region(area, hass.config.currency)

    this_sensor = SensorEntityDescription(
        key="EnergiDataService_{}_{}_{}_{}_{}_{}_{}".format(  # pylint: disable=consider-using-f-string
            config.options.get(CONF_AREA) or config.data.get(CONF_AREA),
            config.options.get(CONF_VAT) or config.data.get(CONF_VAT),
            config.options.get(CONF_CURRENCY_IN_CENT)
            or config.data.get(CONF_CURRENCY_IN_CENT),
            config.options.get(CONF_DECIMALS) or config.data.get(CONF_DECIMALS),
            config.options.get(CONF_PRICETYPE) or config.data.get(CONF_PRICETYPE),
            config.options.get(CONF_NAME) or config.data.get(CONF_NAME),
            config.options.get(CONF_COUNTRY) or config.data.get(CONF_COUNTRY),
        ),
        device_class=SensorDeviceClass.MONETARY,
        icon="mdi:flash",
        name=config.data.get(CONF_NAME),
        state_class=SensorStateClass.TOTAL,
        last_reset=None,
    )
    sens = EnergidataserviceSensor(config, hass, region, this_sensor)
    add_devices([sens])

    api = hass.data[DOMAIN][config.entry_id]

    if api.has_co2:
        co2_sensor = SensorEntityDescription(
            key="EnergiDataService_co2",
            device_class=None,
            icon="mdi:molecule-co2",
            name=config.data.get(CONF_NAME) + " CO2",
            state_class=SensorStateClass.MEASUREMENT,
            last_reset=None,
        )
        sens = EnergidataserviceCO2Sensor(config, hass, region, co2_sensor)
        add_devices([sens])


@callback
def _async_migrate_unique_id(hass: HomeAssistant, entity: str, new_id: str) -> None:
    """Change unique_ids to allow multiple instances."""
    _LOGGER.debug("Testing for unique_id")
    entity_registry = er.async_get(hass)
    curentity = entity_registry.async_get(entity)
    if curentity is not None:
        _LOGGER.debug("- Device_id: %s", curentity.device_id)
        if new_id is not None:
            device_registry = dr.async_get(hass)
            curdevice = device_registry.async_get(curentity.device_id)
            identifiers = curdevice.identifiers
            for identifier in identifiers:
                _LOGGER.debug(" - Identifier found: %s", identifier)
            _LOGGER.debug(" - Adding new device identifier")
            device_registry = dr.async_get(hass)
            curdevice = device_registry.async_get(curentity.device_id)
            identifiers = curdevice.identifiers
            tup_dict = dict(identifiers)  # {'hi': 'bye', 'one': 'two'}
            tup_dict[DOMAIN] = new_id
            identifiers = tuple(tup_dict.items())  # (('one', 'two'),)
            for identifier in identifiers:
                _LOGGER.debug(" - Identifier after edit: %s", identifier)
            device_registry.async_update_device(
                curentity.device_id, new_identifiers=identifiers
            )
            if curentity.unique_id in [
                "energidataservice_West of the great belt",
                "energidataservice_East of the great belt",
            ]:
                _LOGGER.debug(" - Adding extra entity identifier")
                entity_registry.async_update_entity(entity, new_unique_id=new_id)
        else:
            _LOGGER.debug(" - New id not set, skipping")
    else:
        _LOGGER.debug("- Check didn't find anything")


class EnergidataserviceCO2Sensor(SensorEntity):
    """Representation of Energi Data Service CO2 data."""

    def __init__(
        self,
        config: ConfigEntry,
        hass: HomeAssistant,
        region: RegionHandler,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize Energidataservice CO2 sensor."""
        self.entity_description = description
        self.entity_description = description
        self.region = region

        self._area = region.description
        self._attr_name = self.entity_description.name
        self._config = config
        self._entry_id = config.entry_id
        self._api = hass.data[DOMAIN][config.entry_id]
        self._hass = hass

        self._entity_id = sensor.ENTITY_ID_FORMAT.format(
            util_slugify(f"{self._attr_name} {self._area}")
        )
        self._unique_id = util_slugify(f"{self._attr_name}_co2_{self._entry_id}")
        _async_migrate_unique_id(hass, self._entity_id, self._unique_id)

        self._friendly_name = (
            config.options.get(CONF_NAME) + " CO2"
            or config.data.get(CONF_NAME) + " CO2"
        )

        self._attr_native_value = None
        self._attr_native_unit_of_measurement = "g/kWh"

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._friendly_name

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def unit(self) -> str:
        """Return currency unit."""
        return self._attr_native_unit_of_measurement

    @property
    def device_info(self):
        """Return the device info."""
        _LOGGER.debug("Master UUID: %s", self._api.master_uuid)
        return {
            "identifiers": {(DOMAIN, self._api.master_uuid)},
            "model": f"Region code: {self.region.region}",
            "manufacturer": "Energi Data Service",
        }

    async def update_data(self) -> None:
        """Update data for the sensor."""
        current_state_time = datetime.fromisoformat(
            dt_utils.now().replace(microsecond=0).replace(second=0).isoformat()
        )
        if self._api.co2:
            possible_dataset = []
            for dataset in self._api.co2:
                if dataset.time <= current_state_time:
                    possible_dataset = dataset
                else:
                    self._attr_native_value = possible_dataset.value
                    _LOGGER.debug(
                        "Current CO2 value updated to %f for %s using dataset time %s",
                        self._attr_native_value,
                        self.region.region,
                        possible_dataset.time,
                    )
                    break

            self._attr_extra_state_attributes = {"next_refresh": self._api.co2_refresh}

            value_dict = {}
            for i in self._api.co2:
                value_dict.update({i.time.strftime("%H:%M"): i.value})

            self._attr_extra_state_attributes.update({"emissions": value_dict})

        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        await super().async_added_to_hass()
        _LOGGER.debug("Added sensor '%s' CO2", self._entity_id)
        await self.update_data()
        self.async_on_remove(
            async_dispatcher_connect(
                self._hass, UPDATE_EDS_5MIN.format(self._entry_id), self.update_data
            )
        )


class EnergidataserviceSensor(SensorEntity):
    """Representation of Energi Data Service data."""

    _unrecorded_attributes = frozenset(
        {
            ATTR_TODAY,
            ATTR_TOMORROW,
            ATTR_RAW_TODAY,
            ATTR_RAW_TOMORROW,
            ATTR_FORECAST,
            ATTR_TARIFFS,
        }
    )

    def __init__(
        self,
        config: ConfigEntry,
        hass: HomeAssistant,
        region: RegionHandler,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize Energidataservice sensor."""
        self.entity_description = description
        self._attr_name = self.entity_description.name
        self._config = config
        self.region = region
        self._entry_id = config.entry_id
        self._cent = config.options.get(CONF_CURRENCY_IN_CENT) or False
        self._forecast = config.options.get(CONF_ENABLE_FORECAST) or False
        self._tariff = config.options.get(CONF_ENABLE_TARIFFS) or False
        self._carnot_user = config.options.get(CONF_EMAIL) or None
        self._carnot_apikey = config.options.get(CONF_API_KEY) or None
        self._area = region.description
        self._currency = hass.config.currency
        self._price_type = config.options.get(CONF_PRICETYPE) or config.data.get(
            CONF_PRICETYPE
        )

        self._attr_suggested_display_precision = config.options.get(
            CONF_DECIMALS
        ) or config.data.get(CONF_DECIMALS)

        self._api = hass.data[DOMAIN][config.entry_id]
        self._cost_template = config.options.get(CONF_TEMPLATE) or config.data.get(
            CONF_TEMPLATE
        )
        self._hass = hass
        self._friendly_name = config.options.get(CONF_NAME) or config.data.get(
            CONF_NAME
        )
        self._validation_lock = asyncio.Lock()
        self._today_source = None
        self._tomorrow_source = None
        self._predictions_source = None
        self._tariff_data_source = None
        self._tariff_connector_source = None
        self._connector_currency_source = None
        self._predictions_currency_source = None
        self._price_breakdown_today = None
        self._price_breakdown_tomorrow = None
        self._current_price_breakdown = None

        if config.options.get(CONF_VAT) is True:
            self._vat = region.vat
        else:
            self._vat = 0

        if config.options.get(CONF_COUNTRY) == "Fixed Price":
            self._vat = (config.options.get(CONF_FIXED_PRICE_VAT) / 100) or 0

        self._entity_id = sensor.ENTITY_ID_FORMAT.format(
            util_slugify(f"{self._attr_name} {self._area}")
        )
        self._unique_id = util_slugify(f"{self._attr_name}_{self._entry_id}")
        _async_migrate_unique_id(hass, self._entity_id, self._unique_id)

        self._api.master_uuid = self._unique_id

        # Holds current price
        self._attr_native_value = None
        if CONF_CURRENCY_IN_CENT in config.options:
            self._attr_native_unit_of_measurement = (
                f"{region.currency.cent}/{config.options[CONF_PRICETYPE]}"
                if config.options[CONF_CURRENCY_IN_CENT]
                else f"{region.currency.name}/{config.options[CONF_PRICETYPE]}"
            )
        else:
            self._attr_native_unit_of_measurement = (
                f"{region.currency.name}/{config.options[CONF_PRICETYPE]}"
            )
        # Holds the raw data
        self._today_raw = None
        self._tomorrow_raw = None

        # Holds statistical prices for today
        self._today_min = None
        self._today_max = None
        self._today_remaining_min = None
        self._today_remaining_max = None

        # Holds statistical prices for tomorrow
        self._tomorrow_min = None
        self._tomorrow_max = None

        # Holds mean values for today and tomorrow
        self._today_mean = None
        self._today_remaining_mean = None
        self._tomorrow_mean = None

        # Check incase the sensor was setup using config flow.
        # This blow up if the template isnt valid.
        if not isinstance(self._cost_template, Template):
            if self._cost_template in (None, ""):
                self._cost_template = DEFAULT_TEMPLATE
            self._cost_template = cv.template(self._cost_template)
        # check for yaml setup.
        else:
            if self._cost_template.template in ("", None):
                self._cost_template = cv.template(DEFAULT_TEMPLATE)

    async def validate_data(self) -> None:
        """Validate sensor data."""
        async with self._validation_lock:
            await self._validate_data()

    async def _validate_data(self) -> None:
        """Validate and publish a consistent sensor data snapshot."""
        _LOGGER.debug("Validating sensor %s", self.name)

        # Do we have valid data for today? If not, try fetching new dataset
        if not self._api.api_today:
            _LOGGER.debug("No sensor data found - calling update")
            await self._api.update()

        # If predictions is enabled but no data exists, fetch dataset
        if self._api.forecast and self._api.api_predictions is None:
            await self._api.update_carnot()

        # Build calculated lists from one consistent set of raw API data. If an API
        # refresh replaces a source while calculation runs in the executor, retry
        # once and otherwise retain the previously published state.
        for attempt in range(2):
            today_source = self._api.api_today
            tomorrow_source = self._api.api_tomorrow if self.tomorrow_valid else None
            predictions_source = (
                self._api.api_predictions if self._api.forecast else None
            )
            tariff_data_source = self._api.tariff_data
            tariff_connector_source = self._api.tariff_connector
            connector_currency = self._api.connector_currency or self._currency
            predictions_currency = self._api.predictions_currency or self._currency

            today = self._api.today
            if today_source is not None and (
                not self._api.today_calculated
                or self._price_breakdown_today is None
                or self._today_source is not today_source
                or self._tariff_data_source is not tariff_data_source
                or self._tariff_connector_source is not tariff_connector_source
                or self._connector_currency_source != connector_currency
            ):
                today, price_breakdown_today = await self._hass.async_add_executor_job(
                    self._format_list_with_breakdown,
                    today_source,
                    False,
                    False,
                    connector_currency,
                )
            else:
                price_breakdown_today = self._price_breakdown_today

            tomorrow = self._api.tomorrow
            if tomorrow_source is not None and (
                not self._api.tomorrow_calculated
                or self._price_breakdown_tomorrow is None
                or self._tomorrow_source is not tomorrow_source
                or self._tariff_data_source is not tariff_data_source
                or self._tariff_connector_source is not tariff_connector_source
                or self._connector_currency_source != connector_currency
            ):
                (
                    tomorrow,
                    price_breakdown_tomorrow,
                ) = await self._hass.async_add_executor_job(
                    self._format_list_with_breakdown,
                    tomorrow_source,
                    True,
                    False,
                    connector_currency,
                )
            else:
                price_breakdown_tomorrow = self._price_breakdown_tomorrow

            predictions = self._api.predictions
            if predictions_source is not None and (
                not self._api.predictions_calculated
                or self._predictions_source is not predictions_source
                or self._tariff_data_source is not tariff_data_source
                or self._tariff_connector_source is not tariff_connector_source
                or self._predictions_currency_source != predictions_currency
            ):
                predictions = await self._hass.async_add_executor_job(
                    self._format_list,
                    predictions_source,
                    False,
                    True,
                    predictions_currency,
                )

            sources_unchanged = (
                today_source is self._api.api_today
                and tomorrow_source
                is (self._api.api_tomorrow if self.tomorrow_valid else None)
                and predictions_source
                is (self._api.api_predictions if self._api.forecast else None)
                and tariff_data_source is self._api.tariff_data
                and tariff_connector_source is self._api.tariff_connector
                and connector_currency
                == (self._api.connector_currency or self._currency)
                and predictions_currency
                == (self._api.predictions_currency or self._currency)
            )
            if not sources_unchanged:
                _LOGGER.debug("Price data changed during calculation, retrying")
                if attempt == 0:
                    continue
                _LOGGER.warning(
                    "Price data kept changing during calculation; retaining the "
                    "previous sensor state"
                )
                return

            # Commit calculated data only after every source has been verified. No
            # await is allowed between this point and writing the Home Assistant
            # state, so raw and calculated data cannot be interleaved.
            self._api.today = today if today_source is not None else None
            self._api.today_calculated = today_source is not None
            self._api.tomorrow = tomorrow if tomorrow_source is not None else None
            self._api.tomorrow_calculated = tomorrow_source is not None
            self._api.predictions = (
                predictions if predictions_source is not None else None
            )
            self._api.predictions_calculated = predictions_source is not None
            self._price_breakdown_today = (
                price_breakdown_today if today_source is not None else None
            )
            self._price_breakdown_tomorrow = (
                price_breakdown_tomorrow if tomorrow_source is not None else None
            )

            self._today_source = today_source
            self._tomorrow_source = tomorrow_source
            self._predictions_source = predictions_source
            self._tariff_data_source = tariff_data_source
            self._tariff_connector_source = tariff_connector_source
            self._connector_currency_source = connector_currency
            self._predictions_currency_source = predictions_currency
            break

        # Update attributes
        if self._api.today:
            self._today_raw = self._price_breakdown_today
            self._tomorrow_raw = self._price_breakdown_tomorrow

            self._today_min = self._get_specific(
                "min", self._api.today, self._attr_suggested_display_precision
            )
            self._today_max = self._get_specific(
                "max",
                self._api.today,
                self._attr_suggested_display_precision,
            )
            self._today_mean = self._get_specific(
                "mean",
                self._api.today,
                self._attr_suggested_display_precision,
            )

            remaining_today = self._filter_remaining_today(self._api.today)

            self._today_remaining_min = self._get_specific(
                "min",
                remaining_today,
                self._attr_suggested_display_precision,
            )
            self._today_remaining_max = self._get_specific(
                "max",
                remaining_today,
                self._attr_suggested_display_precision,
            )
            self._today_remaining_mean = self._get_specific(
                "mean",
                remaining_today,
                self._attr_suggested_display_precision,
            )

            self._tomorrow_min = self._get_specific(
                "min",
                self._api.tomorrow,
                self._attr_suggested_display_precision,
            )
            self._tomorrow_max = self._get_specific(
                "max",
                self._api.tomorrow,
                self._attr_suggested_display_precision,
            )
        else:
            self._today_min = None
            self._today_max = None
            self._today_mean = None
            self._today_remaining_min = None
            self._today_remaining_max = None
            self._today_remaining_mean = None
            self._tomorrow_min = None
            self._tomorrow_max = None

        # If we have valid data for tomorrow, then find the mean value
        if self.tomorrow_valid:
            self._tomorrow_mean = self._get_specific(
                "mean",
                self._api.tomorrow,
                self._attr_suggested_display_precision,
            )
        else:
            self._tomorrow_mean = None

        # Updates price for this hour.
        self._get_current_price()

        self.async_write_ha_state()

    def _get_current_price(self) -> None:
        """Get price for current hour."""
        if self._api.today:
            self._current_price_breakdown = None
            for index, dataset in enumerate(self._api.today):
                if dataset.time.hour != dt_utils.now().hour:
                    continue

                if (
                    dataset.time.hour == dt_utils.now().hour
                    and len(self._api.today) == 24
                ) or (
                    dataset.time.minute <= dt_utils.now().minute
                    and (
                        (dataset.time + timedelta(minutes=15)).minute
                        > dt_utils.now().minute
                        or (dataset.time + timedelta(minutes=15)).minute == 0
                    )
                ):
                    self._attr_native_value = dataset.price
                    self._current_price_breakdown = self._price_breakdown_today[index]
                    _LOGGER.debug(
                        "Current price updated to %f for %s",
                        self._attr_native_value,
                        self.region.region,
                    )
                    break

            self._attr_extra_state_attributes = {
                ATTR_CURRENT_PRICE: self.state,
                ATTR_CURRENT_PRICE_BREAKDOWN: self._current_price_breakdown,
                ATTR_UNIT: self.unit,
                ATTR_CURRENCY: self._currency,
                ATTR_REGION: self._area,
                ATTR_REGION_CODE: self.region.region,
                ATTR_TOMORROW_VALID: self.tomorrow_valid,
                ATTR_NEXT_DATA_UPDATE: self._api.next_data_refresh,
                ATTR_TODAY: self.today,
                ATTR_TOMORROW: self.tomorrow or None,
                ATTR_RAW_TODAY: self._today_raw or None,
                ATTR_RAW_TOMORROW: self._tomorrow_raw or None,
                ATTR_TODAY_MIN: self._today_min,
                ATTR_TODAY_MAX: self._today_max,
                ATTR_TODAY_MEAN: self._today_mean,
                ATTR_TODAY_REMAINING_MIN: self._today_remaining_min,
                ATTR_TODAY_REMAINING_MAX: self._today_remaining_max,
                ATTR_TODAY_REMAINING_MEAN: self._today_remaining_mean,
                ATTR_TOMORROW_MIN: self._tomorrow_min or None,
                ATTR_TOMORROW_MAX: self._tomorrow_max or None,
                ATTR_TOMORROW_MEAN: self._tomorrow_mean or None,
                ATTR_USE_CENT: self._cent,
                ATTR_ATTRIBUTION: f"Data sourced from {self._api.source}",
            }

            if not isinstance(self.predictions, type(None)):
                self._attr_extra_state_attributes.update(
                    {
                        ATTR_FORECAST: self._add_raw(
                            self.predictions, self._attr_suggested_display_precision
                        ),
                        ATTR_ATTRIBUTION: f"Data sourced from {self._api.source} "
                        "and forecast from Carnot",
                    }
                )

            if not isinstance(self._api.tariff_data, type(None)):
                self._attr_extra_state_attributes.update(
                    {
                        ATTR_NET_OPERATOR: self._config.options.get(
                            CONF_TARIFF_CHARGE_OWNER
                        ),
                        ATTR_TARIFFS: show_with_vat(
                            self._api.tariff_data,
                            self._vat,
                            self._attr_suggested_display_precision,
                        ),
                    }
                )
        else:
            self._attr_native_value = None
            _LOGGER.debug("No data found for %s", self.region.region)

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        await super().async_added_to_hass()
        _LOGGER.debug("Added sensor '%s'", self._entity_id)
        await self.validate_data()
        self.async_on_remove(
            async_dispatcher_connect(
                self._hass, UPDATE_EDS.format(self._entry_id), self.validate_data
            )
        )

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._friendly_name

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def unit(self) -> str:
        """Return currency unit."""
        return self._price_type

    @property
    def device_info(self):
        """Return the device info."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "model": f"Region code: {self.region.region}",
            "manufacturer": "Energi Data Service",
        }

    @property
    def today(self) -> list:
        """Get todays prices.

        Returns:
            list: sorted list where today[0] is the price of hour 00.00 - 01.00.

        """
        return (
            [
                round(i.price, self._attr_suggested_display_precision)
                for i in self._api.today
                if i
            ]
            if not isinstance(self._api.today, type(None))
            else None
        )

    @property
    def tomorrow(self) -> list:
        """Get tomorrows prices.

        Returns:
            list: sorted where tomorrow[0] is the price of hour 00.00 - 01.00 etc.

        """
        if self._api.tomorrow_valid:
            return [
                round(i.price, self._attr_suggested_display_precision)
                for i in self._api.tomorrow
                if i
            ]
        else:
            return None

    @property
    def predictions(self) -> list | None:
        """Return predictions (forecasts) if enabled, else None."""
        if self._forecast:
            return self._api.predictions

    def _filter_remaining_today(self, data) -> list:
        """Return only current and upcoming entries for today."""
        if not data:
            return []

        now = dt_utils.now()
        is_hourly = self._config.options.get(
            CONF_RESOLUTION,
            self._config.data.get(CONF_RESOLUTION, True),
        )
        interval_length = timedelta(hours=1) if is_hourly else timedelta(minutes=15)

        return [
            entry
            for entry in data
            if (dt_utils.as_local(entry.time) + interval_length) > now
        ]

    @staticmethod
    def _add_raw(data, decimals: int) -> list:
        lst = []
        for i in data:
            ret = {
                "hour": i.time,
                "price": round(i.price, decimals),
            }
            lst.append(ret)

        return lst

    @property
    def raw_today(self):
        """Return the raw array with todays prices."""
        return self._today_raw

    @property
    def raw_tomorrow(self):
        """Return the raw array with tomorrows prices."""
        return self._tomorrow_raw

    @property
    def tomorrow_valid(self):
        """Return state of tomorrow_valid."""
        return self._api.tomorrow_valid

    @property
    def today_min(self):
        """Return lowpoint for today."""
        return self._today_min

    @property
    def today_max(self):
        """Return highpoint for today."""
        return self._today_max

    @property
    def tomorrow_min(self):
        """Return lowpoint for tomorrow."""
        return self._tomorrow_min

    @property
    def tomorrow_max(self):
        """Return highpoint for tomorrow."""
        return self._tomorrow_max

    @property
    def today_mean(self):
        """Return mean value for today."""
        return self._today_mean

    @property
    def tomorrow_mean(self):
        """Return mean value for tomorrow."""
        return self._tomorrow_mean

    def _calculate(
        self,
        value=None,
        fake_dt=datetime,
        default_currency: str = "EUR",
    ) -> float:
        """Do price calculations."""
        return self._calculate_breakdown(value, fake_dt, default_currency)["total"]

    def _calculate_breakdown(
        self,
        value=None,
        fake_dt=datetime,
        default_currency: str = "EUR",
    ) -> dict:
        """Calculate a price and retain every component used in its total."""
        if value is None:
            value = self._attr_native_value

        def faker():
            def inner(*_, **__):
                return fake_dt or dt_utils.now()

            return pass_context(inner)

        # Convert currency from EUR
        if self._currency != default_currency:
            value = self.region.currency.convert(
                value, to_currency=self._currency, from_currency=default_currency
            )

        tariff_value = 0
        owner_tariff = 0
        elafgift = 0
        system_tariffs = {}
        if (
            self._api.tariff_data is not None
            and fake_dt is not None
            and len(self._api.tariff_data["tariffs"]) > 0
        ):
            try:
                system_tariff: dict = (
                    self._api.tariff_connector.get_dated_system_tariff(fake_dt)
                )
                chargeowner_tariff: dict = self._api.tariff_connector.get_dated_tariff(
                    fake_dt
                )

                if system_tariff:
                    for tariff, additional_tariff in system_tariff.items():
                        component_value = float(additional_tariff)
                        system_tariffs[tariff] = component_value
                        tariff_value += component_value
                        if tariff == "elafgift":
                            elafgift = component_value

                owner_tariff = float(
                    chargeowner_tariff[str(fake_dt.hour)] if chargeowner_tariff else 0
                )
                tariff_value += owner_tariff
            except KeyError:
                _LOGGER.warning(
                    "Error adding tariffs for %s, no valid tariffs was found!", fake_dt
                )
                raise
        elif (
            self._api.tariff_data is not None
            and fake_dt is not None
            and len(self._api.tariff_data["tariffs"]) == 0
        ):
            _LOGGER.warning(
                "Error adding tariffs for %s, empty tariff dataset was found!", fake_dt
            )

        spot_price = value / UNIT_TO_MULTIPLIER[self._price_type]

        template_value = self._cost_template.async_render(
            now=faker(),
            current_tariff=tariff_value,
            current_price=spot_price,
            el_afgift=elafgift,
            chargeowner_tariff=owner_tariff,
        )

        if not isinstance(template_value, int | float | type(None)):
            try:
                template_value = float(template_value)
            except (TypeError, ValueError):
                _LOGGER.exception(
                    "Failed to convert %s %s to float",
                    template_value,
                    type(template_value),
                )
                raise

        if isinstance(template_value, type(None)):
            template_value = 0

        try:
            subtotal = spot_price + template_value + tariff_value
        except Exception:
            _LOGGER.debug(
                "Price %s template value %s type %s dt %s tariff_value %s ",
                spot_price,
                template_value,
                type(template_value),
                fake_dt,
                tariff_value,
            )
            raise

        vat = subtotal * self._vat
        total = subtotal + vat

        if self._cent:
            spot_price *= CENT_MULTIPLIER
            owner_tariff *= CENT_MULTIPLIER
            template_value *= CENT_MULTIPLIER
            vat *= CENT_MULTIPLIER
            total *= CENT_MULTIPLIER
            system_tariffs = {
                name: price * CENT_MULTIPLIER for name, price in system_tariffs.items()
            }

        return {
            "spot_price": spot_price,
            "chargeowner_tariff": owner_tariff,
            "system_tariffs": system_tariffs,
            "additional_cost": template_value,
            "vat": vat,
            "total": total,
        }

    def _format_list_with_breakdown(
        self, data, tomorrow=False, predictions=False, default_currency: str = "EUR"
    ) -> tuple[list, list]:
        """Format prices and their components from the same calculations."""
        formatted_pricelist = []
        breakdown = []
        interval = namedtuple("Interval", "price time")
        decimals = self._attr_suggested_display_precision

        for item in data:
            components = self._calculate_breakdown(
                item.price,
                fake_dt=dt_utils.as_local(item.time),
                default_currency=default_currency,
            )
            formatted_pricelist.append(interval(components["total"], item.time))
            breakdown.append(
                {
                    "hour": item.time,
                    "price": round(components["total"], decimals),
                    "spot_price": round(components["spot_price"], decimals),
                    "chargeowner_tariff": round(
                        components["chargeowner_tariff"], decimals
                    ),
                    **{
                        name: round(price, decimals)
                        for name, price in components["system_tariffs"].items()
                    },
                    "additional_cost": round(components["additional_cost"], decimals),
                    "vat": round(components["vat"], decimals),
                }
            )

        return formatted_pricelist, breakdown

    def _format_list(
        self, data, tomorrow=False, predictions=False, default_currency: str = "EUR"
    ) -> list:
        """Format data as list with prices localized."""
        formatted_pricelist = []

        if tomorrow:
            pass

        if predictions:
            pass

        _start = datetime.now().timestamp()
        Interval = namedtuple("Interval", "price time")
        for i in data:
            price = self._calculate(
                i.price,
                fake_dt=dt_utils.as_local(i.time),
                default_currency=default_currency,
            )
            formatted_pricelist.append(Interval(price, i.time))

        _stop = datetime.now().timestamp()
        _ttf = round(_stop - _start, 2)

        if tomorrow:
            _calc_for = "TOMORROW"
        elif predictions:
            _calc_for = "PREDICTIONS"
        else:
            _calc_for = "TODAY"

        _LOGGER.debug(
            "Calculation for %s in %s took %s seconds",
            _calc_for,
            self.region.region,
            _ttf,
        )
        return formatted_pricelist

    @staticmethod
    def _get_specific(datatype: str, data: list, decimals: int):
        """Get specific values - ie. min, max, mean values."""

        if datatype in ["MIN", "Min", "min"]:
            if data:
                res = min(data, key=lambda k: k.price)
                ret = {
                    "hour": res.time,
                    "price": round(res.price, decimals),
                }

                return ret
            else:
                return None
        elif datatype in ["MAX", "Max", "max"]:
            if data:
                res = max(data, key=lambda k: k.price)
                ret = {"hour": res.time, "price": round(res.price, decimals)}

                return ret
            else:
                return None
        elif datatype in ["MEAN", "Mean", "mean"]:
            if data:
                return round(mean(data), decimals)
            else:
                return None
        else:
            return None
