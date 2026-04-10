"""Tests for Terminal Dashboard."""
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO


def _sample_positions() -> list[dict]:
    return [
        {"symbol": "RELIANCE", "qty": 10, "entry_price": 500.0,
         "current_price": 510.0, "pnl": 100.0, "direction": "LONG"},
        {"symbol": "TCS", "qty": 5, "entry_price": 3000.0,
         "current_price": 2980.0, "pnl": -100.0, "direction": "LONG"},
    ]


def _sample_signals() -> list[dict]:
    return [
        {"symbol": "INFY", "direction": "LONG", "strategy": "ORB",
         "entry": 1500.0, "sl": 1480.0, "target": 1540.0},
    ]


# ─── Instantiation ───

def test_instantiates():
    from infrastructure.dashboard.terminal_ui import TerminalDashboard
    td = TerminalDashboard()
    assert td is not None


# ─── render_positions ───

def test_render_positions_returns_string():
    from infrastructure.dashboard.terminal_ui import TerminalDashboard
    td = TerminalDashboard()
    out = td.render_positions(_sample_positions())
    assert isinstance(out, str)


def test_render_positions_contains_symbol():
    from infrastructure.dashboard.terminal_ui import TerminalDashboard
    td = TerminalDashboard()
    out = td.render_positions(_sample_positions())
    assert "RELIANCE" in out
    assert "TCS" in out


def test_render_positions_empty():
    from infrastructure.dashboard.terminal_ui import TerminalDashboard
    td = TerminalDashboard()
    out = td.render_positions([])
    assert isinstance(out, str)


# ─── render_signals ───

def test_render_signals_returns_string():
    from infrastructure.dashboard.terminal_ui import TerminalDashboard
    td = TerminalDashboard()
    out = td.render_signals(_sample_signals())
    assert isinstance(out, str)


def test_render_signals_contains_symbol():
    from infrastructure.dashboard.terminal_ui import TerminalDashboard
    td = TerminalDashboard()
    out = td.render_signals(_sample_signals())
    assert "INFY" in out


def test_render_signals_empty():
    from infrastructure.dashboard.terminal_ui import TerminalDashboard
    td = TerminalDashboard()
    out = td.render_signals([])
    assert isinstance(out, str)


# ─── render_summary ───

def test_render_summary_returns_string():
    from infrastructure.dashboard.terminal_ui import TerminalDashboard
    td = TerminalDashboard()
    out = td.render_summary(day_pnl=500.0, capital=100_000.0, open_count=2)
    assert isinstance(out, str)


def test_render_summary_contains_pnl():
    from infrastructure.dashboard.terminal_ui import TerminalDashboard
    td = TerminalDashboard()
    out = td.render_summary(day_pnl=500.0, capital=100_000.0, open_count=2)
    assert "500" in out


def test_render_summary_negative_pnl():
    from infrastructure.dashboard.terminal_ui import TerminalDashboard
    td = TerminalDashboard()
    out = td.render_summary(day_pnl=-300.0, capital=100_000.0, open_count=1)
    assert "300" in out


# ─── print_dashboard ───

def test_print_dashboard_runs_without_error():
    from infrastructure.dashboard.terminal_ui import TerminalDashboard
    td = TerminalDashboard()
    # Should not raise — captures output to string
    output = td.print_dashboard(
        positions=_sample_positions(),
        signals=_sample_signals(),
        day_pnl=100.0,
        capital=100_000.0,
    )
    assert isinstance(output, str)
