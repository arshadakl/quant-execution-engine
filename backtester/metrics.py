"""Performance metrics for backtesting.

All metric functions accept a list of net P&L floats (one per trade).
calculate_metrics() is the main entry point — returns a MetricsResult.
"""
import math
import statistics
from dataclasses import dataclass
from typing import Any

_TRADING_DAYS = 252


@dataclass(frozen=True)
class MetricsResult:
    """Full performance summary for a backtest run."""

    total_trades: int
    win_rate: float
    profit_factor: float
    expectancy: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    calmar_ratio: float
    total_net_pnl: float
    total_return_pct: float


# ─── Individual metric functions ───

def win_rate(pnls: list[float]) -> float:
    """Fraction of trades that are profitable."""
    if not pnls:
        return 0.0
    return sum(1 for p in pnls if p > 0) / len(pnls)


def profit_factor(pnls: list[float]) -> float:
    """Gross profit / gross loss. Returns inf when no losing trades."""
    if not pnls:
        return 0.0
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p < 0))
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def expectancy(pnls: list[float]) -> float:
    """Average net P&L per trade."""
    if not pnls:
        return 0.0
    return sum(pnls) / len(pnls)


def max_drawdown(equity_curve: list[float]) -> float:
    """Maximum peak-to-trough drawdown as a negative fraction."""
    if len(equity_curve) < 2:
        return 0.0
    peak = equity_curve[0]
    worst = 0.0
    for value in equity_curve[1:]:
        if value > peak:
            peak = value
        dd = (value - peak) / peak
        if dd < worst:
            worst = dd
    return worst


def sharpe_ratio(pnls: list[float], risk_free: float = 0.0) -> float:
    """Annualised Sharpe ratio. Returns 0 if std dev is zero or insufficient data."""
    if len(pnls) < 2:
        return 0.0
    std = statistics.stdev(pnls)
    if std == 0:
        return 0.0
    mean = statistics.mean(pnls)
    return (mean - risk_free) / std * math.sqrt(_TRADING_DAYS)


def sortino_ratio(pnls: list[float], risk_free: float = 0.0) -> float:
    """Annualised Sortino ratio (penalises only downside deviation)."""
    if len(pnls) < 2:
        return 0.0
    downside = [p for p in pnls if p < 0]
    if not downside:
        return math.inf if sum(pnls) > 0 else 0.0
    downside_std = statistics.stdev(downside) if len(downside) > 1 else abs(downside[0])
    if downside_std == 0:
        return 0.0
    mean = statistics.mean(pnls)
    return (mean - risk_free) / downside_std * math.sqrt(_TRADING_DAYS)


def calmar_ratio(total_return_pct: float, max_dd_pct: float) -> float:
    """Total return / absolute max drawdown. Returns 0 if drawdown is zero."""
    if max_dd_pct == 0:
        return 0.0
    return total_return_pct / abs(max_dd_pct)


# ─── Main entry point ───

def calculate_metrics(trades: list[Any], initial_capital: float) -> MetricsResult:
    """Compute all metrics from a list of SimulatedTrade objects."""
    pnls = [t.net_pnl for t in trades]
    total_pnl = sum(pnls)
    total_return = total_pnl / initial_capital if initial_capital else 0.0

    equity = [initial_capital + sum(pnls[:i]) for i in range(len(pnls) + 1)]
    mdd = max_drawdown(equity)

    return MetricsResult(
        total_trades=len(trades),
        win_rate=win_rate(pnls),
        profit_factor=profit_factor(pnls),
        expectancy=expectancy(pnls),
        sharpe_ratio=sharpe_ratio(pnls),
        sortino_ratio=sortino_ratio(pnls),
        max_drawdown_pct=mdd,
        calmar_ratio=calmar_ratio(total_return, mdd),
        total_net_pnl=total_pnl,
        total_return_pct=total_return,
    )
