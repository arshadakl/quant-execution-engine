"""Tests for Risk Manager / Validator."""
import pytest
from datetime import datetime, time
from core.use_cases.risk_manager import RiskManager, RiskState


# ─── Instantiation ───

def test_instantiates_with_defaults():
    rm = RiskManager()
    assert rm.max_daily_loss_pct == 0.03
    assert rm.max_open_positions == 5
    assert rm.trade_start == time(9, 15)
    assert rm.trade_end == time(15, 15)
    assert rm.cooldown_seconds == 300


def test_instantiates_with_custom_params():
    rm = RiskManager(
        max_daily_loss_pct=0.05,
        max_open_positions=10,
        trade_start=time(9, 30),
        trade_end=time(15, 0),
        cooldown_seconds=60,
    )
    assert rm.max_daily_loss_pct == 0.05
    assert rm.max_open_positions == 10


# ─── RiskState ───

def test_risk_state_defaults():
    state = RiskState()
    assert state.daily_pnl == 0.0
    assert state.open_positions == 0
    assert state.last_trade_time is None
    assert state.kill_switch is False


# ─── Kill switch ───

def test_rejects_when_kill_switch_active():
    rm = RiskManager()
    state = RiskState(kill_switch=True)
    ok, reason = rm.validate(state=state, capital=100_000.0,
                             signal_time=datetime(2026, 1, 2, 10, 0))
    assert ok is False
    assert "kill" in reason.lower()


def test_activates_kill_switch_on_daily_loss_breach():
    rm = RiskManager(max_daily_loss_pct=0.03)
    state = RiskState(daily_pnl=-3100.0)  # > 3% of 100_000
    ok, reason = rm.validate(state=state, capital=100_000.0,
                             signal_time=datetime(2026, 1, 2, 10, 0))
    assert ok is False
    assert "loss" in reason.lower()


def test_passes_when_daily_loss_within_limit():
    rm = RiskManager(max_daily_loss_pct=0.03)
    state = RiskState(daily_pnl=-2900.0)  # < 3% of 100_000
    ok, _ = rm.validate(state=state, capital=100_000.0,
                        signal_time=datetime(2026, 1, 2, 10, 0))
    assert ok is True


# ─── Time gate ───

def test_rejects_before_market_open():
    rm = RiskManager(trade_start=time(9, 15))
    state = RiskState()
    ok, reason = rm.validate(state=state, capital=100_000.0,
                             signal_time=datetime(2026, 1, 2, 9, 10))
    assert ok is False
    assert "time" in reason.lower()


def test_rejects_after_market_close():
    rm = RiskManager(trade_end=time(15, 15))
    state = RiskState()
    ok, reason = rm.validate(state=state, capital=100_000.0,
                             signal_time=datetime(2026, 1, 2, 15, 20))
    assert ok is False
    assert "time" in reason.lower()


def test_passes_within_trading_window():
    rm = RiskManager()
    state = RiskState()
    ok, _ = rm.validate(state=state, capital=100_000.0,
                        signal_time=datetime(2026, 1, 2, 10, 30))
    assert ok is True


def test_passes_exactly_at_trade_start():
    rm = RiskManager(trade_start=time(9, 15))
    state = RiskState()
    ok, _ = rm.validate(state=state, capital=100_000.0,
                        signal_time=datetime(2026, 1, 2, 9, 15))
    assert ok is True


def test_passes_exactly_at_trade_end():
    rm = RiskManager(trade_end=time(15, 15))
    state = RiskState()
    ok, _ = rm.validate(state=state, capital=100_000.0,
                        signal_time=datetime(2026, 1, 2, 15, 15))
    assert ok is True


# ─── Max open positions ───

def test_rejects_when_max_positions_reached():
    rm = RiskManager(max_open_positions=3)
    state = RiskState(open_positions=3)
    ok, reason = rm.validate(state=state, capital=100_000.0,
                             signal_time=datetime(2026, 1, 2, 10, 0))
    assert ok is False
    assert "position" in reason.lower()


def test_passes_when_below_max_positions():
    rm = RiskManager(max_open_positions=3)
    state = RiskState(open_positions=2)
    ok, _ = rm.validate(state=state, capital=100_000.0,
                        signal_time=datetime(2026, 1, 2, 10, 0))
    assert ok is True


# ─── Cooldown ───

def test_rejects_within_cooldown():
    rm = RiskManager(cooldown_seconds=300)
    last = datetime(2026, 1, 2, 10, 0, 0)
    signal = datetime(2026, 1, 2, 10, 4, 0)  # 240s later < 300s cooldown
    state = RiskState(last_trade_time=last)
    ok, reason = rm.validate(state=state, capital=100_000.0, signal_time=signal)
    assert ok is False
    assert "cooldown" in reason.lower()


def test_passes_after_cooldown():
    rm = RiskManager(cooldown_seconds=300)
    last = datetime(2026, 1, 2, 10, 0, 0)
    signal = datetime(2026, 1, 2, 10, 6, 0)  # 360s later > 300s
    state = RiskState(last_trade_time=last)
    ok, _ = rm.validate(state=state, capital=100_000.0, signal_time=signal)
    assert ok is True


def test_no_cooldown_when_no_prior_trade():
    rm = RiskManager(cooldown_seconds=300)
    state = RiskState(last_trade_time=None)
    ok, _ = rm.validate(state=state, capital=100_000.0,
                        signal_time=datetime(2026, 1, 2, 10, 0))
    assert ok is True


# ─── Return types ───

def test_validate_returns_tuple_of_bool_and_str():
    rm = RiskManager()
    state = RiskState()
    result = rm.validate(state=state, capital=100_000.0,
                         signal_time=datetime(2026, 1, 2, 10, 0))
    assert isinstance(result, tuple) and len(result) == 2
    assert type(result[0]) is bool
    assert isinstance(result[1], str)
