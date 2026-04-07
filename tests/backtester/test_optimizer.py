"""Tests for backtester/optimizer.py — grid search parameter optimizer."""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from strategies.base_strategy import BacktestParams


def dt(day: int, h: int, m: int) -> datetime:
    return datetime(2026, 1, day, h, m)


def make_orb_df() -> pd.DataFrame:
    """Multi-bar df with a clear ORB breakout for testing."""
    rows = []
    # Opening range bars (09:15-09:29): high=105, low=98
    for i in range(3):
        t = dt(2, 9, 15 + i * 5)
        rows.append((t, 100, 105, 98, 102, 5000))
    # Post-range bars: breakout above 105
    for i in range(5):
        t = dt(2, 9, 30 + i * 5)
        rows.append((t, 105, 112, 104, 110, 8000))
    idx = [r[0] for r in rows]
    return pd.DataFrame(
        [{"open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]}
         for r in rows],
        index=idx,
    )


def make_params() -> BacktestParams:
    return BacktestParams(
        symbol="RELIANCE", token="2885", interval="5m",
        from_dt=datetime(2026, 1, 1), to_dt=datetime(2026, 3, 31),
        initial_capital=100000.0,
    )


# ─── OptimizationResult ───

def test_optimization_result_is_frozen():
    from backtester.optimizer import OptimizationResult
    from backtester.metrics import MetricsResult
    m = MetricsResult(0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    r = OptimizationResult(params={"a": 1}, metrics=m, trades=[])
    with pytest.raises((AttributeError, TypeError)):
        r.params = {}


def test_optimization_result_stores_fields():
    from backtester.optimizer import OptimizationResult
    from backtester.metrics import MetricsResult
    m = MetricsResult(5, 0.6, 2.0, 100.0, 1.4, 1.8, -0.05, 2.5, 500.0, 0.005)
    r = OptimizationResult(params={"x": 10}, metrics=m, trades=[])
    assert r.params == {"x": 10}
    assert r.metrics.total_trades == 5


# ─── run_backtest ───

def test_run_backtest_returns_trades_and_metrics():
    from backtester.optimizer import run_backtest
    from strategies.orb import ORBStrategy
    strategy = ORBStrategy()
    df = make_orb_df()
    trades, metrics = run_backtest(strategy, df, make_params(), qty=10)
    assert isinstance(trades, list)
    from backtester.metrics import MetricsResult
    assert isinstance(metrics, MetricsResult)


def test_run_backtest_empty_df_returns_empty():
    from backtester.optimizer import run_backtest
    from strategies.orb import ORBStrategy
    trades, metrics = run_backtest(ORBStrategy(), pd.DataFrame(), make_params(), qty=10)
    assert trades == []
    assert metrics.total_trades == 0


# ─── grid_search ───

def test_grid_search_returns_best_and_all():
    from backtester.optimizer import grid_search
    from strategies.orb import ORBStrategy
    param_grid = {"opening_range_minutes": [15, 30]}
    best, all_results = grid_search(ORBStrategy, param_grid, make_orb_df(), make_params())
    from backtester.optimizer import OptimizationResult
    assert isinstance(best, OptimizationResult)
    assert isinstance(all_results, list)


def test_grid_search_tries_all_combinations():
    from backtester.optimizer import grid_search
    from strategies.orb import ORBStrategy
    param_grid = {
        "opening_range_minutes": [15, 30],
        "target_multiplier": [1.5, 2.0, 2.5],
    }
    _, all_results = grid_search(ORBStrategy, param_grid, make_orb_df(), make_params())
    assert len(all_results) == 6  # 2 × 3


def test_grid_search_empty_param_grid_runs_once():
    from backtester.optimizer import grid_search
    from strategies.orb import ORBStrategy
    _, all_results = grid_search(ORBStrategy, {}, make_orb_df(), make_params())
    assert len(all_results) == 1


def test_grid_search_best_has_highest_sharpe():
    from backtester.optimizer import grid_search
    from strategies.orb import ORBStrategy
    param_grid = {"opening_range_minutes": [15, 30, 45]}
    best, all_results = grid_search(ORBStrategy, param_grid, make_orb_df(), make_params())
    sharpes = [r.metrics.sharpe_ratio for r in all_results]
    assert best.metrics.sharpe_ratio == max(sharpes)


def test_grid_search_optimize_for_profit_factor():
    from backtester.optimizer import grid_search
    from strategies.orb import ORBStrategy
    param_grid = {"opening_range_minutes": [15, 30]}
    best, all_results = grid_search(
        ORBStrategy, param_grid, make_orb_df(), make_params(),
        optimize_for="profit_factor",
    )
    pfs = [r.metrics.profit_factor for r in all_results]
    # best profit_factor should be the max among finite values
    finite_pfs = [p for p in pfs if p != float("inf")]
    if finite_pfs:
        assert best.metrics.profit_factor >= max(finite_pfs)


def test_grid_search_all_results_have_correct_params():
    from backtester.optimizer import grid_search
    from strategies.orb import ORBStrategy
    param_grid = {"opening_range_minutes": [15, 30]}
    _, all_results = grid_search(ORBStrategy, param_grid, make_orb_df(), make_params())
    used_values = {r.params["opening_range_minutes"] for r in all_results}
    assert used_values == {15, 30}


def test_grid_search_custom_qty():
    from backtester.optimizer import grid_search
    from strategies.orb import ORBStrategy
    param_grid = {"opening_range_minutes": [15]}
    best, _ = grid_search(ORBStrategy, param_grid, make_orb_df(), make_params(), qty=5)
    assert isinstance(best.trades, list)
