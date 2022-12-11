"""Diagnostics support for Energi Data Service integration."""
from __future__ import annotations
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_UNIQUE_ID, CONF_API_KEY, CONF_EMAIL

from .const import DOMAIN

TO_REDACT = {
    CONF_UNIQUE_ID,
    CONF_API_KEY,
    CONF_EMAIL,
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    api = hass.data[DOMAIN][entry.entry_id]

    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "today": api.today,
        "today_calculated": api.today_calculated,
        "api_today": api.api_today,
        "tomorrow": api.tomorrow,
        "tomorrow_calculated": api.tomorrow_calculated,
        "api_tomorrow": api.api_tomorrow,
        "predictions": api.predictions,
        "api_predictions": api.api_predictions,
        "next_update": api.next_data_refresh,
        "data_source": api._source,
        "home_assistant_tz": hass.config.time_zone,
        "home_assistant_currency": hass.config.currency,
    }
