"""Regression test for current_price on the DST fall-back (25-hour) day."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from homeassistant.util import dt as dt_utils

from custom_components.energidataservice.const import CONF_RESOLUTION, INTERVAL
from test_sensor_concurrency import ControlledHass, _sensor

CEST = timezone(timedelta(hours=2))
CET = timezone(timedelta(hours=1))


def _dst_fallback_today() -> list[INTERVAL]:
    """Build a 25-entry hourly dataset like the one produced on DST fall-back day.

    Hour 02 occurs twice (once in CEST, once in CET), matching the real
    data returned by the API on the day clocks go back.
    """
    data = [
        INTERVAL(float(hour), datetime(2026, 10, 25, hour, tzinfo=CEST))
        for hour in range(3)
    ]
    data += [
        INTERVAL(float(hour) + 100, datetime(2026, 10, 25, hour, tzinfo=CET))
        for hour in range(2, 24)
    ]
    return data


def test_current_price_resolves_on_dst_fallback_day(monkeypatch) -> None:
    """A 25-entry today list must still resolve the current hour's price."""
    hass = ControlledHass()
    sensor = _sensor(hass, [])
    sensor._config.options[CONF_RESOLUTION] = True
    sensor._api.today = _dst_fallback_today()

    now = datetime(2026, 10, 25, 15, 30, tzinfo=CET)
    monkeypatch.setattr(dt_utils, "now", lambda: now)

    sensor._get_current_price()

    assert sensor._attr_native_value == pytest.approx(115.0)


def test_current_price_picks_correct_duplicate_hour(monkeypatch) -> None:
    """The second (post-transition) 02:00 slot must win over the first."""
    hass = ControlledHass()
    sensor = _sensor(hass, [])
    sensor._config.options[CONF_RESOLUTION] = True
    sensor._api.today = _dst_fallback_today()

    # 02:30 CET is only inside the second 02:00 entry's window.
    now = datetime(2026, 10, 25, 2, 30, tzinfo=CET)
    monkeypatch.setattr(dt_utils, "now", lambda: now)

    sensor._get_current_price()

    assert sensor._attr_native_value == pytest.approx(102.0)
