# Stage 1 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Working project skeleton with Angel One broker connection, historical data fetching, WebSocket tick feed, and Parquet data caching — all tested and committed to `stage-1/foundation`.

**Architecture:** Clean Architecture layers — entities and interfaces are pure Python with zero external dependencies; adapters wrap Angel One SmartAPI using `asyncio.to_thread` for async compatibility; infrastructure handles config loading via `pydantic-settings`.

**Tech Stack:** Python 3.11+, smartapi-python, pyotp, pydantic-settings, PyYAML, pandas, pyarrow, aiohttp, python-json-logger, pytest, pytest-asyncio, pytest-mock, pre-commit

---

## File Map

```
algotrader-india/
├── core/
│   ├── __init__.py
│   ├── entities/
│   │   ├── __init__.py
│   │   ├── signal.py          # Signal frozen dataclass
│   │   ├── trade.py           # Trade frozen dataclass
│   │   ├── order.py           # Order frozen dataclass
│   │   └── position.py        # Position frozen dataclass + computed props
│   └── interfaces/
│       ├── __init__.py
│       ├── i_broker.py        # IOrderBroker + IDataBroker protocols
│       └── i_data_feed.py     # IDataFeed protocol
├── adapters/
│   ├── __init__.py
│   ├── broker/
│   │   ├── __init__.py
│   │   └── angel_broker.py    # AngelBroker — auth + all data methods
│   └── data/
│       ├── __init__.py
│       ├── data_feed.py       # DataFeed — WebSocket tick subscription
│       └── data_cacher.py     # DataCacher — Parquet cache read/write
├── infrastructure/
│   ├── __init__.py
│   └── config/
│       ├── __init__.py
│       └── settings.py        # BrokerConfig, RiskConfig, TradingConfig, get_settings()
├── tests/
│   ├── __init__.py
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   └── config/
│   │       ├── __init__.py
│   │       └── test_settings.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── entities/
│   │       ├── __init__.py
│   │       └── test_entities.py
│   └── adapters/
│       ├── __init__.py
│       ├── broker/
│       │   ├── __init__.py
│       │   └── test_angel_broker.py
│       └── data/
│           ├── __init__.py
│           ├── test_data_feed.py
│           └── test_data_cacher.py
├── config/
│   ├── settings.yaml
│   └── stock_universe.yaml
├── scripts/
│   └── run_bot.py
├── data/
│   ├── historical/
│   ├── logs/
│   └── reports/
├── requirements.txt
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── pytest.ini
└── CLAUDE.md                  # Already created — do not recreate
```

---

## Task 1: Project Scaffold

**Files:**
- Create: all directories + root config files listed above
- Modify: `CLAUDE.md` (update Session 1 status)

- [ ] **Step 1: Initialize git and create stage branch**

```bash
cd D:/Own/NVPs/algo
git init
git checkout -b stage-1/foundation
```

Expected output: `Switched to a new branch 'stage-1/foundation'`

- [ ] **Step 2: Create requirements.txt**

```
# Broker
smartapi-python>=1.3.7
pyotp>=2.9.0
websocket-client>=1.6.0

# Data
pandas>=2.0.0
numpy>=1.24.0
pyarrow>=12.0.0

# Config
pydantic>=2.0.0
pydantic-settings>=2.0.0
PyYAML>=6.0.0

# Async
aiohttp>=3.8.0

# Logging
python-json-logger>=2.0.7

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-mock>=3.11.0

# Dev
pre-commit>=3.3.0
detect-secrets>=1.4.0
```

- [ ] **Step 3: Create .gitignore**

```
# Secrets — NEVER commit
.env
*.env

# Python
*.pyc
__pycache__/
*.pyo
*.pyd
.Python

# Testing
.pytest_cache/
.coverage
htmlcov/

# Data (generated at runtime)
data/historical/
data/logs/
data/reports/
*.db

# Virtual environments
venv/
.venv/
env/

# Build
dist/
build/
*.egg-info/

# IDE
.vscode/
.idea/
*.swp
```

- [ ] **Step 4: Create .env.example**

```
# Angel One SmartAPI credentials
ANGEL_CLIENT_ID=your_client_id_here
ANGEL_PASSWORD=your_password_here
ANGEL_TOTP_SECRET=your_totp_secret_here
ANGEL_API_KEY=your_api_key_here

# Telegram notifications
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

- [ ] **Step 5: Create pytest.ini**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

- [ ] **Step 6: Create .pre-commit-config.yaml**

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: detect-private-key
      - id: check-added-large-files
        args: ["--maxkb=1000"]
      - id: check-merge-conflict
      - id: end-of-file-fixer
      - id: trailing-whitespace
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
```

- [ ] **Step 7: Create config/settings.yaml**

```yaml
# ─── Trading Mode ───
trading:
  mode: "paper"
  paper_capital: 100000

# ─── Risk Management ───
risk:
  max_capital_usage_percent: 60
  per_trade_risk_percent: 1.5
  max_position_size_percent: 15
  max_daily_loss_percent: 3.0
  max_daily_trades: 10
  max_open_positions: 5
  mandatory_stop_loss: true
  max_stop_loss_percent: 2.0
  trailing_stop_enabled: true
  trailing_stop_trigger_percent: 1.0
  trailing_stop_distance_percent: 0.5
  no_new_trades_after: "14:30"
  force_square_off_time: "15:10"
  no_trade_first_minutes: 3
  cooldown_after_consecutive_losses: 3
  cooldown_duration_minutes: 30

# ─── Scanner ───
scanner:
  min_volume: 500000
  min_turnover_cr: 10
  price_range: [100, 5000]
  min_atr_percent: 1.5
  max_stocks: 15
  scan_time: "08:50"

# ─── Schedule ───
schedule:
  market_open: "09:15"
  market_close: "15:30"
  scanner_run: "08:50"
  square_off_check: "15:10"
```

- [ ] **Step 8: Create config/stock_universe.yaml**

```yaml
# NSE equity universe filters
universe:
  exchange: "NSE"
  index_filters:
    - "NIFTY500"
  exclude_sectors:
    - "REALTY"

# Manual overrides — always include these if they pass filters
watchlist_override: []
```

- [ ] **Step 9: Create all __init__.py files and directory structure**

```bash
# Run from D:/Own/NVPs/algo
mkdir -p core/entities core/interfaces
mkdir -p adapters/broker adapters/data
mkdir -p infrastructure/config
mkdir -p tests/infrastructure/config tests/core/entities tests/adapters/broker tests/adapters/data
mkdir -p scripts data/historical data/logs data/reports

touch core/__init__.py core/entities/__init__.py core/interfaces/__init__.py
touch adapters/__init__.py adapters/broker/__init__.py adapters/data/__init__.py
touch infrastructure/__init__.py infrastructure/config/__init__.py
touch tests/__init__.py
touch tests/infrastructure/__init__.py tests/infrastructure/config/__init__.py
touch tests/core/__init__.py tests/core/entities/__init__.py
touch tests/adapters/__init__.py tests/adapters/broker/__init__.py tests/adapters/data/__init__.py
```

- [ ] **Step 10: Create scripts/run_bot.py (entry point stub)**

```python
"""Main entry point — runs the trading bot."""
import asyncio
import logging
from infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


def main() -> None:
    settings = get_settings()
    logger.info("AlgoTrader India starting in %s mode", settings.trading.mode)


if __name__ == "__main__":
    main()
```

- [ ] **Step 11: Install dependencies**

```bash
python -m venv venv
source venv/Scripts/activate  # Windows
pip install -r requirements.txt
```

Expected: All packages install without errors.

- [ ] **Step 12: Install pre-commit hooks**

```bash
pre-commit install
pre-commit run --all-files
```

Expected: `detect-private-key` and other hooks run. Ignore `detect-secrets` baseline warning for now — no secrets exist yet.

- [ ] **Step 13: Commit scaffold**

```bash
git add requirements.txt .gitignore .env.example pytest.ini .pre-commit-config.yaml
git add config/ scripts/ core/__init__.py adapters/__init__.py infrastructure/__init__.py
git add tests/ CLAUDE.md docs/
git commit -m "feat(stage-1): project scaffold — directories, config, pre-commit hooks"
```

- [ ] **Step 14: Update CLAUDE.md**

In the Stage 1 Module Status table, change Session 1 (Project scaffold) from `PENDING` to `DONE`.
Add to Session Log:
```
### 2026-04-01
- Stage 1, Session 1: Project scaffold — git init, directories, requirements, pre-commit
- Next: Config loader (infrastructure/config/settings.py)
```

---

## Task 2: Config Loader

**Files:**
- Create: `infrastructure/config/settings.py`
- Create: `tests/infrastructure/config/test_settings.py`

- [ ] **Step 1: Write failing tests**

Create `tests/infrastructure/config/test_settings.py`:

```python
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
        # Pass empty strings — pydantic will reject missing required fields
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


def test_get_settings_returns_singleton(monkeypatch):
    monkeypatch.setenv("ANGEL_CLIENT_ID", "x")
    monkeypatch.setenv("ANGEL_PASSWORD", "x")
    monkeypatch.setenv("ANGEL_TOTP_SECRET", "JBSWY3DPEHPK3PXP")
    monkeypatch.setenv("ANGEL_API_KEY", "x")

    from infrastructure.config.settings import get_settings
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/infrastructure/config/test_settings.py -v
```

Expected: `ModuleNotFoundError: No module named 'infrastructure.config.settings'`

- [ ] **Step 3: Implement infrastructure/config/settings.py**

```python
"""Config loader — loads secrets from .env, non-secrets from settings.yaml."""
import logging
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_YAML_PATH = Path("config/settings.yaml")


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


class TradingConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    mode: str = "paper"
    paper_capital: float = 100000.0

    @field_validator("mode")
    @classmethod
    def mode_must_be_valid(cls, v: str) -> str:
        if v not in ("paper", "live"):
            raise ValueError(f"mode must be 'paper' or 'live', got {v!r}")
        return v


class RiskConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

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
    def __init__(self) -> None:
        self.broker = BrokerConfig()
        _yaml = _load_yaml()
        self.trading = TradingConfig(**_yaml.get("trading", {}))
        self.risk = RiskConfig(**_yaml.get("risk", {}))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run tests — must pass**

```bash
pytest tests/infrastructure/config/test_settings.py -v
```

Expected:
```
PASSED tests/infrastructure/config/test_settings.py::test_broker_config_loads_from_env_vars
PASSED tests/infrastructure/config/test_settings.py::test_broker_config_fails_without_required_fields
PASSED tests/infrastructure/config/test_settings.py::test_risk_config_has_correct_defaults
PASSED tests/infrastructure/config/test_settings.py::test_trading_config_defaults_to_paper_mode
PASSED tests/infrastructure/config/test_settings.py::test_get_settings_returns_singleton
5 passed
```

- [ ] **Step 5: Commit**

```bash
git add infrastructure/config/settings.py tests/infrastructure/config/test_settings.py
git commit -m "feat(stage-1): config loader — pydantic-settings with .env + yaml, fail-fast validation"
```

- [ ] **Step 6: Update CLAUDE.md — mark Session 2 DONE**

---

## Task 3: Base Entities + Interfaces

**Files:**
- Create: `core/entities/signal.py`
- Create: `core/entities/order.py`
- Create: `core/entities/trade.py`
- Create: `core/entities/position.py`
- Create: `core/interfaces/i_broker.py`
- Create: `core/interfaces/i_data_feed.py`
- Create: `tests/core/entities/test_entities.py`

- [ ] **Step 1: Write failing tests**

Create `tests/core/entities/test_entities.py`:

```python
"""Tests for core entity dataclasses — all must be frozen and validated."""
import pytest
from datetime import datetime


# ─── Signal ───

def test_signal_creates_with_valid_data():
    from core.entities.signal import Signal
    sig = Signal(
        strategy="ORB",
        symbol="RELIANCE",
        direction="LONG",
        entry_price=2450.0,
        stop_loss=2430.0,
        target_1=2490.0,
        timestamp=datetime(2026, 1, 15, 9, 31),
        confidence=0.85,
    )
    assert sig.symbol == "RELIANCE"
    assert sig.direction == "LONG"
    assert sig.target_2 is None


def test_signal_is_frozen():
    from core.entities.signal import Signal
    sig = Signal(
        strategy="ORB", symbol="RELIANCE", direction="LONG",
        entry_price=2450.0, stop_loss=2430.0, target_1=2490.0,
        timestamp=datetime(2026, 1, 15, 9, 31),
    )
    with pytest.raises(Exception):  # FrozenInstanceError
        sig.symbol = "INFY"


def test_signal_rejects_invalid_direction():
    from core.entities.signal import Signal
    with pytest.raises(ValueError, match="direction"):
        Signal(
            strategy="ORB", symbol="RELIANCE", direction="SIDEWAYS",
            entry_price=2450.0, stop_loss=2430.0, target_1=2490.0,
            timestamp=datetime(2026, 1, 15, 9, 31),
        )


def test_signal_rejects_negative_entry_price():
    from core.entities.signal import Signal
    with pytest.raises(ValueError, match="entry_price"):
        Signal(
            strategy="ORB", symbol="RELIANCE", direction="LONG",
            entry_price=-100.0, stop_loss=2430.0, target_1=2490.0,
            timestamp=datetime(2026, 1, 15, 9, 31),
        )


def test_signal_rejects_confidence_out_of_range():
    from core.entities.signal import Signal
    with pytest.raises(ValueError, match="confidence"):
        Signal(
            strategy="ORB", symbol="RELIANCE", direction="LONG",
            entry_price=2450.0, stop_loss=2430.0, target_1=2490.0,
            timestamp=datetime(2026, 1, 15, 9, 31),
            confidence=1.5,
        )


# ─── Order ───

def test_order_creates_with_valid_data():
    from core.entities.order import Order, OrderStatus, OrderType, TransactionType
    order = Order(
        order_id="123456",
        symbol="RELIANCE",
        token="2885",
        transaction_type=TransactionType.BUY,
        order_type=OrderType.LIMIT,
        quantity=18,
        price=2450.0,
        trigger_price=None,
        status=OrderStatus.PENDING,
        timestamp=datetime(2026, 1, 15, 9, 31),
    )
    assert order.order_id == "123456"
    assert order.status == OrderStatus.PENDING


def test_order_is_frozen():
    from core.entities.order import Order, OrderStatus, OrderType, TransactionType
    order = Order(
        order_id="123456", symbol="RELIANCE", token="2885",
        transaction_type=TransactionType.BUY, order_type=OrderType.LIMIT,
        quantity=18, price=2450.0, trigger_price=None,
        status=OrderStatus.PENDING, timestamp=datetime(2026, 1, 15, 9, 31),
    )
    with pytest.raises(Exception):
        order.status = OrderStatus.FILLED


# ─── Trade ───

def test_trade_creates_open():
    from core.entities.trade import Trade
    trade = Trade(
        trade_id="T001",
        symbol="RELIANCE",
        strategy="ORB",
        direction="LONG",
        entry_price=2450.0,
        quantity=18,
        stop_loss=2430.0,
        target_1=2490.0,
        entry_time=datetime(2026, 1, 15, 9, 31),
    )
    assert trade.exit_price is None
    assert trade.pnl is None


def test_trade_is_frozen():
    from core.entities.trade import Trade
    trade = Trade(
        trade_id="T001", symbol="RELIANCE", strategy="ORB",
        direction="LONG", entry_price=2450.0, quantity=18,
        stop_loss=2430.0, target_1=2490.0,
        entry_time=datetime(2026, 1, 15, 9, 31),
    )
    with pytest.raises(Exception):
        trade.exit_price = 2490.0


# ─── Position ───

def test_position_long_unrealized_pnl():
    from core.entities.position import Position
    pos = Position(
        symbol="RELIANCE",
        direction="LONG",
        entry_price=2450.0,
        current_price=2470.0,
        quantity=18,
        stop_loss=2430.0,
        target_1=2490.0,
        strategy="ORB",
        entry_time=datetime(2026, 1, 15, 9, 31),
        entry_order_id="123456",
    )
    assert pos.unrealized_pnl == pytest.approx(18 * 20.0)
    assert pos.unrealized_pnl_percent == pytest.approx((20 / 2450) * 100)


def test_position_short_unrealized_pnl():
    from core.entities.position import Position
    pos = Position(
        symbol="INFY",
        direction="SHORT",
        entry_price=1580.0,
        current_price=1560.0,
        quantity=30,
        stop_loss=1600.0,
        target_1=1540.0,
        strategy="VWAP",
        entry_time=datetime(2026, 1, 15, 9, 45),
        entry_order_id="789012",
    )
    assert pos.unrealized_pnl == pytest.approx(30 * 20.0)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/core/entities/test_entities.py -v
```

Expected: `ModuleNotFoundError: No module named 'core.entities.signal'`

- [ ] **Step 3: Implement core/entities/signal.py**

```python
"""Signal entity — immutable trading signal produced by a strategy."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Signal:
    strategy: str
    symbol: str
    direction: str        # "LONG" or "SHORT"
    entry_price: float
    stop_loss: float
    target_1: float
    timestamp: datetime
    confidence: float = 1.0
    target_2: Optional[float] = None

    def __post_init__(self) -> None:
        if self.direction not in ("LONG", "SHORT"):
            raise ValueError(
                f"direction must be 'LONG' or 'SHORT', got {self.direction!r}"
            )
        if self.entry_price <= 0:
            raise ValueError(f"entry_price must be positive, got {self.entry_price}")
        if self.stop_loss <= 0:
            raise ValueError(f"stop_loss must be positive, got {self.stop_loss}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be between 0 and 1, got {self.confidence}"
            )
```

- [ ] **Step 4: Implement core/entities/order.py**

```python
"""Order entity — immutable representation of a broker order."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    OPEN = "OPEN"


@dataclass(frozen=True)
class Order:
    order_id: str
    symbol: str
    token: str                      # Angel One symbol token
    transaction_type: TransactionType
    order_type: OrderType
    quantity: int
    price: Optional[float]
    trigger_price: Optional[float]
    status: OrderStatus
    timestamp: datetime
    fill_price: Optional[float] = None
```

- [ ] **Step 5: Implement core/entities/trade.py**

```python
"""Trade entity — immutable record of a completed or open trade."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Trade:
    trade_id: str
    symbol: str
    strategy: str
    direction: str              # "LONG" or "SHORT"
    entry_price: float
    quantity: int
    stop_loss: float
    target_1: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None  # "TARGET_HIT" | "SL_HIT" | "SQUARE_OFF" | "MANUAL"
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
```

- [ ] **Step 6: Implement core/entities/position.py**

```python
"""Position entity — open position with computed unrealized P&L."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Position:
    symbol: str
    direction: str          # "LONG" or "SHORT"
    entry_price: float
    current_price: float
    quantity: int
    stop_loss: float
    target_1: float
    strategy: str
    entry_time: datetime
    entry_order_id: str
    sl_order_id: Optional[str] = None
    target_order_id: Optional[str] = None

    @property
    def unrealized_pnl(self) -> float:
        if self.direction == "LONG":
            return (self.current_price - self.entry_price) * self.quantity
        return (self.entry_price - self.current_price) * self.quantity

    @property
    def unrealized_pnl_percent(self) -> float:
        cost_basis = self.entry_price * self.quantity
        return (self.unrealized_pnl / cost_basis) * 100
```

- [ ] **Step 7: Implement core/interfaces/i_broker.py**

```python
"""IBroker protocols — IOrderBroker + IDataBroker.
Adapters must implement these. Business logic depends only on these protocols.
"""
from datetime import datetime
from typing import Optional, Protocol

import pandas as pd

from core.entities.order import Order


class IOrderBroker(Protocol):
    """Protocol for placing and managing orders."""

    async def place_order(
        self,
        symbol: str,
        token: str,
        qty: int,
        order_type: str,
        transaction_type: str,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
    ) -> str:
        """Place an order. Returns order_id."""
        ...

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order. Returns True if successful."""
        ...

    async def get_order_status(self, order_id: str) -> dict:
        """Get current status of an order."""
        ...

    async def get_orders(self) -> list[Order]:
        """Get all orders for today."""
        ...


class IDataBroker(Protocol):
    """Protocol for fetching market data."""

    async def get_historical(
        self,
        symbol: str,
        token: str,
        interval: str,
        from_dt: datetime,
        to_dt: datetime,
    ) -> pd.DataFrame:
        """Fetch OHLCV candles. Returns DataFrame with columns:
        open, high, low, close, volume. Index: datetime."""
        ...

    async def get_ltp(
        self, symbol_token_pairs: list[tuple[str, str, str]]
    ) -> dict[str, float]:
        """Get last traded price.
        symbol_token_pairs: [(exchange, tradingsymbol, symboltoken), ...]
        Returns: {tradingsymbol: ltp}
        """
        ...

    async def get_funds(self) -> dict:
        """Get account funds and margin details."""
        ...

    async def get_positions(self) -> list:
        """Get current open positions from broker."""
        ...
```

- [ ] **Step 8: Implement core/interfaces/i_data_feed.py**

```python
"""IDataFeed protocol — real-time tick subscription interface."""
from typing import Callable, Protocol


class IDataFeed(Protocol):
    """Protocol for real-time market data feed."""

    def set_tick_callback(self, callback: Callable[[dict], None]) -> None:
        """Register callback invoked on every incoming tick."""
        ...

    async def connect(self) -> None:
        """Establish WebSocket connection."""
        ...

    def subscribe(self, tokens: list[dict]) -> None:
        """Subscribe to tick data.
        tokens: [{"exchangeType": 1, "tokens": ["2885", "1594"]}]
        """
        ...

    async def disconnect(self) -> None:
        """Close WebSocket connection gracefully."""
        ...
```

- [ ] **Step 9: Run tests — must pass**

```bash
pytest tests/core/entities/test_entities.py -v
```

Expected:
```
PASSED test_signal_creates_with_valid_data
PASSED test_signal_is_frozen
PASSED test_signal_rejects_invalid_direction
PASSED test_signal_rejects_negative_entry_price
PASSED test_signal_rejects_confidence_out_of_range
PASSED test_order_creates_with_valid_data
PASSED test_order_is_frozen
PASSED test_trade_creates_open
PASSED test_trade_is_frozen
PASSED test_position_long_unrealized_pnl
PASSED test_position_short_unrealized_pnl
11 passed
```

- [ ] **Step 10: Commit**

```bash
git add core/entities/ core/interfaces/ tests/core/
git commit -m "feat(stage-1): base entities + interfaces — Signal, Trade, Order, Position, IBroker, IDataFeed"
```

- [ ] **Step 11: Update CLAUDE.md — mark Session 3 DONE**

---

## Task 4: Broker Auth

**Files:**
- Create: `adapters/broker/angel_broker.py` (auth section)
- Create: `tests/adapters/broker/test_angel_broker.py`

- [ ] **Step 1: Write failing tests**

Create `tests/adapters/broker/test_angel_broker.py`:

```python
"""Tests for AngelBroker — auth methods only (Task 4).
SmartConnect is mocked — no real API calls made.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call


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
async def test_refresh_not_needed_when_token_fresh(broker_config, mock_smart_session):
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
async def test_refresh_triggers_when_token_near_expiry(broker_config, mock_smart_session):
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
async def test_refresh_fallback_to_relogin_on_failure(broker_config, mock_smart_session):
    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.return_value = mock_smart_session
        mock_api.generateToken.return_value = {"status": False, "message": "Token expired"}

        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        await broker.login()
        broker._token_expiry = datetime.now() + timedelta(minutes=3)

        result = await broker.ensure_authenticated()

        assert result is True
        # generateSession called twice: initial login + fallback re-login
        assert mock_api.generateSession.call_count == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/adapters/broker/test_angel_broker.py -v
```

Expected: `ModuleNotFoundError: No module named 'adapters.broker.angel_broker'`

- [ ] **Step 3: Implement adapters/broker/angel_broker.py (auth only)**

```python
"""AngelBroker — Angel One SmartAPI adapter.
Implements IOrderBroker + IDataBroker protocols.
Uses asyncio.to_thread for all blocking SDK calls.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import pyotp
from SmartApi import SmartConnect

from infrastructure.config.settings import BrokerConfig

logger = logging.getLogger(__name__)

_TOKEN_LIFETIME_HOURS = 23
_REFRESH_BEFORE_MINUTES = 5


class AngelBroker:
    """Wraps Angel One SmartAPI with async interface and auto token refresh."""

    def __init__(self, config: BrokerConfig) -> None:
        self._config = config
        self._smart = SmartConnect(api_key=config.api_key)
        self._jwt_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._feed_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    @property
    def feed_token(self) -> Optional[str]:
        return self._feed_token

    @property
    def jwt_token(self) -> Optional[str]:
        return self._jwt_token

    async def login(self) -> bool:
        """Authenticate with Angel One using TOTP. Returns True on success."""
        totp = pyotp.TOTP(self._config.totp_secret).now()
        try:
            data = await asyncio.to_thread(
                self._smart.generateSession,
                self._config.client_id,
                self._config.password,
                totp,
            )
            if not data.get("status"):
                logger.error("Login failed: %s", data.get("message"))
                return False
            session = data["data"]
            self._jwt_token = session["jwtToken"]
            self._refresh_token = session["refreshToken"]
            self._feed_token = session["feedToken"]
            self._token_expiry = datetime.now() + timedelta(
                hours=_TOKEN_LIFETIME_HOURS
            )
            logger.info("Authenticated: client=%s", self._config.client_id)
            return True
        except Exception as exc:
            logger.error("Login exception: %s", exc)
            return False

    async def ensure_authenticated(self) -> bool:
        """Refresh token if within 5-minute expiry window. Re-login if refresh fails."""
        if self._token_expiry is None:
            return False
        refresh_threshold = datetime.now() + timedelta(
            minutes=_REFRESH_BEFORE_MINUTES
        )
        if datetime.now() < refresh_threshold < self._token_expiry:
            return True
        return await self._refresh_token_or_relogin()

    async def _refresh_token_or_relogin(self) -> bool:
        try:
            data = await asyncio.to_thread(
                self._smart.generateToken, self._refresh_token
            )
            if not data.get("status"):
                logger.warning("Token refresh failed — re-logging in")
                return await self.login()
            self._jwt_token = data["data"]["jwtToken"]
            self._token_expiry = datetime.now() + timedelta(
                hours=_TOKEN_LIFETIME_HOURS
            )
            logger.info("Token refreshed successfully")
            return True
        except Exception as exc:
            logger.error("Token refresh exception: %s — re-logging in", exc)
            return await self.login()
```

- [ ] **Step 4: Run tests — must pass**

```bash
pytest tests/adapters/broker/test_angel_broker.py -v
```

Expected:
```
PASSED test_login_success_stores_tokens
PASSED test_login_failure_returns_false
PASSED test_login_exception_returns_false
PASSED test_refresh_not_needed_when_token_fresh
PASSED test_refresh_triggers_when_token_near_expiry
PASSED test_refresh_fallback_to_relogin_on_failure
6 passed
```

- [ ] **Step 5: Commit**

```bash
git add adapters/broker/angel_broker.py tests/adapters/broker/test_angel_broker.py
git commit -m "feat(stage-1): broker auth — TOTP login, JWT storage, auto-refresh with relogin fallback"
```

- [ ] **Step 6: Update CLAUDE.md — mark Session 4 DONE**

---

## Task 5: Broker Data Methods

**Files:**
- Modify: `adapters/broker/angel_broker.py` (add data methods)
- Modify: `tests/adapters/broker/test_angel_broker.py` (add data tests)

- [ ] **Step 1: Write failing tests — append to test_angel_broker.py**

```python
# ─── Data method tests — append to test_angel_broker.py ───

@pytest.fixture
def authenticated_broker(broker_config, mock_smart_session):
    """Returns a broker that has already logged in."""
    with patch("adapters.broker.angel_broker.SmartConnect") as mock_cls:
        mock_api = MagicMock()
        mock_cls.return_value = mock_api
        mock_api.generateSession.return_value = mock_smart_session

        import asyncio
        from adapters.broker.angel_broker import AngelBroker
        broker = AngelBroker(broker_config)
        asyncio.get_event_loop().run_until_complete(broker.login())
        yield broker, mock_api


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


@pytest.mark.asyncio
async def test_get_historical_returns_empty_df_when_no_data(broker_config, mock_smart_session):
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/adapters/broker/test_angel_broker.py::test_get_historical_returns_dataframe -v
```

Expected: `AttributeError: 'AngelBroker' object has no attribute 'get_historical'`

- [ ] **Step 3: Add data methods to adapters/broker/angel_broker.py**

Append these methods to the `AngelBroker` class (after `_refresh_token_or_relogin`):

```python
    # ─── Interval mapping ───
    _INTERVAL_MAP: dict[str, str] = {
        "1m": "ONE_MINUTE",
        "3m": "THREE_MINUTE",
        "5m": "FIVE_MINUTE",
        "10m": "TEN_MINUTE",
        "15m": "FIFTEEN_MINUTE",
        "30m": "THIRTY_MINUTE",
        "1h": "ONE_HOUR",
        "1d": "ONE_DAY",
    }

    async def get_historical(
        self,
        symbol: str,
        token: str,
        interval: str,
        from_dt: datetime,
        to_dt: datetime,
    ) -> "pd.DataFrame":
        """Fetch OHLCV candles from Angel One.
        Returns DataFrame indexed by datetime with columns: open, high, low, close, volume.
        """
        import pandas as pd

        await self.ensure_authenticated()
        angel_interval = self._INTERVAL_MAP.get(interval)
        if not angel_interval:
            raise ValueError(
                f"Unsupported interval: {interval!r}. "
                f"Valid: {list(self._INTERVAL_MAP.keys())}"
            )
        params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": angel_interval,
            "fromdate": from_dt.strftime("%Y-%m-%d %H:%M"),
            "todate": to_dt.strftime("%Y-%m-%d %H:%M"),
        }
        response = await asyncio.to_thread(self._smart.getCandleData, params)
        rows = response.get("data") or []
        if not rows:
            return pd.DataFrame(
                columns=["open", "high", "low", "close", "volume"]
            )
        df = pd.DataFrame(
            rows, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_localize(None)
        return df.set_index("timestamp")

    async def get_ltp(
        self, symbol_token_pairs: list[tuple[str, str, str]]
    ) -> dict[str, float]:
        """Get last traded price for multiple symbols.
        symbol_token_pairs: [(exchange, tradingsymbol, symboltoken), ...]
        Returns: {tradingsymbol: ltp}
        """
        await self.ensure_authenticated()
        result: dict[str, float] = {}
        for exchange, tradingsymbol, symboltoken in symbol_token_pairs:
            try:
                data = await asyncio.to_thread(
                    self._smart.ltpData, exchange, tradingsymbol, symboltoken
                )
                if data.get("status") and data.get("data"):
                    result[tradingsymbol] = float(data["data"]["ltp"])
            except Exception as exc:
                logger.warning("LTP fetch failed for %s: %s", tradingsymbol, exc)
        return result

    async def get_funds(self) -> dict:
        """Get account margin and available cash."""
        await self.ensure_authenticated()
        data = await asyncio.to_thread(self._smart.rmsLimit)
        return data.get("data") or {}

    async def get_positions(self) -> list:
        """Get all open positions from broker."""
        await self.ensure_authenticated()
        data = await asyncio.to_thread(self._smart.position)
        return data.get("data") or []

    async def get_orders(self) -> list:
        """Get today's order book."""
        await self.ensure_authenticated()
        data = await asyncio.to_thread(self._smart.orderBook)
        return data.get("data") or []
```

Add `import pandas as pd` at the top of the file (with other imports).

- [ ] **Step 4: Run all broker tests — must pass**

```bash
pytest tests/adapters/broker/test_angel_broker.py -v
```

Expected: All tests pass (6 from Task 4 + 5 new = 11 passed)

- [ ] **Step 5: Commit**

```bash
git add adapters/broker/angel_broker.py tests/adapters/broker/test_angel_broker.py
git commit -m "feat(stage-1): broker data methods — get_historical, get_ltp, get_funds, get_positions, get_orders"
```

- [ ] **Step 6: Update CLAUDE.md — mark Session 5 DONE**

---

## Task 6: WebSocket Data Feed

**Files:**
- Create: `adapters/data/data_feed.py`
- Create: `tests/adapters/data/test_data_feed.py`

- [ ] **Step 1: Write failing tests**

Create `tests/adapters/data/test_data_feed.py`:

```python
"""Tests for DataFeed — WebSocket tick subscription with reconnect."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


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
    # No callback registered — must not raise
    feed._on_data(MagicMock(), {"token": "2885"})


def test_subscribe_stores_tokens_and_calls_ws(feed_params):
    with patch("adapters.data.data_feed.SmartWebSocketV2") as mock_ws_cls:
        mock_ws = MagicMock()
        mock_ws_cls.return_value = mock_ws

        from adapters.data.data_feed import DataFeed
        feed = DataFeed(**feed_params)
        feed._sws = mock_ws  # simulate connected state

        tokens = [{"exchangeType": 1, "tokens": ["2885", "1594"]}]
        feed.subscribe(tokens)

        assert feed._subscribed_tokens == tokens
        mock_ws.subscribe.assert_called_once()


def test_on_open_resubscribes_existing_tokens(feed_params):
    with patch("adapters.data.data_feed.SmartWebSocketV2") as mock_ws_cls:
        mock_ws = MagicMock()
        mock_ws_cls.return_value = mock_ws

        from adapters.data.data_feed import DataFeed
        feed = DataFeed(**feed_params)
        feed._sws = mock_ws
        feed._subscribed_tokens = [{"exchangeType": 1, "tokens": ["2885"]}]

        feed._on_open(mock_ws)

        mock_ws.subscribe.assert_called_once()


def test_on_open_with_no_subscriptions_does_not_subscribe(feed_params):
    with patch("adapters.data.data_feed.SmartWebSocketV2"):
        from adapters.data.data_feed import DataFeed
        feed = DataFeed(**feed_params)
        feed._sws = MagicMock()
        # No subscribed tokens
        feed._on_open(MagicMock())
        feed._sws.subscribe.assert_not_called()


@pytest.mark.asyncio
async def test_disconnect_closes_connection(feed_params):
    with patch("adapters.data.data_feed.SmartWebSocketV2") as mock_ws_cls:
        mock_ws = MagicMock()
        mock_ws_cls.return_value = mock_ws

        from adapters.data.data_feed import DataFeed
        feed = DataFeed(**feed_params)
        feed._sws = mock_ws
        await feed.disconnect()

        mock_ws.close_connection.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/adapters/data/test_data_feed.py -v
```

Expected: `ModuleNotFoundError: No module named 'adapters.data.data_feed'`

- [ ] **Step 3: Implement adapters/data/data_feed.py**

```python
"""DataFeed — real-time WebSocket tick subscription via Angel One SmartWebSocketV2.
Implements IDataFeed protocol.
"""
import asyncio
import logging
from typing import Callable, Optional

from SmartApi.SmartWebSocketV2 import SmartWebSocketV2

logger = logging.getLogger(__name__)

_SUBSCRIPTION_MODE = 1          # LTP mode (1=LTP, 2=QUOTE, 3=SNAP_QUOTE)
_SESSION_CORRELATION = "algo-feed"


class DataFeed:
    """WebSocket tick feed with auto-resubscription on reconnect."""

    def __init__(
        self,
        auth_token: str,
        api_key: str,
        client_id: str,
        feed_token: str,
    ) -> None:
        self._auth_token = auth_token
        self._api_key = api_key
        self._client_id = client_id
        self._feed_token = feed_token
        self._sws: Optional[SmartWebSocketV2] = None
        self._tick_callback: Optional[Callable[[dict], None]] = None
        self._subscribed_tokens: list[dict] = []

    def set_tick_callback(self, callback: Callable[[dict], None]) -> None:
        """Register callback invoked on every incoming tick."""
        self._tick_callback = callback

    async def connect(self) -> None:
        """Initialize WebSocket and start connection in background thread."""
        self._sws = SmartWebSocketV2(
            self._auth_token,
            self._api_key,
            self._client_id,
            self._feed_token,
            max_retry_attempt=5,
        )
        self._sws.on_open = self._on_open
        self._sws.on_data = self._on_data
        self._sws.on_error = self._on_error
        self._sws.on_close = self._on_close
        await asyncio.to_thread(self._sws.connect)

    def subscribe(self, tokens: list[dict]) -> None:
        """Subscribe to tick stream.
        tokens: [{"exchangeType": 1, "tokens": ["2885", "1594"]}]
        """
        self._subscribed_tokens = tokens
        if self._sws:
            self._sws.subscribe(_SESSION_CORRELATION, _SUBSCRIPTION_MODE, tokens)

    async def disconnect(self) -> None:
        """Close WebSocket connection gracefully."""
        if self._sws:
            await asyncio.to_thread(self._sws.close_connection)
            self._sws = None
            logger.info("DataFeed disconnected")

    # ─── Internal callbacks ───

    def _on_open(self, wsapp) -> None:
        logger.info("WebSocket connected")
        if self._subscribed_tokens:
            self._sws.subscribe(
                _SESSION_CORRELATION, _SUBSCRIPTION_MODE, self._subscribed_tokens
            )

    def _on_data(self, wsapp, message: dict) -> None:
        if self._tick_callback:
            self._tick_callback(message)

    def _on_error(self, wsapp, error) -> None:
        logger.error("WebSocket error: %s", error)

    def _on_close(self, wsapp, close_status_code, close_msg) -> None:
        logger.warning(
            "WebSocket closed: status=%s msg=%s", close_status_code, close_msg
        )
```

- [ ] **Step 4: Run tests — must pass**

```bash
pytest tests/adapters/data/test_data_feed.py -v
```

Expected: All 8 tests pass.

- [ ] **Step 5: Commit**

```bash
git add adapters/data/data_feed.py tests/adapters/data/test_data_feed.py
git commit -m "feat(stage-1): websocket data feed — tick subscription, reconnect callbacks, auto-resubscribe"
```

- [ ] **Step 6: Update CLAUDE.md — mark Session 6 DONE**

---

## Task 7: Data Cacher

**Files:**
- Create: `adapters/data/data_cacher.py`
- Create: `tests/adapters/data/test_data_cacher.py`

- [ ] **Step 1: Write failing tests**

Create `tests/adapters/data/test_data_cacher.py`:

```python
"""Tests for DataCacher — Parquet read/write with deduplication."""
import pytest
import pandas as pd
from datetime import datetime
from pathlib import Path


@pytest.fixture
def tmp_cacher(tmp_path):
    from adapters.data.data_cacher import DataCacher
    return DataCacher(cache_dir=tmp_path)


@pytest.fixture
def sample_df():
    idx = pd.to_datetime([
        "2026-01-15 09:15:00",
        "2026-01-15 09:20:00",
        "2026-01-15 09:25:00",
    ])
    return pd.DataFrame(
        {
            "open":   [2440.0, 2455.0, 2460.0],
            "high":   [2460.0, 2470.0, 2475.0],
            "low":    [2435.0, 2450.0, 2455.0],
            "close":  [2455.0, 2465.0, 2470.0],
            "volume": [100000, 80000, 90000],
        },
        index=idx,
    )


def test_save_and_load_roundtrip(tmp_cacher, sample_df):
    tmp_cacher.save("RELIANCE", "5m", sample_df)
    result = tmp_cacher.load(
        "RELIANCE", "5m",
        from_dt=datetime(2026, 1, 15, 9, 0),
        to_dt=datetime(2026, 1, 15, 15, 30),
    )
    assert result is not None
    assert len(result) == 3
    assert list(result.columns) == ["open", "high", "low", "close", "volume"]


def test_load_returns_none_when_no_file(tmp_cacher):
    result = tmp_cacher.load(
        "NONEXISTENT", "5m",
        from_dt=datetime(2026, 1, 15, 9, 0),
        to_dt=datetime(2026, 1, 15, 15, 30),
    )
    assert result is None


def test_load_filters_by_date_range(tmp_cacher, sample_df):
    tmp_cacher.save("RELIANCE", "5m", sample_df)
    result = tmp_cacher.load(
        "RELIANCE", "5m",
        from_dt=datetime(2026, 1, 15, 9, 20),
        to_dt=datetime(2026, 1, 15, 9, 25),
    )
    assert result is not None
    assert len(result) == 2  # 09:20 and 09:25 only


def test_save_deduplicates_overlapping_data(tmp_cacher, sample_df):
    tmp_cacher.save("RELIANCE", "5m", sample_df)

    # Save again with one overlapping row + one new row
    new_idx = pd.to_datetime(["2026-01-15 09:25:00", "2026-01-15 09:30:00"])
    new_df = pd.DataFrame(
        {
            "open":   [2461.0, 2470.0],
            "high":   [2476.0, 2485.0],
            "low":    [2456.0, 2465.0],
            "close":  [2471.0, 2480.0],
            "volume": [91000, 70000],
        },
        index=new_idx,
    )
    tmp_cacher.save("RELIANCE", "5m", new_df)

    result = tmp_cacher.load(
        "RELIANCE", "5m",
        from_dt=datetime(2026, 1, 15, 9, 0),
        to_dt=datetime(2026, 1, 15, 15, 30),
    )
    assert result is not None
    assert len(result) == 4  # 09:15, 09:20, 09:25 (deduped, new wins), 09:30


def test_save_deduplication_keeps_latest_value(tmp_cacher, sample_df):
    tmp_cacher.save("RELIANCE", "5m", sample_df)

    # Re-save 09:25 candle with updated close price
    updated_idx = pd.to_datetime(["2026-01-15 09:25:00"])
    updated_df = pd.DataFrame(
        {"open": [2460.0], "high": [2480.0], "low": [2455.0],
         "close": [9999.0], "volume": [95000]},
        index=updated_idx,
    )
    tmp_cacher.save("RELIANCE", "5m", updated_df)

    result = tmp_cacher.load(
        "RELIANCE", "5m",
        from_dt=datetime(2026, 1, 15, 9, 25),
        to_dt=datetime(2026, 1, 15, 9, 25),
    )
    assert result is not None
    assert result.iloc[0]["close"] == 9999.0  # latest value wins


def test_has_data_returns_true_when_cached(tmp_cacher, sample_df):
    tmp_cacher.save("RELIANCE", "5m", sample_df)
    assert tmp_cacher.has_data(
        "RELIANCE", "5m",
        from_dt=datetime(2026, 1, 15, 9, 15),
        to_dt=datetime(2026, 1, 15, 9, 25),
    ) is True


def test_has_data_returns_false_when_not_cached(tmp_cacher):
    assert tmp_cacher.has_data(
        "RELIANCE", "5m",
        from_dt=datetime(2026, 1, 15, 9, 15),
        to_dt=datetime(2026, 1, 15, 9, 25),
    ) is False


def test_cache_filename_uses_symbol_and_interval(tmp_cacher, tmp_path, sample_df):
    tmp_cacher.save("TATAMOTORS", "15m", sample_df)
    expected_path = tmp_path / "TATAMOTORS_15m.parquet"
    assert expected_path.exists()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/adapters/data/test_data_cacher.py -v
```

Expected: `ModuleNotFoundError: No module named 'adapters.data.data_cacher'`

- [ ] **Step 3: Implement adapters/data/data_cacher.py**

```python
"""DataCacher — Parquet-based local cache for OHLCV historical data.
Cache-first: saves to disk, deduplicates on merge, latest value wins on conflict.
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


class DataCacher:
    """Reads and writes OHLCV DataFrames to Parquet files.
    One file per symbol+interval combination.
    """

    def __init__(self, cache_dir: Path = Path("data/historical")) -> None:
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def save(self, symbol: str, interval: str, df: pd.DataFrame) -> None:
        """Merge df into existing cache. Latest values win on duplicate timestamps."""
        path = self._cache_path(symbol, interval)
        if path.exists():
            existing = pd.read_parquet(path)
            df = pd.concat([existing, df])
            df = df[~df.index.duplicated(keep="last")]
            df = df.sort_index()
        df.to_parquet(path)
        logger.debug("Cached %d rows → %s", len(df), path.name)

    def load(
        self,
        symbol: str,
        interval: str,
        from_dt: datetime,
        to_dt: datetime,
    ) -> Optional[pd.DataFrame]:
        """Load cached rows within [from_dt, to_dt]. Returns None if no file or empty."""
        path = self._cache_path(symbol, interval)
        if not path.exists():
            return None
        df = pd.read_parquet(path)
        mask = (df.index >= from_dt) & (df.index <= to_dt)
        result = df.loc[mask]
        return result if not result.empty else None

    def has_data(
        self,
        symbol: str,
        interval: str,
        from_dt: datetime,
        to_dt: datetime,
    ) -> bool:
        """True if cache has at least one row in the given range."""
        return self.load(symbol, interval, from_dt, to_dt) is not None

    def _cache_path(self, symbol: str, interval: str) -> Path:
        return self._cache_dir / f"{symbol}_{interval}.parquet"
```

- [ ] **Step 4: Run all tests — full suite must pass**

```bash
pytest -v
```

Expected: All tests from Tasks 2-7 pass (no failures).

```
tests/infrastructure/config/test_settings.py          5 passed
tests/core/entities/test_entities.py                 11 passed
tests/adapters/broker/test_angel_broker.py           11 passed
tests/adapters/data/test_data_feed.py                 8 passed
tests/adapters/data/test_data_cacher.py               8 passed
43 passed
```

- [ ] **Step 5: Commit**

```bash
git add adapters/data/data_cacher.py tests/adapters/data/test_data_cacher.py
git commit -m "feat(stage-1): data cacher — Parquet read/write, deduplication, cache-first loading"
```

- [ ] **Step 6: Final full test run with coverage check**

```bash
pytest -v --tb=short
```

All 43 tests must pass. Zero failures.

- [ ] **Step 7: Update CLAUDE.md — mark Session 7 DONE, Stage 1 COMPLETE**

Change Stage 1 status from `PENDING` → `DONE` in the Stage Status table.
Update Sessions Done from `0` → `7`.

Add to Session Log:
```
### 2026-04-01
- Stage 1: ALL 7 sessions complete — foundation layer done
- 43 tests passing, zero failures
- Next stage: stage-2/backtest — run_backtest.py, backtesting engine
```

- [ ] **Step 8: Merge stage branch**

```bash
git checkout main
git merge stage-1/foundation --no-ff -m "merge(stage-1): foundation complete — broker, data feed, cacher, entities, config"
git checkout -b stage-2/backtest
```

---

## Self-Review Checklist

**Spec coverage:**
- Config loader ✓ (Task 2)
- Base entities: Signal, Trade, Order, Position ✓ (Task 3)
- IBroker, IDataFeed interfaces ✓ (Task 3)
- Broker auth: TOTP login, token refresh, relogin fallback ✓ (Task 4)
- Broker data: get_historical, get_ltp, get_funds, get_positions, get_orders ✓ (Task 5)
- WebSocket feed: subscribe, reconnect, callback dispatch ✓ (Task 6)
- Data cacher: Parquet save/load, deduplication, date range filter ✓ (Task 7)
- Pre-commit hooks with secret detection ✓ (Task 1)
- Security: .gitignore for .env, BrokerConfig from env vars only ✓ (Task 1 + 2)

**Type consistency:**
- `AngelBroker._token_expiry` → `Optional[datetime]` used consistently in Tasks 4 and 5 ✓
- `DataCacher.load()` → returns `Optional[pd.DataFrame]`, consistent with `has_data()` usage ✓
- `DataFeed._subscribed_tokens` → `list[dict]`, consistent between `subscribe()` and `_on_open()` ✓
- `BrokerConfig` field names (`client_id`, `password`, `totp_secret`, `api_key`) consistent across Tasks 2, 4, 5 ✓
- `ensure_authenticated()` used in Task 5 data methods, defined in Task 4 ✓

**No placeholders:** All code blocks are complete and runnable. All test assertions are specific. ✓
