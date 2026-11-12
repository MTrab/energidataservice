"""Regression tests for forecast failures and setup retries."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

from aiohttp import ClientError, ConnectionTimeoutError, ServerDisconnectedError
from homeassistant.exceptions import ConfigEntryNotReady

import custom_components.energidataservice as integration
from custom_components.energidataservice.api import APIConnector
from custom_components.energidataservice.const import CONF_ENABLE_FORECAST, DOMAIN
from custom_components.energidataservice.forecasts.carnot import (
    REQUEST_TIMEOUT,
    Connector,
)


def _forecast_api():
    """Create an API connector with a mocked forecast endpoint."""
    forecast = AsyncMock()
    module = SimpleNamespace(
        Connector=Mock(return_value=forecast), DEFAULT_CURRENCY="DKK"
    )
    api = object.__new__(APIConnector)
    api.forecast = True
    api.forecasts = SimpleNamespace(
        get_endpoint=AsyncMock(return_value=[SimpleNamespace(namespace="test")])
    )
    api.hass = SimpleNamespace(async_add_executor_job=AsyncMock(return_value=module))
    api._region = SimpleNamespace(region="DK1")
    api._client = Mock()
    api._tz = UTC
    api._version = "test"
    api._carnot_apikey = "test-key"
    api._carnot_user = "test-user"
    api._tomorrow_valid = False
    api.predictions = None
    api.api_predictions = None
    api.today = [1]
    api.api_today = api.today
    return api, forecast


class ForecastFailureTests(IsolatedAsyncioTestCase):
    """Keep optional forecast failures separate from spot price availability."""

    def setUp(self) -> None:
        """Create a connector without loading external APIs."""
        self.api, self.forecast = _forecast_api()

    async def test_network_errors_leave_spot_prices_available(self) -> None:
        """Transport errors must not escape the forecast update."""
        for error in (
            TimeoutError(),
            ConnectionTimeoutError(),
            ServerDisconnectedError(),
            ClientError(),
        ):
            with self.subTest(error=type(error).__name__):
                self.forecast.async_get_forecast.side_effect = error
                await self.api.update_carnot()
                self.assertEqual(self.api.today, [1])
                self.assertIs(self.api.today, self.api.api_today)
                self.assertIsNone(self.api.api_predictions)

    async def test_next_update_recovers_after_timeout(self) -> None:
        """A later successful request must publish its forecast."""
        predictions = [SimpleNamespace(time=datetime.now(UTC) + timedelta(days=2))]
        self.forecast.async_get_forecast.side_effect = [TimeoutError(), predictions]
        await self.api.update_carnot()
        await self.api.update_carnot()
        self.assertIs(self.api.api_predictions, predictions)

    async def test_timeout_preserves_cached_forecast(self) -> None:
        """Keep the previous forecast when the request fails."""
        cached = [SimpleNamespace(time=datetime.now(UTC) + timedelta(days=2))]
        self.api.predictions = cached
        self.api.api_predictions = cached
        self.forecast.async_get_forecast.side_effect = TimeoutError()
        await self.api.update_carnot()
        self.assertIs(self.api.api_predictions, cached)
        self.assertEqual(len(cached), 1)

    async def test_cancellation_propagates(self) -> None:
        """Home Assistant must still be able to cancel an in-flight fetch."""
        self.forecast.async_get_forecast.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.api.update_carnot()


class SetupRetryTests(IsolatedAsyncioTestCase):
    """Retry failed initial fetches without leaving callbacks behind."""

    def setUp(self) -> None:
        """Create the setup dependencies and record scheduled callbacks."""
        self.entry = SimpleNamespace(
            entry_id="test", options={CONF_ENABLE_FORECAST: True}
        )
        self.hass = SimpleNamespace(
            data={DOMAIN: {}},
            config_entries=SimpleNamespace(async_forward_entry_setups=AsyncMock()),
        )
        self.api = SimpleNamespace(
            initialize=AsyncMock(),
            _connectors=SimpleNamespace(get_connectors=Mock(return_value=[])),
            _region=SimpleNamespace(region="DK1"),
            update=AsyncMock(),
            update_carnot=AsyncMock(),
            async_get_tariffs=AsyncMock(),
            updateco2=AsyncMock(),
            cancel_retry_updates=Mock(),
            listeners=[],
            is_unloading=False,
        )
        self.schedule = Mock(side_effect=lambda *args, **kwargs: Mock())
        self.track = Mock(side_effect=lambda *args, **kwargs: Mock())
        self.enterContext(
            patch.object(integration, "APIConnector", return_value=self.api)
        )
        self.enterContext(
            patch.object(
                integration,
                "async_get_integration",
                AsyncMock(return_value=SimpleNamespace(version="test")),
            )
        )
        self.enterContext(patch.object(integration, "async_call_later", self.schedule))
        self.enterContext(
            patch.object(integration, "async_track_time_change", self.track)
        )
        self.enterContext(patch.object(integration, "async_dispatcher_send"))

    async def test_initial_network_failure_requests_setup_retry(self) -> None:
        """Initial transport errors must request Home Assistant's setup retry."""
        for error in (TimeoutError(), ClientError()):
            with self.subTest(error=type(error).__name__):
                self.api.update.side_effect = error
                with self.assertRaises(ConfigEntryNotReady) as raised:
                    await integration._setup(self.hass, self.entry)
                self.assertIs(raised.exception.__cause__, error)
                self.assertNotIn(self.entry.entry_id, self.hass.data[DOMAIN])
                self.assertTrue(self.api.is_unloading)
                self.api.cancel_retry_updates.assert_called()
                self.track.assert_not_called()
                self.schedule.assert_not_called()

    async def test_tariff_setup_retry_cancels_pending_retries(self) -> None:
        """An existing setup-retry exception must also clean up API callbacks."""
        error = ConfigEntryNotReady("Invalid charge owner")
        self.api.async_get_tariffs.side_effect = error
        with self.assertRaises(ConfigEntryNotReady) as raised:
            await integration._setup(self.hass, self.entry)
        self.assertIs(raised.exception, error)
        self.api.cancel_retry_updates.assert_called_once()
        self.track.assert_not_called()
        self.assertNotIn(self.entry.entry_id, self.hass.data[DOMAIN])

    async def test_timeout_does_not_stop_periodic_forecasts(self) -> None:
        """A handled timeout must allow the periodic callback to reschedule."""

        async def failed_forecast(*args):
            """Run the real forecast error handler with a failing request."""
            api, forecast = _forecast_api()
            forecast.async_get_forecast.side_effect = TimeoutError()
            await api.update_carnot()

        self.api.update_carnot.side_effect = failed_forecast
        self.assertTrue(await integration._setup(self.hass, self.entry))
        self.assertIs(self.hass.data[DOMAIN][self.entry.entry_id], self.api)
        self.api.async_get_tariffs.assert_awaited_once()
        callback = self.schedule.call_args.args[2]
        self.schedule.reset_mock()
        await callback(None)
        self.schedule.assert_called_once_with(
            self.hass, integration.CARNOT_UPDATE, callback
        )
        started = asyncio.Event()
        release = asyncio.Event()

        async def delayed_forecast(*args):
            """Hold the request open while the entry unloads."""
            started.set()
            await release.wait()
            await failed_forecast()

        self.api.update_carnot.side_effect = delayed_forecast
        self.schedule.reset_mock()
        update = asyncio.create_task(callback(None))
        await started.wait()
        self.api.is_unloading = True
        release.set()
        await update
        self.schedule.assert_not_called()


class CarnotRequestTests(IsolatedAsyncioTestCase):
    """Bound requests and release their responses."""

    async def test_request_timeout_and_response_cleanup(self) -> None:
        """JSON failures must release the response and propagate for handling."""
        response = AsyncMock()
        response.status = 200
        response.json.side_effect = TimeoutError()
        context = AsyncMock()
        context.__aenter__.return_value = response
        client = SimpleNamespace(get=Mock(return_value=context))
        connector = Connector(SimpleNamespace(region="DK1"), client, UTC, "test")
        with self.assertRaises(TimeoutError):
            await connector.async_get_forecast("test-key", "test-user")
        self.assertEqual(client.get.call_args.kwargs["timeout"], REQUEST_TIMEOUT)
        self.assertEqual(REQUEST_TIMEOUT.total, 30)
        context.__aexit__.assert_awaited_once()
