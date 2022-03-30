"""Support for Energi Data Service sensor."""
from collections import defaultdict, namedtuple
from datetime import datetime
import logging

from currency_converter import CurrencyConverter
from homeassistant.components import sensor
from homeassistant.const import DEVICE_CLASS_MONETARY, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.template import Template, attach
from homeassistant.util import dt as dt_utils, slugify as util_slugify
from jinja2 import contextfunction

from .const import (
    AREA_MAP,
    CONF_AREA,
    CONF_DECIMALS,
    CONF_PRICETYPE,
    CONF_TEMPLATE,
    CONF_VAT,
    DEFAULT_TEMPLATE,
    DOMAIN,
    PRICE_IN,
    UNIQUE_ID,
    UPDATE_EDS,
)
from .entity import EnergidataserviceEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_devices):
    """Setup sensor platform from a config entry."""
    config = config_entry.data
    _setup(hass, config, async_add_devices)
    return True


def _setup(hass, config, add_devices):
    """Setup the damn platform using yaml."""
    _LOGGER.debug("Dumping config %r", config)
    _LOGGER.debug("Timezone set in ha %r", hass.config.time_zone)
    _LOGGER.debug("Currency set in ha %r", hass.config.currency)
    area = config.get(CONF_AREA)
    price_type = config.get(CONF_PRICETYPE)
    decimals = config.get(CONF_DECIMALS)
    currency = hass.config.currency
    vat = config.get(CONF_VAT)
    cost_template = config.get(CONF_TEMPLATE)
    name = config.get(CONF_NAME)
    api = hass.data[DOMAIN]
    _LOGGER.debug("Unique_id from config: %s", config.get(UNIQUE_ID))
    sens = EnergidataserviceSensor(
        name,
        area,
        price_type,
        decimals,
        currency,
        vat,
        api,
        cost_template,
        hass,
        api.entry_id,
    )

    add_devices([sens])


@callback
def _async_migrate_unique_id(
    hass: HomeAssistant, entity: str, old_id: str, new_id: str
) -> None:
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
            tup_dict = dict(identifiers) # {'hi': 'bye', 'one': 'two'}
            tup_dict[DOMAIN] = new_id
            identifiers = tuple(tup_dict.items()) # (('one', 'two'),)
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


class EnergidataserviceSensor(EnergidataserviceEntity):
    """Representation of Energi Data Service data."""

    def __init__(
        self,
        name,
        area,
        price_type,
        decimals,
        currency,
        vat,
        api,
        cost_template,
        hass,
        entry_id,
    ) -> None:
        """Initialize Ally binary_sensor."""
        self._entry_id = entry_id
        self._area = area
        self._currency = currency
        self._price_type = price_type
        self._decimals = decimals
        self._api = api
        self._cost_template = cost_template
        self._hass = hass
        self._newstyle_unique_id = None
        if vat is True:
            self._vat = 0.25
        else:
            self._vat = 0

        ### NEW WAY
        self._friendly_name = f"{name} {area}"
        self._entity_id = sensor.ENTITY_ID_FORMAT.format(util_slugify(f"{name} {area}"))
        self._unique_id = util_slugify(f"{name}_{self._entry_id}")
        old_id = f"energidataservice_{area}"
        # self._unique_id = f"energidataservice_{self._entry_id}"
        _async_migrate_unique_id(
            hass, self._entity_id, old_id, self._unique_id
        )
        ###

        # ### OLD WAY
        # self._friendly_name = f"Energi Data Service {area}"
        # self._entity_id = sensor.ENTITY_ID_FORMAT.format(
        #     util_slugify(self._friendly_name)
        # )
        # self._unique_id = f"energidataservice_{area}"
        # # super().__init__(self._friendly_name, self._area)
        # ###

        # Holds current price
        self._state = None

        # Holds the raw data
        self._today_raw = None
        self._tomorrow_raw = None

        # Holds statistical prices for today
        self._today_min = None
        self._today_max = None

        # Holds statistical prices for tomorrow
        self._tomorrow_min = None
        self._tomorrow_max = None

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

        if not self._api.today:
            _LOGGER.debug("No sensor data found - calling update")
            await self._api.update()
            self._api.today = self._format_list(self._api.today)

        if self.tomorrow_valid:
            if not self._api.tomorrow_calculated:
                self._api.tomorrow = self._format_list(self._api.tomorrow, True)
            self._tomorrow_raw = self._add_raw(self._api.tomorrow)
        else:
            self._api.tomorrow = None
            self._tomorrow_raw = None
            self._api.tomorrow_calculated = False

        if not self._api.today_calculated:
            self._api.today = self._format_list(self._api.today)

        # Updates price for this hour.
        await self._get_current_price()

        # Update attributes
        self._today_raw = self._add_raw(self._api.today)

        self._today_min = self._get_specific("min", self._api.today)
        self._today_max = self._get_specific("max", self._api.today)
        self._tomorrow_min = self._get_specific("min", self._api.tomorrow)
        self._tomorrow_max = self._get_specific("max", self._api.tomorrow)

        self.async_write_ha_state()

    async def _get_current_price(self) -> None:
        """Get price for current hour"""
        # now = dt_utils.now()
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
                    self._state = dataset.price
                    _LOGGER.debug("Current price updated to %f", self._state)
                    break
        else:
            _LOGGER.debug("No data found, can't update _state")

    async def async_added_to_hass(self):
        """Connect to dispatcher listening for entity data notifications."""
        await super().async_added_to_hass()
        _LOGGER.debug("Added sensor '%s'", self._entity_id)
        await self.validate_data()
        async_dispatcher_connect(self._hass, UPDATE_EDS, self.validate_data)

    @staticmethod
    def _convert_currency(currency_from, currency_to, value):
        """Convert currency"""
        c = CurrencyConverter()  # pylint: disable=invalid-name
        return c.convert(value, currency_from, currency_to)

    def _calculate(self, value=None, fake_dt=None) -> float:
        """Do price calculations"""
        if value is None:
            value = self._state

        # Convert currency from EUR
        if self._currency != "EUR":
            value = self._convert_currency("EUR", self._currency, value)

        # Used to inject the current hour.
        # so template can be simplified using now
        if fake_dt is not None:

            def faker():
                def inner(*args, **kwargs):  # type: ignore pylint: disable=unused-argument
                    return fake_dt

                return contextfunction(inner)

            template_value = self._cost_template.async_render(now=faker())
        else:
            template_value = self._cost_template.async_render()

        # The api returns prices in MWh
        if self._price_type in ("MWh", "mWh"):
            price = template_value / 1000 + value * float(1 + self._vat)
        else:
            price = template_value + value / PRICE_IN[self._price_type] * (
                float(1 + self._vat)
            )

        return round(price, self._decimals)

    @property
    def unique_id(self):
        """Return the unique id."""
        return self._unique_id

    @property
    def icon(self) -> str:
        return "mdi:flash"

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._friendly_name

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def state(self):
        """Return sensor state."""
        return self._state

    @property
    def unit(self) -> str:
        """Return currency unit."""
        return self._price_type

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "unique_id": self.unique_id,
            "current_price": self.state,
            "unit": self.unit,
            "currency": self._currency,
            "area": self._area,
            "area_code": AREA_MAP[self._area],
            "tomorrow_valid": self.tomorrow_valid,
            "next_data_update": self._api.next_data_refresh,
            "today": self.today,
            "tomorrow": self.tomorrow,
            "raw_today": self.raw_today,
            "raw_tomorrow": self.raw_tomorrow,
            "today_min": self.today_min,
            "today_max": self.today_max,
            "tomorrow_min": self.tomorrow_min,
            "tomorrow_max": self.tomorrow_max,
        }

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return f"{self._currency}/{self._price_type}"

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return DEVICE_CLASS_MONETARY

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "model": f"Area code: {AREA_MAP[self._area]}",
            "manufacturer": "Energi Data Service",
        }

    @property
    def today(self) -> list:
        """Get todays prices
        Returns:
            list: sorted list where today[0] is the price of hour 00.00 - 01.00
        """

        return [i.price for i in self._api.today if i]

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

    @staticmethod
    def _add_raw(data):
        lst = []
        for i in data:
            ret = defaultdict(dict)
            ret["hour"] = i.hour
            ret["price"] = i.price
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

    def _format_list(self, data, tomorrow=False) -> list:
        """Format data as list with prices localized."""
        formatted_pricelist = []

        for i in data:
            Interval = namedtuple("Interval", "price hour")
            price = self._calculate(i.price, fake_dt=dt_utils.as_local(i.hour))
            formatted_pricelist.append(Interval(price, i.hour))

        if tomorrow:
            self._api.tomorrow_calculated = True
        else:
            self._api.today_calculated = True

        return formatted_pricelist

    @staticmethod
    def _get_specific(datatype, data):
        """Get specific values - ie. min, max, mean values"""

        if datatype in ["MIN", "Min", "min"]:
            if data:
                res = min(data, key=lambda k: k.price)
                ret = defaultdict(dict)
                ret["hour"] = res.hour
                ret["price"] = res.price

                return ret
            else:
                return None
        elif datatype in ["MAX", "Max", "max"]:
            if data:
                res = max(data, key=lambda k: k.price)
                ret = defaultdict(dict)
                ret["hour"] = res.hour
                ret["price"] = res.price

                return ret
            else:
                return None
        else:
            return None
