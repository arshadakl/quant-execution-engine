"""Tests for Volatility Filter."""
import pytest
import pandas as pd
from datetime import datetime, timedelta


def make_ohlcv(
    n: int,
    close: float = 500.0,
    atr_range: float = 10.0,  # high - low per bar
    volume: int = 600_000,
) -> pd.DataFrame:
    """Build n bars; bar range = atr_range for predictable ATR."""
    idx = [datetime(2026, 1, 2, 9, 15) + timedelta(minutes=i * 5) for i in range(n)]
    rows = []
    for i in range(n):
        rows.append({
            "open": close,
            "high": close + atr_range / 2,
            "low": close - atr_range / 2,
            "close": close,
            "volume": volume,
        })
    return pd.DataFrame(rows, index=idx)


def make_trending(n: int = 20, start: float = 500.0, step: float = 1.0,
                   atr_range: float = 10.0) -> pd.DataFrame:
    """Rising close prices with consistent bar range."""
    idx = [datetime(2026, 1, 2, 9, 15) + timedelta(minutes=i * 5) for i in range(n)]
    rows = []
    for i in range(n):
        c = start + i * step
        rows.append({
            "open": c - 0.5,
            "high": c + atr_range / 2,
            "low": c - atr_range / 2,
            "close": c,
            "volume": 600_000,
        })
    return pd.DataFrame(rows, index=idx)


# ─── Instantiation ───

def test_instantiates_with_defaults():
    from adapters.scanner.filters.volatility import VolatilityFilter
    f = VolatilityFilter()
    assert f.atr_period == 14
    assert f.min_atr_pct == 0.015
    assert f.min_price == 100.0
    assert f.max_price == 5000.0


def test_instantiates_with_custom_params():
    from adapters.scanner.filters.volatility import VolatilityFilter
    f = VolatilityFilter(atr_period=7, min_atr_pct=0.02, min_price=200.0, max_price=3000.0)
    assert f.atr_period == 7
    assert f.min_atr_pct == 0.02
    assert f.min_price == 200.0
    assert f.max_price == 3000.0


# ─── Empty / insufficient data ───

def test_returns_false_on_empty_df():
    from adapters.scanner.filters.volatility import VolatilityFilter
    assert VolatilityFilter().passes(pd.DataFrame(), "RELIANCE") is False


def test_returns_false_when_fewer_bars_than_atr_period():
    from adapters.scanner.filters.volatility import VolatilityFilter
    df = make_ohlcv(10, close=500.0, atr_range=10.0)  # < 14 bars
    assert VolatilityFilter().passes(df, "RELIANCE") is False


# ─── Price range check ───

def test_fails_when_close_below_min_price():
    from adapters.scanner.filters.volatility import VolatilityFilter
    # close=50 < 100 min_price; give enough ATR to pass that check
    df = make_ohlcv(20, close=50.0, atr_range=5.0)
    assert VolatilityFilter().passes(df, "RELIANCE") is False


def test_fails_when_close_above_max_price():
    from adapters.scanner.filters.volatility import VolatilityFilter
    # close=6000 > 5000 max_price
    df = make_ohlcv(20, close=6000.0, atr_range=100.0)
    assert VolatilityFilter().passes(df, "RELIANCE") is False


def test_passes_at_min_price_boundary():
    from adapters.scanner.filters.volatility import VolatilityFilter
    # close=100 exactly, ATR=10 → ATR%=10% > 1.5%
    df = make_ohlcv(20, close=100.0, atr_range=20.0)
    assert VolatilityFilter().passes(df, "RELIANCE") is True


def test_passes_at_max_price_boundary():
    from adapters.scanner.filters.volatility import VolatilityFilter
    # close=5000, ATR=100 → ATR%=2% > 1.5%
    df = make_ohlcv(20, close=5000.0, atr_range=200.0)
    assert VolatilityFilter().passes(df, "RELIANCE") is True


# ─── ATR % check ───

def test_passes_when_atr_pct_above_threshold():
    from adapters.scanner.filters.volatility import VolatilityFilter
    # close=500, atr_range=20 → ATR≈10 (half range used by true range) but range=20
    # ATR% = 20/500 = 4% >> 1.5%
    df = make_ohlcv(20, close=500.0, atr_range=20.0)
    assert VolatilityFilter().passes(df, "RELIANCE") is True


def test_fails_when_atr_pct_below_threshold():
    from adapters.scanner.filters.volatility import VolatilityFilter
    # close=500, atr_range=2 → ATR%=0.4% < 1.5%
    df = make_ohlcv(20, close=500.0, atr_range=2.0)
    assert VolatilityFilter().passes(df, "RELIANCE") is False


def test_atr_uses_last_bar_close_for_pct():
    from adapters.scanner.filters.volatility import VolatilityFilter
    # Trending df: last close is higher, ATR% based on last close
    df = make_trending(n=20, start=490.0, step=1.0, atr_range=20.0)
    # last close ≈ 509, ATR% = 20/509 ≈ 3.9% > 1.5% → should pass
    assert VolatilityFilter().passes(df, "RELIANCE") is True


# ─── compute_atr exposed ───

def test_compute_atr_returns_series_of_same_length():
    from adapters.scanner.filters.volatility import compute_atr
    df = make_ohlcv(20, close=500.0, atr_range=10.0)
    atr = compute_atr(df, period=14)
    assert len(atr) == len(df)


def test_compute_atr_flat_bars_equals_bar_range():
    from adapters.scanner.filters.volatility import compute_atr
    # When H-L = constant and prev_close == close, TR = H-L
    df = make_ohlcv(30, close=500.0, atr_range=10.0)
    atr = compute_atr(df, period=14)
    # After warm-up, ATR should converge to 10
    assert atr.iloc[-1] == pytest.approx(10.0, rel=0.05)
