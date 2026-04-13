"""TradingBot orchestrator tests — uses MagicMock for all external deps."""
import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd

from core.use_cases.trading_bot import TradingBot
from infrastructure.dashboard.state_bridge import StateBridge
from core.entities.signal import Signal


def _make_signal(symbol="RELIANCE-EQ"):
    return Signal(
        symbol=symbol, direction="LONG", strategy="ORB",
        entry_price=2850.0, stop_loss=2820.0, target_1=2910.0,
        timestamp=datetime.now(),
    )


def _make_df():
    import numpy as np
    n = 30
    return pd.DataFrame({
        "open":   np.linspace(100, 110, n),
        "high":   np.linspace(101, 111, n),
        "low":    np.linspace(99, 109, n),
        "close":  np.linspace(100, 110, n),
        "volume": [500_000] * n,
    })


@pytest.fixture
def bot(tmp_path):
    bridge = StateBridge()
    broker = MagicMock()
    broker.get_historical = AsyncMock(return_value=_make_df())
    broker.get_ltp = AsyncMock(return_value={"RELIANCE-EQ": 2870.0})

    strategy_engine = MagicMock()
    strategy_engine.run = MagicMock(return_value=[_make_signal()])
    strategy_engine._enabled = {}

    risk_manager = MagicMock()
    risk_manager.validate = MagicMock(return_value=(True, ""))

    position_sizer = MagicMock()
    position_sizer.calculate = MagicMock(return_value=5)

    paper_trader = MagicMock()
    paper_trader.fill = MagicMock(return_value=1)
    paper_trader.day_pnl = MagicMock(return_value=500.0)
    paper_trader.open_trades = MagicMock(return_value=[])
    paper_trader.capital = 100_000.0

    telegram = MagicMock()
    telegram.notify_entry = AsyncMock()
    telegram.notify_exit = AsyncMock()

    health = MagicMock()
    health.record_heartbeat = MagicMock()
    health.system_status = MagicMock(return_value={})

    return TradingBot(
        mode="paper",
        broker=broker,
        strategy_engine=strategy_engine,
        risk_manager=risk_manager,
        position_sizer=position_sizer,
        paper_trader=paper_trader,
        telegram=telegram,
        health_monitor=health,
        state_bridge=bridge,
        symbol_tokens={"RELIANCE-EQ": "2885"},
    )


@pytest.mark.asyncio
async def test_strategy_cycle_fills_signal(bot):
    await bot._strategy_cycle()
    bot.paper_trader.fill.assert_called_once()


@pytest.mark.asyncio
async def test_strategy_cycle_skips_when_risk_rejects(bot):
    bot.risk_manager.validate = MagicMock(return_value=(False, "kill switch active"))
    await bot._strategy_cycle()
    bot.paper_trader.fill.assert_not_called()


@pytest.mark.asyncio
async def test_strategy_cycle_skips_zero_qty(bot):
    bot.position_sizer.calculate = MagicMock(return_value=0)
    await bot._strategy_cycle()
    bot.paper_trader.fill.assert_not_called()


@pytest.mark.asyncio
async def test_strategy_cycle_updates_state_bridge(bot):
    await bot._strategy_cycle()
    signals = bot.state_bridge.get("signals")
    assert isinstance(signals, list)
    assert len(signals) == 1
    assert signals[0]["symbol"] == "RELIANCE-EQ"
    assert "entry" in signals[0]
    assert "sl" in signals[0]
    assert "target" in signals[0]


@pytest.mark.asyncio
async def test_strategy_cycle_sends_telegram_on_fill(bot):
    await bot._strategy_cycle()
    bot.telegram.notify_entry.assert_called_once()


@pytest.mark.asyncio
async def test_strategy_cycle_handles_broker_error_gracefully(bot):
    bot.broker.get_historical = AsyncMock(side_effect=RuntimeError("API down"))
    await bot._strategy_cycle()   # must not raise
    bot.paper_trader.fill.assert_not_called()


@pytest.mark.asyncio
async def test_update_dashboard_state_populates_positions(bot):
    bot.paper_trader.open_trades = MagicMock(return_value=[{
        "id": 1, "symbol": "RELIANCE-EQ", "direction": "LONG",
        "qty": 5, "entry_price": 2850.0, "stop_loss": 2820.0,
        "target_1": 2910.0, "entry_time": "2026-04-11T10:00:00", "strategy": "ORB",
    }])
    bot._update_dashboard_state(ltp_map={"RELIANCE-EQ": 2870.0})
    pos = bot.state_bridge.get("positions")
    assert len(pos) == 1
    assert pos[0]["symbol"] == "RELIANCE-EQ"
    assert pos[0]["pnl"] == pytest.approx(100.0)  # (2870-2850)*5


def test_set_kill_switch_updates_bridge(bot):
    bot.set_kill_switch(True)
    assert bot.state_bridge.get("kill_switch") is True


def test_toggle_strategy_updates_engine(bot):
    bot.toggle_strategy("orb", False)
    assert bot.strategy_engine._enabled.get("orb") is False


@pytest.mark.asyncio
async def test_open_position_uses_real_ltp_not_candle_close(bot):
    """Positions must use broker.get_ltp(), not the stale last-candle close."""
    bot.paper_trader.open_trades = MagicMock(return_value=[{
        "id": 1, "symbol": "RELIANCE-EQ", "direction": "LONG",
        "qty": 5, "entry_price": 2850.0, "stop_loss": 2820.0,
        "target_1": 2910.0, "entry_time": "2026-04-11T10:00:00", "strategy": "ORB",
    }])
    bot.broker.get_ltp = AsyncMock(return_value={"RELIANCE-EQ": 2870.0})
    await bot._strategy_cycle()
    pos = bot.state_bridge.get("positions")
    assert pos[0]["current_price"] == pytest.approx(2870.0)
    assert pos[0]["pnl"] == pytest.approx(100.0)   # (2870-2850)*5
    bot.broker.get_ltp.assert_called_once()


@pytest.mark.asyncio
async def test_run_loop_stops_on_stop(bot):
    """run_loop exits cleanly when stop() is called."""
    task = asyncio.create_task(bot.run_loop(interval_seconds=0))
    await asyncio.sleep(0.05)
    bot.stop()
    await asyncio.wait_for(task, timeout=2.0)  # must not hang
