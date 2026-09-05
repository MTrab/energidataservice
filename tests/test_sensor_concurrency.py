"""Regression tests for concurrent price sensor updates."""

from __future__ import annotations

import asyncio
from types import MethodType, SimpleNamespace

import pytest
from homeassistant.util import dt as dt_utils

from custom_components.energidataservice.const import CONF_RESOLUTION, INTERVAL
from custom_components.energidataservice.sensor import EnergidataserviceSensor

RAW_PRICE = 109.565
CONVERSION_FACTOR = 7.46 / 1000


class ControlledHass:
    """Minimal Home Assistant executor facade with a controllable first job."""

    def __init__(self) -> None:
        """Initialize executor control events."""
        self.first_job_started = asyncio.Event()
        self.release_first_job = asyncio.Event()
        self.job_count = 0

    async def async_add_executor_job(self, target, *args):
        """Run executor jobs after optionally pausing the first one."""
        self.job_count += 1
        if self.job_count == 1:
            self.first_job_started.set()
            await self.release_first_job.wait()
        return target(*args)


def _raw_data(price: float) -> list:
    """Return raw data matching the current quarter."""
    now = dt_utils.now()
    interval_start = now.replace(
        minute=(now.minute // 15) * 15,
        second=0,
        microsecond=0,
    )
    return [INTERVAL(price, interval_start)]


def _sensor(hass: ControlledHass, raw_today: list) -> EnergidataserviceSensor:
    """Create the smallest sensor instance needed for data validation."""
    api = SimpleNamespace(
        api_today=raw_today,
        api_tomorrow=None,
        api_predictions=None,
        today=raw_today,
        tomorrow=None,
        predictions=None,
        today_calculated=False,
        tomorrow_calculated=False,
        predictions_calculated=False,
        forecast=False,
        tariff_data=None,
        tariff_connector=None,
        connector_currency="EUR",
        predictions_currency=None,
        tomorrow_valid=False,
        source="test",
        next_data_refresh="13:30:00",
    )

    sensor = object.__new__(EnergidataserviceSensor)
    sensor._api = api
    sensor._hass = hass
    sensor._validation_lock = asyncio.Lock()
    sensor._today_source = None
    sensor._tomorrow_source = None
    sensor._predictions_source = None
    sensor._tariff_data_source = None
    sensor._tariff_connector_source = None
    sensor._connector_currency_source = None
    sensor._predictions_currency_source = None
    sensor._currency = "DKK"
    sensor._forecast = False
    sensor._cent = False
    sensor._vat = 0
    sensor._price_type = "kWh"
    sensor._area = "East of the great belt"
    sensor.region = SimpleNamespace(region="DK2")
    sensor._friendly_name = "Energi Data Service"
    sensor._attr_suggested_display_precision = 3
    sensor._attr_native_unit_of_measurement = "DKK/kWh"
    sensor._config = SimpleNamespace(options={CONF_RESOLUTION: False}, data={})
    sensor._today_raw = None
    sensor._tomorrow_raw = None
    sensor._today_min = None
    sensor._today_max = None
    sensor._today_remaining_min = None
    sensor._today_remaining_max = None
    sensor._today_mean = None
    sensor._today_remaining_mean = None
    sensor._tomorrow_min = None
    sensor._tomorrow_max = None
    sensor._tomorrow_mean = None
    sensor._calculate = MethodType(
        lambda self, value=None, fake_dt=None, default_currency="EUR": (
            value * CONVERSION_FACTOR
        ),
        sensor,
    )
    return sensor


@pytest.mark.asyncio
async def test_concurrent_validation_never_publishes_raw_price() -> None:
    """A raw-list reset during validation must never reach sensor state."""
    hass = ControlledHass()
    raw_today = _raw_data(RAW_PRICE)
    sensor = _sensor(hass, raw_today)
    published_values = []
    sensor.async_write_ha_state = lambda: published_values.append(
        sensor._attr_native_value
    )

    first_validation = asyncio.create_task(sensor.validate_data())
    await hass.first_job_started.wait()

    # Reproduce the unsafe state formerly created by the quarter-hour callback.
    sensor._api.today = sensor._api.api_today
    sensor._api.today_calculated = False
    second_validation = asyncio.create_task(sensor.validate_data())

    await asyncio.sleep(0)
    assert not second_validation.done()

    hass.release_first_job.set()
    await asyncio.gather(first_validation, second_validation)

    expected_price = RAW_PRICE * CONVERSION_FACTOR
    assert hass.job_count == 1
    assert published_values == pytest.approx([expected_price, expected_price])
    assert RAW_PRICE not in published_values
    assert sensor._api.today_calculated is True
    assert sensor._api.today[0].price == pytest.approx(expected_price)


@pytest.mark.asyncio
async def test_source_replaced_during_calculation_is_recalculated() -> None:
    """Only a calculation made from the newest raw snapshot may be committed."""
    hass = ControlledHass()
    sensor = _sensor(hass, _raw_data(RAW_PRICE))
    published_values = []
    sensor.async_write_ha_state = lambda: published_values.append(
        sensor._attr_native_value
    )

    validation = asyncio.create_task(sensor.validate_data())
    await hass.first_job_started.wait()

    replacement_price = 87.25
    replacement_data = _raw_data(replacement_price)
    sensor._api.api_today = replacement_data
    sensor._api.today = replacement_data
    sensor._api.today_calculated = False

    hass.release_first_job.set()
    await validation

    expected_price = replacement_price * CONVERSION_FACTOR
    assert hass.job_count == 2
    assert published_values == pytest.approx([expected_price])
    assert RAW_PRICE not in published_values
    assert sensor._api.today[0].price == pytest.approx(expected_price)


def test_format_list_does_not_mutate_shared_api_data() -> None:
    """Formatting must return calculated data without changing its source."""
    hass = ControlledHass()
    raw_today = _raw_data(RAW_PRICE)
    sensor = _sensor(hass, raw_today)

    formatted = sensor._format_list(raw_today, default_currency="EUR")

    assert sensor._api.today is raw_today
    assert sensor._api.today_calculated is False
    assert formatted is not raw_today
    assert formatted[0].price == pytest.approx(RAW_PRICE * CONVERSION_FACTOR)


@pytest.mark.asyncio
async def test_replaced_tariffs_invalidate_calculated_prices() -> None:
    """A tariff refresh must still trigger price recalculation."""
    hass = ControlledHass()
    hass.release_first_job.set()
    sensor = _sensor(hass, _raw_data(RAW_PRICE))
    sensor.async_write_ha_state = lambda: None

    await sensor.validate_data()
    sensor._api.tariff_data = {
        "additional_tariffs": {},
        "status": 200,
        "tariffs": {},
    }
    await sensor.validate_data()

    assert hass.job_count == 2


@pytest.mark.asyncio
async def test_tomorrow_and_forecast_are_calculated_from_raw_sources() -> None:
    """Tomorrow and forecast behavior must be preserved by snapshot validation."""
    hass = ControlledHass()
    hass.release_first_job.set()
    sensor = _sensor(hass, _raw_data(RAW_PRICE))
    tomorrow_source = _raw_data(82.4)
    predictions_source = _raw_data(76.3)
    sensor._api.api_tomorrow = tomorrow_source
    sensor._api.tomorrow = tomorrow_source
    sensor._api.tomorrow_valid = True
    sensor._api.api_predictions = predictions_source
    sensor._api.predictions = predictions_source
    sensor._api.forecast = True
    sensor._forecast = True
    sensor.async_write_ha_state = lambda: None

    await sensor.validate_data()

    assert hass.job_count == 3
    assert sensor._api.tomorrow_calculated is True
    assert sensor._api.predictions_calculated is True
    assert sensor._api.tomorrow[0].price == pytest.approx(82.4 * CONVERSION_FACTOR)
    assert sensor._api.predictions[0].price == pytest.approx(76.3 * CONVERSION_FACTOR)
