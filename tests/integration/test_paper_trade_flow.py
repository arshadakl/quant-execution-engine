"""Integration tests — paper trade end-to-end flow.

Uses real StateBridge, PaperTrader, RiskManager, PositionSizer,
StrategyEngine, and HealthMonitor. Only the broker and telegram
are mocked (external I/O).
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, time
from unittest.mock import AsyncMock, MagicMock

from core.entities.signal import Signal
from core.use_cases.trading_bot import TradingBot
from core.use_cases.risk_manager import RiskManager, RiskState
from core.use_cases.position_sizer import PositionSizer
from core.use_cases.strategy_engine import StrategyEngine
from adapters.paper_trader import PaperTrader
from infrastructure.dashboard.state_bridge import StateBridge
from infrastructure.health_monitor import HealthMonitor


_TRADE_TIME = datetime(2026, 4, 11, 10, 30, 0)  # within 9:15–15:15


def _make_signal(symbol: str = "RELIANCE-EQ") -> Signal:
    return Signal(
        symbol=symbol, direction="LONG", strategy="orb",
        entry_price=2850.0, stop_loss=2820.0, target_1=2910.0,
        timestamp=_TRADE_TIME,
    )


def _make_df(n: int = 30) -> pd.DataFrame:
    return pd.DataFrame({
        "open":   np.linspace(100, 110, n),
        "high":   np.linspace(101, 111, n),
        "low":    np.linspace(99, 109, n),
        "close":  np.linspace(100, 110, n),
        "volume": [500_000] * n,
    })


def _mock_broker(df: pd.DataFrame | None = None) -> MagicMock:
    broker = MagicMock()
    broker.get_historical = AsyncMock(return_value=df or _make_df())
    return broker


def _mock_telegram() -> MagicMock:
    tg = MagicMock()
    tg.notify_entry = AsyncMock()
    tg.notify_error = AsyncMock()
    return tg


class _StubStrategy:
    """Strategy that always emits one fixed signal."""
    name = "orb"

    def __init__(self, signal: Signal) -> None:
        self._signal = signal

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        return [self._signal]


@pytest.fixture
def components(tmp_path):
    bridge = StateBridge()
    db = str(tmp_path / "paper.db")
    paper = PaperTrader(db_path=db, initial_capital=100_000.0)
    risk = RiskManager(
        max_daily_loss_pct=0.03,
        max_open_positions=5,
        trade_start=time(9, 15),
        trade_end=time(15, 15),
        cooldown_seconds=0,  # no cooldown for tests
    )
    sizer = PositionSizer(risk_pct=0.01, max_qty=500)
    health = HealthMonitor()
    signal = _make_signal()
    strategy = _StubStrategy(signal)
    engine = StrategyEngine(strategies=[strategy], enabled={"orb": True})
    broker = _mock_broker()
    telegram = _mock_telegram()

    bot = TradingBot(
        mode="paper",
        broker=broker,
        strategy_engine=engine,
        risk_manager=risk,
        position_sizer=sizer,
        paper_trader=paper,
        telegram=telegram,
        health_monitor=health,
        state_bridge=bridge,
        symbol_tokens={"RELIANCE-EQ": "2885"},
    )
    return {
        "bot": bot, "bridge": bridge, "paper": paper,
        "risk": risk, "engine": engine,
    }


# ── Test 1: Signal → Fill → StateBridge ──────────────────────────────────────

@pytest.mark.asyncio
async def test_signal_fill_updates_state_bridge(components):
    bot: TradingBot = components["bot"]
    bridge: StateBridge = components["bridge"]
    paper: PaperTrader = components["paper"]

    await bot._strategy_cycle()

    open_trades = paper.open_trades()
    assert len(open_trades) == 1
    assert open_trades[0]["symbol"] == "RELIANCE-EQ"
    assert open_trades[0]["direction"] == "LONG"

    positions = bridge.get("positions")
    assert len(positions) == 1
    assert positions[0]["symbol"] == "RELIANCE-EQ"

    summary = bridge.get("summary")
    assert summary["open_count"] == 1
    assert summary["capital"] == pytest.approx(100_000.0)


# ── Test 2: Kill switch blocks new signals ────────────────────────────────────

@pytest.mark.asyncio
async def test_kill_switch_blocks_fills(components):
    bot: TradingBot = components["bot"]
    paper: PaperTrader = components["paper"]

    bot.set_kill_switch(True)

    await bot._strategy_cycle()

    assert paper.open_trades() == []
    assert components["bridge"].get("kill_switch") is True


# ── Test 3: Strategy toggle prevents signal generation ────────────────────────

@pytest.mark.asyncio
async def test_strategy_toggle_off_blocks_signals(components):
    bot: TradingBot = components["bot"]
    paper: PaperTrader = components["paper"]
    bridge: StateBridge = components["bridge"]

    bot.toggle_strategy("orb", False)

    await bot._strategy_cycle()

    assert paper.open_trades() == []
    signals = bridge.get("signals")
    assert signals == []
    assert bridge.get("strategies").get("orb") is False


# ── Test 4: Full cycle — summary updated after fill ───────────────────────────

@pytest.mark.asyncio
async def test_full_cycle_summary_updated(components):
    bot: TradingBot = components["bot"]
    bridge: StateBridge = components["bridge"]
    paper: PaperTrader = components["paper"]

    await bot._strategy_cycle()

    summary = bridge.get("summary")
    assert summary["open_count"] == 1
    assert summary["day_pnl"] == pytest.approx(0.0)  # no closed trades yet

    # Verify signals captured in bridge
    signals = bridge.get("signals")
    assert len(signals) == 1
    assert signals[0]["strategy"] == "orb"
    assert signals[0]["entry"] == pytest.approx(2850.0)
    assert signals[0]["sl"] == pytest.approx(2820.0)
