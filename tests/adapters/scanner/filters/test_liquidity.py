"""Tests for Liquidity Filter."""
import pytest
import pandas as pd
from datetime import datetime, timedelta


def make_ohlcv(n: int, close: float = 200.0, volume: int = 600000) -> pd.DataFrame:
    """Build n bars of OHLCV data with given close price and volume."""
    idx = [datetime(2026, 1, 2, 9, 15) + timedelta(minutes=i * 5) for i in range(n)]
    return pd.DataFrame(
        [{"open": close - 1, "high": close + 2, "low": close - 2,
          "close": close, "volume": volume}
         for _ in range(n)],
        index=idx,
    )


# ─── Instantiation ───

def test_instantiates_with_defaults():
    from adapters.scanner.filters.liquidity import LiquidityFilter
    f = LiquidityFilter()
    assert f.min_volume == 500_000
    assert f.min_turnover_cr == 10.0


def test_instantiates_with_custom_params():
    from adapters.scanner.filters.liquidity import LiquidityFilter
    f = LiquidityFilter(min_volume=1_000_000, min_turnover_cr=20.0)
    assert f.min_volume == 1_000_000
    assert f.min_turnover_cr == 20.0


# ─── Empty / insufficient data ───

def test_returns_false_on_empty_df():
    from adapters.scanner.filters.liquidity import LiquidityFilter
    assert LiquidityFilter().passes(pd.DataFrame(), "RELIANCE") is False


def test_returns_false_on_single_bar():
    from adapters.scanner.filters.liquidity import LiquidityFilter
    df = make_ohlcv(1, close=200.0, volume=900_000)
    assert LiquidityFilter().passes(df, "RELIANCE") is False


# ─── Volume check ───

def test_passes_when_avg_volume_above_threshold():
    from adapters.scanner.filters.liquidity import LiquidityFilter
    # avg_volume = 600_000 > 500_000; turnover = 200 * 600_000 * n > 10Cr easily
    df = make_ohlcv(20, close=200.0, volume=600_000)
    assert LiquidityFilter().passes(df, "RELIANCE") is True


def test_fails_when_avg_volume_below_threshold():
    from adapters.scanner.filters.liquidity import LiquidityFilter
    # avg_volume = 400_000 < 500_000
    df = make_ohlcv(20, close=200.0, volume=400_000)
    assert LiquidityFilter().passes(df, "RELIANCE") is False


def test_volume_boundary_exactly_at_threshold_passes():
    from adapters.scanner.filters.liquidity import LiquidityFilter
    # avg_volume == 500_000 exactly — should pass (>=)
    df = make_ohlcv(20, close=200.0, volume=500_000)
    assert LiquidityFilter().passes(df, "RELIANCE") is True


# ─── Turnover check ───

def test_passes_when_avg_turnover_above_threshold():
    from adapters.scanner.filters.liquidity import LiquidityFilter
    # turnover per bar = 500 * 600_000 = 30Cr >> 10Cr
    df = make_ohlcv(20, close=500.0, volume=600_000)
    assert LiquidityFilter().passes(df, "RELIANCE") is True


def test_fails_when_avg_turnover_below_threshold():
    from adapters.scanner.filters.liquidity import LiquidityFilter
    # turnover per bar = 10 * 600_000 = 60L = 0.6Cr << 10Cr
    df = make_ohlcv(20, close=10.0, volume=600_000)
    assert LiquidityFilter().passes(df, "RELIANCE") is False


def test_turnover_boundary_exactly_10cr_passes():
    from adapters.scanner.filters.liquidity import LiquidityFilter
    # close=200, volume=500_000 → turnover = 200 * 500_000 = 10Cr exactly
    df = make_ohlcv(20, close=200.0, volume=500_000)
    assert LiquidityFilter().passes(df, "RELIANCE") is True


# ─── Both conditions must pass ───

def test_fails_when_volume_ok_but_turnover_low():
    from adapters.scanner.filters.liquidity import LiquidityFilter
    # volume=600_000 OK, but close=1 → turnover=6L < 10Cr
    df = make_ohlcv(20, close=1.0, volume=600_000)
    assert LiquidityFilter().passes(df, "RELIANCE") is False


def test_fails_when_turnover_ok_but_volume_low():
    from adapters.scanner.filters.liquidity import LiquidityFilter
    # close=10000 → even 300_000 vol gives 300Cr turnover, but volume < 500_000
    df = make_ohlcv(20, close=10_000.0, volume=300_000)
    assert LiquidityFilter().passes(df, "RELIANCE") is False


# ─── Avg uses all bars ───

def test_avg_volume_is_mean_across_all_bars():
    from adapters.scanner.filters.liquidity import LiquidityFilter
    # Mix: 10 bars at 400_000 + 10 bars at 800_000 → avg = 600_000 > 500_000
    idx = [datetime(2026, 1, 2, 9, 15) + timedelta(minutes=i * 5) for i in range(20)]
    volumes = [400_000] * 10 + [800_000] * 10
    df = pd.DataFrame(
        [{"open": 199, "high": 202, "low": 198, "close": 200.0, "volume": v}
         for v in volumes],
        index=idx,
    )
    assert LiquidityFilter().passes(df, "RELIANCE") is True


def test_avg_volume_below_threshold_mixed_bars():
    from adapters.scanner.filters.liquidity import LiquidityFilter
    # 10 bars at 200_000 + 10 bars at 600_000 → avg = 400_000 < 500_000
    idx = [datetime(2026, 1, 2, 9, 15) + timedelta(minutes=i * 5) for i in range(20)]
    volumes = [200_000] * 10 + [600_000] * 10
    df = pd.DataFrame(
        [{"open": 199, "high": 202, "low": 198, "close": 200.0, "volume": v}
         for v in volumes],
        index=idx,
    )
    assert LiquidityFilter().passes(df, "RELIANCE") is False
