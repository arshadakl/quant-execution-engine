"""Parameter optimizer — grid search over strategy param_grid.

Uses run_backtest() to evaluate each param combination, then ranks
all results by a chosen MetricsResult field (default: sharpe_ratio).
"""
import itertools
import logging
import math
from dataclasses import dataclass
from typing import Any

import pandas as pd

from backtester.metrics import MetricsResult, calculate_metrics
from backtester.trade_simulator import SimulatedTrade, TradeSimulator
from strategies.base_strategy import BacktestParams, BaseStrategy

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OptimizationResult:
    """Single backtest run result with the params that produced it."""

    params: dict
    metrics: MetricsResult
    trades: list


def run_backtest(
    strategy: BaseStrategy,
    df: pd.DataFrame,
    params: BacktestParams,
    qty: int = 1,
) -> tuple[list[SimulatedTrade], MetricsResult]:
    """Run one backtest: generate signals → simulate trades → compute metrics."""
    signals = strategy.generate_signals(df, params.symbol)
    sim = TradeSimulator()
    trades = [
        t for s in signals
        if (t := sim.simulate(s, df, qty)) is not None
    ]
    metrics = calculate_metrics(trades, params.initial_capital)
    return trades, metrics


def grid_search(
    strategy_cls: type[BaseStrategy],
    param_grid: dict[str, list],
    df: pd.DataFrame,
    backtest_params: BacktestParams,
    qty: int = 1,
    optimize_for: str = "sharpe_ratio",
) -> tuple[OptimizationResult, list[OptimizationResult]]:
    """Run grid search over all param combinations.

    Returns (best_result, all_results) sorted descending by optimize_for.
    """
    combos = _all_combinations(param_grid)
    all_results: list[OptimizationResult] = []

    for combo in combos:
        strategy = strategy_cls(params=combo)
        trades, metrics = run_backtest(strategy, df, backtest_params, qty)
        all_results.append(OptimizationResult(params=combo, metrics=metrics, trades=trades))
        logger.debug("Grid search: params=%s sharpe=%.3f", combo, metrics.sharpe_ratio)

    all_results.sort(key=lambda r: _sort_key(r, optimize_for), reverse=True)
    best = all_results[0]
    logger.info(
        "Optimizer: best params=%s %s=%.4f",
        best.params, optimize_for, getattr(best.metrics, optimize_for),
    )
    return best, all_results


def _all_combinations(param_grid: dict[str, list]) -> list[dict]:
    """Return list of all param dicts from grid — one entry per combination."""
    if not param_grid:
        return [{}]
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


def _sort_key(result: OptimizationResult, field: str) -> float:
    """Return sortable float for a metrics field (handles inf gracefully)."""
    val = getattr(result.metrics, field, 0.0)
    if isinstance(val, float) and math.isinf(val):
        return 1e9
    return float(val)
