"""Tests for DataFeed — WebSocket tick subscription with auto-resubscription."""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def feed_params():
    return {
        "auth_token": "Bearer test_jwt",
        "api_key": "test_api_key",
        "client_id": "test_client",
        "feed_token": "test_feed_token",
    }


@pytest.mark.asyncio
async def test_connect_initializes_websocket(feed_params):
    with patch("adapters.data.data_feed.SmartWebSocketV2") as mock_ws_cls:
        mock_ws = MagicMock()
        mock_ws_cls.return_value = mock_ws
        mock_ws.connect = MagicMock()

        from adapters.data.data_feed import DataFeed
        feed = DataFeed(**feed_params)
        await feed.connect()

        mock_ws_cls.assert_called_once_with(
            feed_params["auth_token"],
            feed_params["api_key"],
            feed_params["client_id"],
            feed_params["feed_token"],
            max_retry_attempt=5,
        )


def test_set_tick_callback_stores_callback(feed_params):
    from adapters.data.data_feed import DataFeed
    feed = DataFeed(**feed_params)
    cb = MagicMock()
    feed.set_tick_callback(cb)
    assert feed._tick_callback is cb


def test_on_data_invokes_tick_callback(feed_params):
    from adapters.data.data_feed import DataFeed
    feed = DataFeed(**feed_params)
    cb = MagicMock()
    feed.set_tick_callback(cb)

    tick = {"token": "2885", "ltp": 245000, "volume": 5000}
    feed._on_data(MagicMock(), tick)

    cb.assert_called_once_with(tick)


def test_on_data_without_callback_does_not_raise(feed_params):
    from adapters.data.data_feed import DataFeed
    feed = DataFeed(**feed_params)
    feed._on_data(MagicMock(), {"token": "2885"})


def test_subscribe_stores_tokens_and_calls_ws(feed_params):
    with patch("adapters.data.data_feed.SmartWebSocketV2"):
        from adapters.data.data_feed import DataFeed
        feed = DataFeed(**feed_params)
        feed._sws = MagicMock()

        tokens = [{"exchangeType": 1, "tokens": ["2885", "1594"]}]
        feed.subscribe(tokens)

        assert feed._subscribed_tokens == tokens
        feed._sws.subscribe.assert_called_once()


def test_on_open_resubscribes_existing_tokens(feed_params):
    with patch("adapters.data.data_feed.SmartWebSocketV2"):
        from adapters.data.data_feed import DataFeed
        feed = DataFeed(**feed_params)
        feed._sws = MagicMock()
        feed._subscribed_tokens = [{"exchangeType": 1, "tokens": ["2885"]}]

        feed._on_open(MagicMock())

        feed._sws.subscribe.assert_called_once()


def test_on_open_with_no_subscriptions_does_not_subscribe(feed_params):
    with patch("adapters.data.data_feed.SmartWebSocketV2"):
        from adapters.data.data_feed import DataFeed
        feed = DataFeed(**feed_params)
        feed._sws = MagicMock()

        feed._on_open(MagicMock())

        feed._sws.subscribe.assert_not_called()


@pytest.mark.asyncio
async def test_disconnect_closes_connection(feed_params):
    with patch("adapters.data.data_feed.SmartWebSocketV2"):
        from adapters.data.data_feed import DataFeed
        feed = DataFeed(**feed_params)
        mock_sws = MagicMock()
        feed._sws = mock_sws
        await feed.disconnect()

        mock_sws.close_connection.assert_called_once()


def test_disconnect_when_not_connected_does_not_raise(feed_params):
    with patch("adapters.data.data_feed.SmartWebSocketV2"):
        from adapters.data.data_feed import DataFeed
        feed = DataFeed(**feed_params)
        # _sws is None — must not raise
        import asyncio
        asyncio.get_event_loop().run_until_complete(feed.disconnect())
