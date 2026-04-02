"""Tests for AngelBroker — auth methods only.
SmartConnect is mocked — no real API calls made.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


@pytest.fixture
def broker_config():
    from infrastructure.config.settings import BrokerConfig
    return BrokerConfig(
        client_id="test_client",
        password="test_pass",
        totp_secret="JBSWY3DPEHPK3PXP",
        api_key="test_api_key",
    )


@pytest.fixture
def mock_smart_session():
    return {
        "status": True,
        "data": {
            "jwtToken": "Bearer test_jwt_token",
            "refreshToken": "test_refresh_token",
            "feedToken": "test_feed_token",
        },
    }


@pytest.mark.asyncio
async def test_login_success_stores_tokens(broker_config, mock_smart_session):
    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.return_value = mock_smart_session

        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        result = await broker.login()

        assert result is True
        assert broker._jwt_token == "Bearer test_jwt_token"
        assert broker._refresh_token == "test_refresh_token"
        assert broker._feed_token == "test_feed_token"
        assert broker._token_expiry is not None


@pytest.mark.asyncio
async def test_login_failure_returns_false(broker_config):
    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.return_value = {
            "status": False,
            "message": "Invalid credentials",
        }

        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        result = await broker.login()

        assert result is False
        assert broker._jwt_token is None


@pytest.mark.asyncio
async def test_login_exception_returns_false(broker_config):
    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.side_effect = Exception("Network error")

        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        result = await broker.login()

        assert result is False


@pytest.mark.asyncio
async def test_ensure_authenticated_returns_true_when_token_fresh(
    broker_config, mock_smart_session
):
    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.return_value = mock_smart_session

        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        await broker.login()

        # Token just set — not near expiry
        result = await broker.ensure_authenticated()
        assert result is True
        # generateSession called only once (during login, not again)
        assert mock_api.generateSession.call_count == 1


@pytest.mark.asyncio
async def test_ensure_authenticated_refreshes_near_expiry(
    broker_config, mock_smart_session
):
    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.return_value = mock_smart_session
        mock_api.generateToken.return_value = {
            "status": True,
            "data": {"jwtToken": "Bearer refreshed_jwt"},
        }

        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        await broker.login()

        # Force expiry to 3 minutes from now (within 5-min refresh window)
        broker._token_expiry = datetime.now() + timedelta(minutes=3)
        result = await broker.ensure_authenticated()

        assert result is True
        assert broker._jwt_token == "Bearer refreshed_jwt"
        mock_api.generateToken.assert_called_once_with("test_refresh_token")


@pytest.mark.asyncio
async def test_ensure_authenticated_falls_back_to_relogin_on_refresh_failure(
    broker_config, mock_smart_session
):
    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.return_value = mock_smart_session
        mock_api.generateToken.return_value = {
            "status": False,
            "message": "Token expired",
        }

        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        await broker.login()
        broker._token_expiry = datetime.now() + timedelta(minutes=3)

        result = await broker.ensure_authenticated()

        assert result is True
        # generateSession called twice: initial login + fallback re-login
        assert mock_api.generateSession.call_count == 2


@pytest.mark.asyncio
async def test_ensure_authenticated_returns_false_before_login(broker_config):
    with patch("adapters.broker.angel_broker.SmartConnect"):
        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        # Never logged in — token_expiry is None
        result = await broker.ensure_authenticated()
        assert result is False


@pytest.mark.asyncio
async def test_refresh_stores_new_feed_token(broker_config, mock_smart_session):
    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.return_value = mock_smart_session
        mock_api.generateToken.return_value = {
            "status": True,
            "data": {
                "jwtToken": "Bearer new_jwt",
                "feedToken": "new_feed_token",
                "refreshToken": "new_refresh_token",
            },
        }

        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        await broker.login()
        broker._token_expiry = datetime.now() + timedelta(minutes=3)
        await broker.ensure_authenticated()

        assert broker._jwt_token == "Bearer new_jwt"
        assert broker._feed_token == "new_feed_token"
        assert broker._refresh_token == "new_refresh_token"


@pytest.mark.asyncio
async def test_refresh_exception_falls_back_to_relogin(broker_config, mock_smart_session):
    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.return_value = mock_smart_session
        mock_api.generateToken.side_effect = Exception("Network error")

        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        await broker.login()
        broker._token_expiry = datetime.now() + timedelta(minutes=3)
        result = await broker.ensure_authenticated()

        assert result is True
        assert mock_api.generateSession.call_count == 2


@pytest.mark.asyncio
async def test_logout_clears_tokens(broker_config, mock_smart_session):
    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.return_value = mock_smart_session
        mock_api.terminateSession.return_value = {"status": True}

        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        await broker.login()
        assert broker._jwt_token is not None

        result = await broker.logout()

        assert result is True
        assert broker._jwt_token is None
        assert broker._refresh_token is None
        assert broker._feed_token is None
        assert broker._token_expiry is None


# ─── Data Method Tests ───

@pytest.mark.asyncio
async def test_get_historical_returns_dataframe(broker_config, mock_smart_session):
    from datetime import datetime
    import pandas as pd

    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.return_value = mock_smart_session
        mock_api.getCandleData.return_value = {
            "status": True,
            "data": [
                ["2026-01-15T09:15:00+05:30", 2440.0, 2460.0, 2435.0, 2455.0, 100000],
                ["2026-01-15T09:20:00+05:30", 2455.0, 2470.0, 2450.0, 2465.0, 80000],
            ],
        }

        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        await broker.login()

        df = await broker.get_historical(
            symbol="RELIANCE",
            token="2885",
            interval="5m",
            from_dt=datetime(2026, 1, 15, 9, 15),
            to_dt=datetime(2026, 1, 15, 15, 30),
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert list(df.columns) == ["open", "high", "low", "close", "volume"]
        assert df.index[0] == pd.Timestamp("2026-01-15 09:15:00")
        assert df.index[1] == pd.Timestamp("2026-01-15 09:20:00")


@pytest.mark.asyncio
async def test_get_historical_returns_empty_df_when_no_data(broker_config, mock_smart_session):
    from datetime import datetime
    import pandas as pd

    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.return_value = mock_smart_session
        mock_api.getCandleData.return_value = {"status": True, "data": []}

        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        await broker.login()

        df = await broker.get_historical(
            symbol="RELIANCE", token="2885", interval="5m",
            from_dt=datetime(2026, 1, 15, 9, 15),
            to_dt=datetime(2026, 1, 15, 15, 30),
        )

        assert isinstance(df, pd.DataFrame)
        assert df.empty


@pytest.mark.asyncio
async def test_get_historical_raises_on_invalid_interval(broker_config, mock_smart_session):
    from datetime import datetime

    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.return_value = mock_smart_session

        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        await broker.login()

        with pytest.raises(ValueError, match="Unsupported interval"):
            await broker.get_historical(
                symbol="RELIANCE", token="2885", interval="2m",
                from_dt=datetime(2026, 1, 15, 9, 15),
                to_dt=datetime(2026, 1, 15, 15, 30),
            )


@pytest.mark.asyncio
async def test_get_funds_returns_dict(broker_config, mock_smart_session):
    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.return_value = mock_smart_session
        mock_api.rmsLimit.return_value = {
            "status": True,
            "data": {"availablecash": "95000.00", "utilisedamount": "5000.00"},
        }

        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        await broker.login()
        funds = await broker.get_funds()

        assert isinstance(funds, dict)
        assert "availablecash" in funds


@pytest.mark.asyncio
async def test_get_positions_returns_list(broker_config, mock_smart_session):
    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.return_value = mock_smart_session
        mock_api.position.return_value = {
            "status": True,
            "data": [
                {"tradingsymbol": "RELIANCE", "netqty": "18", "ltp": "2465.00"},
            ],
        }

        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        await broker.login()
        positions = await broker.get_positions()

        assert isinstance(positions, list)
        assert len(positions) == 1


@pytest.mark.asyncio
async def test_get_orders_returns_list(broker_config, mock_smart_session):
    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.return_value = mock_smart_session
        mock_api.orderBook.return_value = {
            "status": True,
            "data": [
                {"orderid": "111111", "tradingsymbol": "RELIANCE", "status": "COMPLETE"},
            ],
        }

        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        await broker.login()
        orders = await broker.get_orders()

        assert isinstance(orders, list)
        assert len(orders) == 1


@pytest.mark.asyncio
async def test_get_ltp_returns_dict(broker_config, mock_smart_session):
    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.return_value = mock_smart_session
        mock_api.ltpData.return_value = {
            "status": True,
            "data": {"ltp": "2465.50"},
        }

        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        await broker.login()
        result = await broker.get_ltp([("NSE", "RELIANCE", "2885")])

        assert isinstance(result, dict)
        assert "RELIANCE" in result
        assert result["RELIANCE"] == pytest.approx(2465.50)
