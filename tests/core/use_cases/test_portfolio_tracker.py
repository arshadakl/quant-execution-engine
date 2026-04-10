"""Tests for Portfolio Tracker."""
import pytest
from datetime import datetime
from core.use_cases.portfolio_tracker import PortfolioTracker, PositionRecord


# ─── Instantiation ───

def test_instantiates_with_capital():
    pt = PortfolioTracker(initial_capital=100_000.0)
    assert pt.initial_capital == 100_000.0
    assert pt.cash == 100_000.0
    assert pt.day_pnl == 0.0
    assert pt.peak_capital == 100_000.0


# ─── Open position ───

def test_open_position_reduces_cash():
    pt = PortfolioTracker(initial_capital=100_000.0)
    pt.open_position("RELIANCE", qty=10, entry_price=500.0)
    # cost = 10 * 500 = 5000
    assert pt.cash == 95_000.0


def test_open_position_recorded():
    pt = PortfolioTracker(initial_capital=100_000.0)
    pt.open_position("RELIANCE", qty=10, entry_price=500.0)
    assert "RELIANCE" in pt.positions
    pos = pt.positions["RELIANCE"]
    assert pos.qty == 10
    assert pos.entry_price == 500.0


def test_open_multiple_positions():
    pt = PortfolioTracker(initial_capital=100_000.0)
    pt.open_position("RELIANCE", qty=10, entry_price=500.0)
    pt.open_position("TCS", qty=5, entry_price=3000.0)
    assert len(pt.positions) == 2
    assert pt.cash == 100_000.0 - 5_000.0 - 15_000.0


# ─── Close position ───

def test_close_position_adds_proceeds_to_cash():
    pt = PortfolioTracker(initial_capital=100_000.0)
    pt.open_position("RELIANCE", qty=10, entry_price=500.0)
    pt.close_position("RELIANCE", exit_price=520.0)
    # proceeds = 10 * 520 = 5200; started with 95000 → 100200
    assert pt.cash == pytest.approx(100_200.0)


def test_close_position_removes_from_open():
    pt = PortfolioTracker(initial_capital=100_000.0)
    pt.open_position("RELIANCE", qty=10, entry_price=500.0)
    pt.close_position("RELIANCE", exit_price=520.0)
    assert "RELIANCE" not in pt.positions


def test_close_position_updates_day_pnl():
    pt = PortfolioTracker(initial_capital=100_000.0)
    pt.open_position("RELIANCE", qty=10, entry_price=500.0)
    pt.close_position("RELIANCE", exit_price=520.0)
    # pnl = (520-500)*10 = 200
    assert pt.day_pnl == pytest.approx(200.0)


def test_close_losing_position_negative_pnl():
    pt = PortfolioTracker(initial_capital=100_000.0)
    pt.open_position("RELIANCE", qty=10, entry_price=500.0)
    pt.close_position("RELIANCE", exit_price=480.0)
    # pnl = (480-500)*10 = -200
    assert pt.day_pnl == pytest.approx(-200.0)


def test_close_nonexistent_position_raises():
    pt = PortfolioTracker(initial_capital=100_000.0)
    with pytest.raises(KeyError):
        pt.close_position("RELIANCE", exit_price=500.0)


# ─── Equity and drawdown ───

def test_equity_equals_cash_plus_open_value():
    pt = PortfolioTracker(initial_capital=100_000.0)
    pt.open_position("RELIANCE", qty=10, entry_price=500.0)
    # mark at 510
    equity = pt.equity(mark_prices={"RELIANCE": 510.0})
    # cash=95000, open_value=10*510=5100 → equity=100100
    assert equity == pytest.approx(100_100.0)


def test_equity_no_open_positions_equals_cash():
    pt = PortfolioTracker(initial_capital=100_000.0)
    assert pt.equity({}) == pytest.approx(100_000.0)


def test_drawdown_zero_at_start():
    pt = PortfolioTracker(initial_capital=100_000.0)
    assert pt.drawdown({}) == pytest.approx(0.0)


def test_drawdown_reflects_loss():
    pt = PortfolioTracker(initial_capital=100_000.0)
    pt.open_position("RELIANCE", qty=10, entry_price=500.0)
    pt.close_position("RELIANCE", exit_price=480.0)
    # equity now = 99800; peak = 100000 → drawdown = -200/100000 = -0.002
    dd = pt.drawdown({})
    assert dd == pytest.approx(-0.002, abs=0.0001)


def test_peak_updates_on_profit():
    pt = PortfolioTracker(initial_capital=100_000.0)
    pt.open_position("RELIANCE", qty=10, entry_price=500.0)
    pt.close_position("RELIANCE", exit_price=520.0)
    # equity = 100200 > peak 100000 → peak updated
    assert pt.peak_capital == pytest.approx(100_200.0)


# ─── Open position count ───

def test_open_position_count():
    pt = PortfolioTracker(initial_capital=100_000.0)
    assert pt.open_position_count == 0
    pt.open_position("RELIANCE", qty=5, entry_price=500.0)
    assert pt.open_position_count == 1
    pt.open_position("TCS", qty=2, entry_price=3000.0)
    assert pt.open_position_count == 2
    pt.close_position("RELIANCE", exit_price=510.0)
    assert pt.open_position_count == 1
