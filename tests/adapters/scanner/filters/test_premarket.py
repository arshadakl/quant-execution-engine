"""Tests for Pre-market Signals filter."""
import pytest
import pandas as pd
from datetime import datetime, timedelta


def make_prev_day(close: float = 500.0, volume: int = 600_000, n: int = 20) -> pd.DataFrame:
    """Previous day bars ending at 15:30."""
    base = datetime(2026, 1, 1, 9, 15)
    idx = [base + timedelta(minutes=i * 5) for i in range(n)]
    return pd.DataFrame(
        [{"open": close - 1, "high": close + 2, "low": close - 2,
          "close": close, "volume": volume}
         for _ in range(n)],
        index=idx,
    )


def make_today(open_: float = 510.0, volume: int = 1_200_000, n: int = 5) -> pd.DataFrame:
    """Today's early bars starting at 09:15."""
    base = datetime(2026, 1, 2, 9, 15)
    idx = [base + timedelta(minutes=i * 5) for i in range(n)]
    return pd.DataFrame(
        [{"open": open_, "high": open_ + 2, "low": open_ - 2,
          "close": open_, "volume": volume}
         for _ in range(n)],
        index=idx,
    )


# ─── Instantiation ───

def test_instantiates_with_defaults():
    from adapters.scanner.filters.premarket import PreMarketFilter
    f = PreMarketFilter()
    assert f.min_gap_pct == 0.005
    assert f.volume_spike_mult == 1.5


def test_instantiates_with_custom_params():
    from adapters.scanner.filters.premarket import PreMarketFilter
    f = PreMarketFilter(min_gap_pct=0.01, volume_spike_mult=2.0)
    assert f.min_gap_pct == 0.01
    assert f.volume_spike_mult == 2.0


# ─── Empty / insufficient data ───

def test_returns_false_on_empty_prev_day():
    from adapters.scanner.filters.premarket import PreMarketFilter
    today = make_today(open_=510.0)
    assert PreMarketFilter().passes(pd.DataFrame(), today, "RELIANCE") is False


def test_returns_false_on_empty_today():
    from adapters.scanner.filters.premarket import PreMarketFilter
    prev = make_prev_day(close=500.0)
    assert PreMarketFilter().passes(prev, pd.DataFrame(), "RELIANCE") is False


# ─── Gap detection ───

def test_detects_gap_up():
    from adapters.scanner.filters.premarket import PreMarketFilter
    prev = make_prev_day(close=500.0, volume=600_000)
    # open 510 → gap = (510-500)/500 = 2% > 0.5%
    today = make_today(open_=510.0, volume=1_200_000)
    result = PreMarketFilter().passes(prev, today, "RELIANCE")
    assert result is True


def test_detects_gap_down():
    from adapters.scanner.filters.premarket import PreMarketFilter
    prev = make_prev_day(close=500.0, volume=600_000)
    # open 487 → gap = abs(487-500)/500 = 2.6% > 0.5%
    today = make_today(open_=487.0, volume=1_200_000)
    result = PreMarketFilter().passes(prev, today, "RELIANCE")
    assert result is True


def test_fails_when_gap_below_threshold():
    from adapters.scanner.filters.premarket import PreMarketFilter
    prev = make_prev_day(close=500.0, volume=600_000)
    # open 501 → gap = 0.2% < 0.5%
    today = make_today(open_=501.0, volume=1_200_000)
    result = PreMarketFilter().passes(prev, today, "RELIANCE")
    assert result is False


def test_gap_boundary_exactly_05pct_passes():
    from adapters.scanner.filters.premarket import PreMarketFilter
    prev = make_prev_day(close=500.0, volume=600_000)
    # open 502.5 → gap = 0.5% exactly
    today = make_today(open_=502.5, volume=1_200_000)
    result = PreMarketFilter().passes(prev, today, "RELIANCE")
    assert result is True


# ─── Volume spike detection ───

def test_fails_when_volume_spike_absent():
    from adapters.scanner.filters.premarket import PreMarketFilter
    prev = make_prev_day(close=500.0, volume=600_000)
    # today volume = 600_000 = same as prev avg → no spike (< 1.5x)
    today = make_today(open_=510.0, volume=600_000)
    result = PreMarketFilter().passes(prev, today, "RELIANCE")
    assert result is False


def test_passes_when_volume_spike_present():
    from adapters.scanner.filters.premarket import PreMarketFilter
    prev = make_prev_day(close=500.0, volume=600_000)
    # today volume = 1_200_000 = 2x prev avg → spike > 1.5x
    today = make_today(open_=510.0, volume=1_200_000)
    result = PreMarketFilter().passes(prev, today, "RELIANCE")
    assert result is True


def test_volume_spike_boundary_at_15x_passes():
    from adapters.scanner.filters.premarket import PreMarketFilter
    prev = make_prev_day(close=500.0, volume=600_000)
    # today volume = 900_000 = 1.5x → boundary, should pass (>=)
    today = make_today(open_=510.0, volume=900_000)
    result = PreMarketFilter().passes(prev, today, "RELIANCE")
    assert result is True


# ─── compute_gap exposed ───

def test_compute_gap_positive_for_gap_up():
    from adapters.scanner.filters.premarket import compute_gap_pct
    assert compute_gap_pct(prev_close=500.0, today_open=510.0) == pytest.approx(0.02)


def test_compute_gap_negative_for_gap_down():
    from adapters.scanner.filters.premarket import compute_gap_pct
    assert compute_gap_pct(prev_close=500.0, today_open=490.0) == pytest.approx(-0.02)


def test_compute_gap_zero_for_flat_open():
    from adapters.scanner.filters.premarket import compute_gap_pct
    assert compute_gap_pct(prev_close=500.0, today_open=500.0) == pytest.approx(0.0)


# ─── result type ───

def test_result_is_plain_bool():
    from adapters.scanner.filters.premarket import PreMarketFilter
    prev = make_prev_day(close=500.0)
    today = make_today(open_=510.0, volume=1_200_000)
    result = PreMarketFilter().passes(prev, today, "RELIANCE")
    assert type(result) is bool
