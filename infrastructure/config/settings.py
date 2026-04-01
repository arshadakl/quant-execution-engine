"""Config loader — loads secrets from .env, non-secrets from settings.yaml."""
import logging
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_YAML_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "settings.yaml"


def _load_yaml() -> dict:
    if not _YAML_PATH.exists():
        logger.warning("settings.yaml not found at %s", _YAML_PATH)
        return {}
    with open(_YAML_PATH) as f:
        return yaml.safe_load(f) or {}


class BrokerConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ANGEL_",
        extra="ignore",
    )

    client_id: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    totp_secret: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)


class TradingConfig(BaseModel):
    mode: str = "paper"
    paper_capital: float = 100000.0

    @field_validator("mode")
    @classmethod
    def mode_must_be_valid(cls, v: str) -> str:
        if v not in ("paper", "live"):
            raise ValueError(f"mode must be 'paper' or 'live', got {v!r}")
        return v


class RiskConfig(BaseModel):
    max_capital_usage_percent: float = 60.0
    per_trade_risk_percent: float = 1.5
    max_position_size_percent: float = 15.0
    max_daily_loss_percent: float = 3.0
    max_daily_trades: int = 10
    max_open_positions: int = 5
    mandatory_stop_loss: bool = True
    max_stop_loss_percent: float = 2.0
    trailing_stop_enabled: bool = True
    trailing_stop_trigger_percent: float = 1.0
    trailing_stop_distance_percent: float = 0.5
    no_new_trades_after: str = "14:30"
    force_square_off_time: str = "15:10"
    no_trade_first_minutes: int = 3
    cooldown_after_consecutive_losses: int = 3
    cooldown_duration_minutes: int = 30


class Settings:
    broker: BrokerConfig
    trading: TradingConfig
    risk: RiskConfig

    def __init__(self) -> None:
        self.broker = BrokerConfig()
        _yaml = _load_yaml()
        self.trading = TradingConfig(**_yaml.get("trading", {}))
        self.risk = RiskConfig(**_yaml.get("risk", {}))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the application settings singleton.

    Cached after first call. Call get_settings.cache_clear() in tests
    that need a fresh instance with different env vars.
    """
    return Settings()
