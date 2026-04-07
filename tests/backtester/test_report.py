"""Tests for backtester/report.py — HTML report generator."""
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock


def make_metrics(**overrides):
    from backtester.metrics import MetricsResult
    defaults = dict(
        total_trades=10, win_rate=0.6, profit_factor=2.1,
        expectancy=150.0, sharpe_ratio=1.4, sortino_ratio=1.8,
        max_drawdown_pct=-0.08, calmar_ratio=2.5,
        total_net_pnl=1500.0, total_return_pct=0.015,
    )
    defaults.update(overrides)
    return MetricsResult(**defaults)


def make_trades(n: int = 5):
    trades = []
    for i in range(n):
        t = MagicMock()
        t.symbol = "RELIANCE"
        t.direction = "LONG" if i % 2 == 0 else "SHORT"
        t.entry_price = 100.0 + i
        t.exit_price = 105.0 + i
        t.qty = 10
        t.net_pnl = 200.0 if i % 2 == 0 else -80.0
        t.entry_time = datetime(2026, 1, i + 2, 9, 15)
        t.exit_time = datetime(2026, 1, i + 2, 11, 30)
        trades.append(t)
    return trades


def make_params():
    from strategies.base_strategy import BacktestParams
    return BacktestParams(
        symbol="RELIANCE", token="2885", interval="5m",
        from_dt=datetime(2026, 1, 1), to_dt=datetime(2026, 3, 31),
        initial_capital=100000.0,
    )


# ─── generate_report ───

def test_generate_report_creates_html_file(tmp_path):
    from backtester.report import generate_report
    out = generate_report(make_trades(), make_metrics(), make_params(), tmp_path)
    assert out.exists()
    assert out.suffix == ".html"


def test_generate_report_returns_path(tmp_path):
    from backtester.report import generate_report
    result = generate_report(make_trades(), make_metrics(), make_params(), tmp_path)
    assert isinstance(result, Path)


def test_report_contains_strategy_symbol(tmp_path):
    from backtester.report import generate_report
    out = generate_report(make_trades(), make_metrics(), make_params(), tmp_path)
    html = out.read_text(encoding="utf-8")
    assert "RELIANCE" in html


def test_report_contains_equity_curve_section(tmp_path):
    from backtester.report import generate_report
    out = generate_report(make_trades(), make_metrics(), make_params(), tmp_path)
    html = out.read_text(encoding="utf-8")
    assert "Equity Curve" in html


def test_report_contains_drawdown_section(tmp_path):
    from backtester.report import generate_report
    out = generate_report(make_trades(), make_metrics(), make_params(), tmp_path)
    html = out.read_text(encoding="utf-8")
    assert "Drawdown" in html


def test_report_contains_trade_log_section(tmp_path):
    from backtester.report import generate_report
    out = generate_report(make_trades(), make_metrics(), make_params(), tmp_path)
    html = out.read_text(encoding="utf-8")
    assert "Trade Log" in html


def test_report_contains_monthly_pnl_section(tmp_path):
    from backtester.report import generate_report
    out = generate_report(make_trades(), make_metrics(), make_params(), tmp_path)
    html = out.read_text(encoding="utf-8")
    assert "Monthly" in html


def test_report_contains_key_metrics(tmp_path):
    from backtester.report import generate_report
    out = generate_report(make_trades(), make_metrics(), make_params(), tmp_path)
    html = out.read_text(encoding="utf-8")
    assert "Win Rate" in html
    assert "Sharpe" in html
    assert "Max Drawdown" in html
    assert "Profit Factor" in html


def test_report_contains_trade_rows(tmp_path):
    from backtester.report import generate_report
    trades = make_trades(3)
    out = generate_report(trades, make_metrics(total_trades=3), make_params(), tmp_path)
    html = out.read_text(encoding="utf-8")
    # Each trade direction should appear
    assert "LONG" in html


def test_report_with_empty_trades_does_not_raise(tmp_path):
    from backtester.report import generate_report
    out = generate_report(
        [], make_metrics(total_trades=0, win_rate=0.0), make_params(), tmp_path
    )
    assert out.exists()


def test_report_filename_includes_symbol_and_interval(tmp_path):
    from backtester.report import generate_report
    out = generate_report(make_trades(), make_metrics(), make_params(), tmp_path)
    assert "RELIANCE" in out.name
    assert "5m" in out.name
