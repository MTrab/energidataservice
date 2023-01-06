"""Support for Energi Data Service sensor."""
from __future__ import annotations

from collections import namedtuple
from datetime import datetime
import json
import logging

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
from homeassistant.helpers import device_registry as dr, entity_registry as er
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.template import Template, attach
from homeassistant.util import dt as dt_utils, slugify as util_slugify
from jinja2 import pass_context

from .const import (
    CENT_MULTIPLIER,
    CONF_AREA,
    CONF_COUNTRY,
    CONF_CURRENCY_IN_CENT,
    CONF_DECIMALS,
    CONF_ENABLE_FORECAST,
    CONF_ENABLE_TARIFFS,
    CONF_PRICETYPE,
    CONF_TEMPLATE,
    CONF_VAT,
    DEFAULT_TEMPLATE,
    DOMAIN,
    UNIT_TO_MULTIPLIER,
    UPDATE_EDS,
)
from .utils.regionhandler import RegionHandler

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_devices):
    """Setup sensor platform from a config entry."""
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
    """Setup the platform."""
    area = config.options.get(CONF_AREA) or config.data.get(CONF_AREA)
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
        state_class=SensorStateClass.MEASUREMENT,
    )
    sens = EnergidataserviceSensor(config, hass, region, this_sensor)

    add_devices([sens])


@callback
def _async_migrate_unique_id(hass: HomeAssistant, entity: str, new_id: str) -> None:
    """Change unique_ids to allow multiple instances."""
    _LOGGER.debug("Testing for unique_id")
    entity_registry = er.async_get(hass)
    curentity = entity_registry.async_get(entity)
    if not curentity is None:
        _LOGGER.debug("- Device_id: %s", curentity.device_id)
        if not new_id is None:
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


class EnergidataserviceSensor(SensorEntity):
    """Representation of Energi Data Service data."""

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
        self._decimals = config.options.get(CONF_DECIMALS) or config.data.get(
            CONF_DECIMALS
        )
        self._api = hass.data[DOMAIN][config.entry_id]
        self._cost_template = config.options.get(CONF_TEMPLATE) or config.data.get(
            CONF_TEMPLATE
        )
        self._hass = hass
        self._friendly_name = config.options.get(CONF_NAME) or config.data.get(
            CONF_NAME
        )

        if config.options.get(CONF_VAT) is True:
            self._vat = 0.25
        else:
            self._vat = 0

        self._entity_id = sensor.ENTITY_ID_FORMAT.format(
            util_slugify(f"{self._attr_name} {self._area}")
        )
        self._unique_id = util_slugify(f"{self._attr_name}_{self._entry_id}")
        _async_migrate_unique_id(hass, self._entity_id, self._unique_id)

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

        # Holds statistical prices for tomorrow
        self._tomorrow_min = None
        self._tomorrow_max = None

        # Holds mean values for today and tomorrow
        self._today_mean = None
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

        attach(self._hass, self._cost_template)

    async def validate_data(self) -> None:
        """Validate sensor data."""
        _LOGGER.debug("Validating sensor %s", self.name)

        # Do we have valid data for today? If not, try fetching new dataset
        if not self._api.today:
            _LOGGER.debug("No sensor data found - calling update")
            await self._api.update()
            if not self._api.today is None and not self._api.today_calculated:
                await self._hass.async_add_executor_job(
                    self._format_list,
                    self._api.today,
                    False,
                    False,
                    self._api.connector_currency,
                )

        # Do we have valid data for tomorrow? If we do, calculate prices in local currency
        # If not, set attributes to None
        if self.tomorrow_valid:
            if not self._api.tomorrow_calculated:
                await self._hass.async_add_executor_job(
                    self._format_list,
                    self._api.tomorrow,
                    True,
                    False,
                    self._api.connector_currency,
                )
            self._tomorrow_raw = self._add_raw(self._api.tomorrow)
        else:
            self._api.tomorrow = None
            self._tomorrow_raw = None
            self._api.tomorrow_calculated = False

        # Check if the data have been reset to API values rather than the calculated values
        if self._api.today == self._api.api_today and not isinstance(
            self._api.today, type(None)
        ):
            self._api.today_calculated = False
        if self._api.tomorrow == self._api.api_tomorrow and not isinstance(
            self._api.tomorrow, type(None)
        ):
            self._api.tomorrow_calculated = False
        if self._api.predictions == self._api.api_predictions and not isinstance(
            self._api.predictions, type(None)
        ):
            self._api.predictions_calculated = False

        # If we haven't already calculated todays prices in local currency, do so now
        if not self._api.today_calculated and not isinstance(
            self._api.today, type(None)
        ):
            await self._hass.async_add_executor_job(self._format_list, self._api.today)

        # If predictions is enabled but no data exists, fetch dataset
        if self._api.forecast and isinstance(self._api.predictions, type(None)):
            await self._api.update_carnot()

        # If predictions is enabled but not calculated, do so now
        if not self._api.predictions_calculated and not isinstance(
            self._api.predictions, type(None)
        ):
            await self._hass.async_add_executor_job(
                self._format_list,
                self._api.predictions,
                False,
                True,
                self._api.predictions_currency,
            )
        else:
            _LOGGER.debug(
                "Predictions: %s (%s)",
                self._api.predictions,
                type(self._api.predictions),
            )

        # Update attributes
        if self._api.today:
            self._today_raw = self._add_raw(self._api.today)

            self._today_min = self._get_specific("min", self._api.today)
            self._today_max = self._get_specific("max", self._api.today)
            self._today_mean = round(
                self._get_specific("mean", self._api.today), self._decimals
            )
            self._tomorrow_min = self._get_specific("min", self._api.tomorrow)
            self._tomorrow_max = self._get_specific("max", self._api.tomorrow)

        # If we have valid data for tomorrow, then find the mean value
        if self.tomorrow_valid:
            self._tomorrow_mean = round(
                self._get_specific("mean", self._api.tomorrow), self._decimals
            )
        else:
            self._tomorrow_mean = None

        # Updates price for this hour.
        self._get_current_price()

        self.async_write_ha_state()

    def _get_current_price(self) -> None:
        """Get price for current hour"""
        current_state_time = datetime.fromisoformat(
            dt_utils.now()
            .replace(microsecond=0)
            .replace(second=0)
            .replace(minute=0)
            .isoformat()
        )
        if self._api.today:
            for dataset in self._api.today:
                if dataset.hour == current_state_time:
                    self._attr_native_value = dataset.price
                    _LOGGER.debug(
                        "Current price updated to %f for %s",
                        self._attr_native_value,
                        self.region.region,
                    )
                    break

            self._attr_extra_state_attributes = {
                "current_price": self.state,
                "unit": self.unit,
                "currency": self._currency,
                "region": self._area,
                "region_code": self.region.region,
                "tomorrow_valid": self.tomorrow_valid,
                "next_data_update": self._api.next_data_refresh,
                "today": self.today,
                "tomorrow": self.tomorrow or None,
                "raw_today": self._today_raw or None,
                "raw_tomorrow": self._tomorrow_raw or None,
                "today_min": self._today_min,
                "today_max": self._today_max,
                "today_mean": self._today_mean,
                "tomorrow_min": self._tomorrow_min or None,
                "tomorrow_max": self._tomorrow_max or None,
                "tomorrow_mean": self._tomorrow_mean or None,
                "attribution": f"Data sourced from {self._api.source}",
            }

            if not isinstance(self.predictions, type(None)):
                self._attr_extra_state_attributes.update(
                    {
                        "forecast": self._add_raw(self.predictions),
                        "attribution": f"Data sourced from {self._api.source} "
                        "and forecast from Carnot",
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
        async_dispatcher_connect(self._hass, UPDATE_EDS, self.validate_data)

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
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "model": f"Region code: {self.region.region}",
            "manufacturer": "Energi Data Service",
        }

    @property
    def today(self) -> list:
        """Get todays prices
        Returns:
            list: sorted list where today[0] is the price of hour 00.00 - 01.00
        """
        return (
            [i.price for i in self._api.today if i]
            if not isinstance(self._api.today, type(None))
            else None
        )

    @property
    def tomorrow(self) -> list:
        """Get tomorrows prices
        Returns:
            list: sorted where tomorrow[0] is the price of hour 00.00 - 01.00 etc.
        """
        if self._api.tomorrow_valid:
            return [i.price for i in self._api.tomorrow if i]
        else:
            return None

    @property
    def predictions(self) -> list | None:
        """Return predictions (forecasts) if enabled, else None."""
        if self._forecast:
            return self._api.predictions

    @staticmethod
    def _add_raw(data) -> list:
        lst = []
        for i in data:
            ret = {
                "hour": i.hour,
                "price": i.price,
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
        self, value=None, fake_dt=None, default_currency: str = "EUR"
    ) -> float:
        """Do price calculations"""
        if value is None:
            value = self._attr_native_value

        # Convert currency from EUR
        if self._currency != default_currency:
            value = self.region.currency.convert(
                value, to_currency=self._currency, from_currency=default_currency
            )

        # Used to inject the current hour.
        # so template can be simplified using now
        if fake_dt is not None:

            def faker():
                def inner(*args, **kwargs):  # type: ignore pylint: disable=unused-argument
                    return fake_dt

                return pass_context(inner)

            template_value = self._cost_template.async_render(now=faker())
        else:
            template_value = self._cost_template.async_render()

        # The api returns prices in MWh
        if self._price_type in ("MWh", "mWh"):
            price = ((template_value / 1000) + value) * float(1 + self._vat)
        else:
            price = (
                template_value + (value / UNIT_TO_MULTIPLIER[self._price_type])
            ) * (float(1 + self._vat))

        if self._cent:
            price = price * CENT_MULTIPLIER

        # if self._api.tariff_data is not None:
        #     # Fetch tariffs automatically

        return round(price, self._decimals)

    def _format_list(
        self, data, tomorrow=False, predictions=False, default_currency: str = "EUR"
    ) -> None:
        """Format data as list with prices localized."""
        formatted_pricelist = []

        list_for = "TODAY"

        if tomorrow:
            list_for = "TOMORROW"

        if predictions:
            list_for = "FORECASTS"

        _LOGGER.debug(
            "Unformatted list for '%s':\n%s",
            list_for,
            json.dumps(data, indent=2, default=str),
        )

        _start = datetime.now().timestamp()
        Interval = namedtuple("Interval", "price hour")
        for i in data:
            price = self._calculate(
                i.price,
                fake_dt=dt_utils.as_local(i.hour),
                default_currency=default_currency,
            )
            formatted_pricelist.append(Interval(price, i.hour))

        _stop = datetime.now().timestamp()
        _ttf = round(_stop - _start, 2)

        _LOGGER.debug(
            "Formatted list for '%s':\n%s",
            list_for,
            json.dumps(formatted_pricelist, indent=2, default=str),
        )

        if tomorrow:
            _calc_for = "TOMORROW"
            self._api.tomorrow_calculated = True
            self._api.tomorrow = formatted_pricelist
        elif predictions:
            _calc_for = "PREDICTIONS"
            self._api.predictions_calculated = True
            self._api.predictions = formatted_pricelist
        else:
            _calc_for = "TODAY"
            self._api.today_calculated = True
            self._api.today = formatted_pricelist

        _LOGGER.debug(
            "Calculation for %s in %s took %s seconds",
            _calc_for,
            self.region.region,
            _ttf,
        )

    @staticmethod
    def _get_specific(datatype: str, data: list):
        """Get specific values - ie. min, max, mean values"""

        if datatype in ["MIN", "Min", "min"]:
            if data:
                res = min(data, key=lambda k: k.price)
                ret = {
                    "hour": res.hour,
                    "price": res.price,
                }

                return ret
            else:
                return None
        elif datatype in ["MAX", "Max", "max"]:
            if data:
                res = max(data, key=lambda k: k.price)
                ret = {
                    "hour": res.hour,
                    "price": res.price,
                }

                return ret
            else:
                return None
        elif datatype in ["MEAN", "Mean", "mean"]:
            if data:
                return mean(data)
            else:
                return None
        else:
            return None
