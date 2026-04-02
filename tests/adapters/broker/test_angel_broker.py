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
