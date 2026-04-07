"""Tests for backtester/metrics.py — Sharpe, Sortino, drawdown, win rate, etc."""
import pytest
import math


# ─── Helpers ───

def make_trades(pnls: list[float]):
    """Build minimal SimulatedTrade-like objects from a list of net P&Ls."""
    from unittest.mock import MagicMock
    trades = []
    for pnl in pnls:
        t = MagicMock()
        t.net_pnl = pnl
        trades.append(t)
    return trades


# ─── win_rate ───

def test_win_rate_empty_returns_zero():
    from backtester.metrics import win_rate
    assert win_rate([]) == 0.0


def test_win_rate_all_wins():
    from backtester.metrics import win_rate
    assert win_rate([100, 200, 50]) == pytest.approx(1.0)


def test_win_rate_mixed():
    from backtester.metrics import win_rate
    assert win_rate([100, -50, 200, -30]) == pytest.approx(0.5)


# ─── profit_factor ───

def test_profit_factor_no_losses_returns_inf():
    from backtester.metrics import profit_factor
    assert math.isinf(profit_factor([100, 200, 50]))


def test_profit_factor_no_wins_returns_zero():
    from backtester.metrics import profit_factor
    assert profit_factor([-100, -50]) == pytest.approx(0.0)


def test_profit_factor_correct():
    from backtester.metrics import profit_factor
    # gross_profit=300, gross_loss=100 → 3.0
    assert profit_factor([100, 200, -100]) == pytest.approx(3.0)


def test_profit_factor_empty_returns_zero():
    from backtester.metrics import profit_factor
    assert profit_factor([]) == 0.0


# ─── expectancy ───

def test_expectancy_empty_returns_zero():
    from backtester.metrics import expectancy
    assert expectancy([]) == 0.0


def test_expectancy_correct():
    from backtester.metrics import expectancy
    # (100 + 200 - 50 - 50) / 4 = 50
    assert expectancy([100, 200, -50, -50]) == pytest.approx(50.0)


# ─── max_drawdown ───

def test_max_drawdown_flat_equity_returns_zero():
    from backtester.metrics import max_drawdown
    assert max_drawdown([1000, 1000, 1000]) == pytest.approx(0.0)


def test_max_drawdown_always_rising_returns_zero():
    from backtester.metrics import max_drawdown
    assert max_drawdown([1000, 1100, 1200, 1300]) == pytest.approx(0.0)


def test_max_drawdown_correct():
    from backtester.metrics import max_drawdown
    # peak=1200, trough=900 → dd = (900-1200)/1200 = -0.25
    curve = [1000, 1200, 1100, 900, 1000]
    assert max_drawdown(curve) == pytest.approx(-0.25, rel=0.01)


def test_max_drawdown_returns_negative_fraction():
    from backtester.metrics import max_drawdown
    curve = [1000, 800]
    dd = max_drawdown(curve)
    assert dd < 0


# ─── sharpe_ratio ───

def test_sharpe_ratio_empty_returns_zero():
    from backtester.metrics import sharpe_ratio
    assert sharpe_ratio([]) == 0.0


def test_sharpe_ratio_zero_std_returns_zero():
    from backtester.metrics import sharpe_ratio
    assert sharpe_ratio([100, 100, 100]) == 0.0


def test_sharpe_ratio_positive_for_consistent_gains():
    from backtester.metrics import sharpe_ratio
    pnls = [100] * 20 + [-10] * 5
    assert sharpe_ratio(pnls) > 0


# ─── sortino_ratio ───

def test_sortino_ratio_empty_returns_zero():
    from backtester.metrics import sortino_ratio
    assert sortino_ratio([]) == 0.0


def test_sortino_higher_than_sharpe_when_losses_rare():
    from backtester.metrics import sharpe_ratio, sortino_ratio
    # few small losses → Sortino should be >= Sharpe
    pnls = [100, 100, 100, -10, 100, 100]
    assert sortino_ratio(pnls) >= sharpe_ratio(pnls)


# ─── calmar_ratio ───

def test_calmar_ratio_zero_drawdown_returns_zero():
    from backtester.metrics import calmar_ratio
    assert calmar_ratio(total_return_pct=0.2, max_dd_pct=0.0) == 0.0


def test_calmar_ratio_correct():
    from backtester.metrics import calmar_ratio
    # 20% return / 10% drawdown = 2.0
    assert calmar_ratio(total_return_pct=0.20, max_dd_pct=-0.10) == pytest.approx(2.0)


# ─── calculate_metrics ───

def test_calculate_metrics_returns_metrics_result():
    from backtester.metrics import calculate_metrics, MetricsResult
    trades = make_trades([100, -50, 200, -30, 150])
    result = calculate_metrics(trades, initial_capital=100000)
    assert isinstance(result, MetricsResult)


def test_calculate_metrics_empty_trades():
    from backtester.metrics import calculate_metrics
    result = calculate_metrics([], initial_capital=100000)
    assert result.total_trades == 0
    assert result.win_rate == 0.0
    assert result.total_net_pnl == 0.0


def test_calculate_metrics_values_correct():
    from backtester.metrics import calculate_metrics
    trades = make_trades([100, -50, 200, -30])
    result = calculate_metrics(trades, initial_capital=100000)
    assert result.total_trades == 4
    assert result.win_rate == pytest.approx(0.5)
    assert result.total_net_pnl == pytest.approx(220.0)
    assert result.profit_factor == pytest.approx(300 / 80, rel=0.01)
