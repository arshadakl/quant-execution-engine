"""Tests for config loader — settings.py"""
import pytest
from pydantic import ValidationError


def test_broker_config_loads_from_env_vars(monkeypatch):
    monkeypatch.setenv("ANGEL_CLIENT_ID", "test_client")
    monkeypatch.setenv("ANGEL_PASSWORD", "test_pass")
    monkeypatch.setenv("ANGEL_TOTP_SECRET", "JBSWY3DPEHPK3PXP")
    monkeypatch.setenv("ANGEL_API_KEY", "test_api_key")

    from infrastructure.config.settings import BrokerConfig
    config = BrokerConfig()

    assert config.client_id == "test_client"
    assert config.password == "test_pass"
    assert config.totp_secret == "JBSWY3DPEHPK3PXP"
    assert config.api_key == "test_api_key"


def test_broker_config_fails_without_required_fields():
    from infrastructure.config.settings import BrokerConfig
    with pytest.raises(ValidationError):
        BrokerConfig(
            client_id="",
            password="",
            totp_secret="",
            api_key="",
        )


def test_risk_config_has_correct_defaults():
    from infrastructure.config.settings import RiskConfig
    config = RiskConfig()
    assert config.max_daily_loss_percent == 3.0
    assert config.max_open_positions == 5
    assert config.mandatory_stop_loss is True
    assert config.no_new_trades_after == "14:30"
    assert config.force_square_off_time == "15:10"


def test_trading_config_defaults_to_paper_mode():
    from infrastructure.config.settings import TradingConfig
    config = TradingConfig()
    assert config.mode == "paper"
    assert config.paper_capital == 100000.0


def test_trading_config_rejects_invalid_mode():
    from infrastructure.config.settings import TradingConfig
    with pytest.raises(ValidationError):
        TradingConfig(mode="simulation")


def test_get_settings_returns_singleton(monkeypatch):
    monkeypatch.setenv("ANGEL_CLIENT_ID", "x")
    monkeypatch.setenv("ANGEL_PASSWORD", "x")
    monkeypatch.setenv("ANGEL_TOTP_SECRET", "JBSWY3DPEHPK3PXP")
    monkeypatch.setenv("ANGEL_API_KEY", "x")

    from infrastructure.config.settings import get_settings
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
