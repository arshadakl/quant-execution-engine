"""Tests for Gap Fill strategy."""
import pytest
import pandas as pd
from datetime import datetime, timedelta


def make_day(date: datetime, bars: list[tuple]) -> pd.DataFrame:
    """bars: [(minute_offset, open, high, low, close, volume)]"""
    idx = [date.replace(hour=9, minute=15) + timedelta(minutes=m) for m, *_ in bars]
    return pd.DataFrame(
        [{"open": r[0], "high": r[1], "low": r[2], "close": r[3], "volume": r[4]}
         for _, *r in bars],
        index=idx,
    )


def two_day_df(prev_close: float, today_open: float, n_today: int = 5) -> pd.DataFrame:
    """Build a two-day df: yesterday ends at prev_close, today opens at today_open."""
    day1 = make_day(datetime(2026, 1, 5), [
        (0,  prev_close - 0.5, prev_close + 1, prev_close - 1, prev_close, 5000),
        (5,  prev_close,       prev_close + 1, prev_close - 1, prev_close, 4000),
    ])
    day2_rows = []
    for i in range(n_today):
        price = today_open + i * 0.1
        day2_rows.append((i * 5, price, price + 1, price - 1, price, 3000))
    day2 = make_day(datetime(2026, 1, 6), day2_rows)
    return pd.concat([day1, day2])


# ─── Instantiation ───

def test_instantiates_with_defaults():
    from strategies.gap_fill import GapFillStrategy
    s = GapFillStrategy()
    assert s.params["min_gap_pct"] == 0.005
    assert s.params["sl_multiplier"] == 0.5


def test_is_i_strategy():
    from strategies.gap_fill import GapFillStrategy
    from core.interfaces.i_strategy import IStrategy
    assert isinstance(GapFillStrategy(), IStrategy)


def test_name():
    from strategies.gap_fill import GapFillStrategy
    assert GapFillStrategy().name == "GAP_FILL"


# ─── No signal ───

def test_no_signal_empty_df():
    from strategies.gap_fill import GapFillStrategy
    assert GapFillStrategy().generate_signals(pd.DataFrame(), "RELIANCE") == []


def test_no_signal_single_day():
    from strategies.gap_fill import GapFillStrategy
    df = make_day(datetime(2026, 1, 5), [
        (0, 100, 101, 99, 100, 5000),
        (5, 100, 101, 99, 100, 4000),
    ])
    assert GapFillStrategy().generate_signals(df, "RELIANCE") == []


def test_no_signal_gap_below_threshold():
    from strategies.gap_fill import GapFillStrategy
    # gap = 0.2% < 0.5% threshold
    df = two_day_df(prev_close=100.0, today_open=100.2)
    assert GapFillStrategy().generate_signals(df, "RELIANCE") == []


# ─── Gap UP → SHORT ───

def test_short_signal_on_gap_up():
    from strategies.gap_fill import GapFillStrategy
    # gap up 2%: prev_close=100, today_open=102
    df = two_day_df(prev_close=100.0, today_open=102.0)
    signals = GapFillStrategy().generate_signals(df, "RELIANCE")
    assert len(signals) == 1
    assert signals[0].direction == "SHORT"


def test_short_entry_is_today_open():
    from strategies.gap_fill import GapFillStrategy
    df = two_day_df(prev_close=100.0, today_open=102.0)
    signals = GapFillStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].entry_price == pytest.approx(102.0)


def test_short_target_is_prev_close():
    from strategies.gap_fill import GapFillStrategy
    df = two_day_df(prev_close=100.0, today_open=102.0)
    signals = GapFillStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].target_1 == pytest.approx(100.0)


def test_short_sl_above_entry():
    from strategies.gap_fill import GapFillStrategy
    df = two_day_df(prev_close=100.0, today_open=102.0)
    signals = GapFillStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].stop_loss > signals[0].entry_price


# ─── Gap DOWN → LONG ───

def test_long_signal_on_gap_down():
    from strategies.gap_fill import GapFillStrategy
    # gap down 2%: prev_close=100, today_open=98
    df = two_day_df(prev_close=100.0, today_open=98.0)
    signals = GapFillStrategy().generate_signals(df, "RELIANCE")
    assert len(signals) == 1
    assert signals[0].direction == "LONG"


def test_long_entry_is_today_open():
    from strategies.gap_fill import GapFillStrategy
    df = two_day_df(prev_close=100.0, today_open=98.0)
    signals = GapFillStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].entry_price == pytest.approx(98.0)


def test_long_target_is_prev_close():
    from strategies.gap_fill import GapFillStrategy
    df = two_day_df(prev_close=100.0, today_open=98.0)
    signals = GapFillStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].target_1 == pytest.approx(100.0)


def test_long_sl_below_entry():
    from strategies.gap_fill import GapFillStrategy
    df = two_day_df(prev_close=100.0, today_open=98.0)
    signals = GapFillStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].stop_loss < signals[0].entry_price


# ─── SL uses sl_multiplier ───

def test_sl_distance_equals_gap_times_multiplier():
    from strategies.gap_fill import GapFillStrategy
    # gap = 2.0, sl_multiplier = 0.5 → SL distance = 1.0
    df = two_day_df(prev_close=100.0, today_open=102.0)
    signals = GapFillStrategy().generate_signals(df, "RELIANCE")
    sig = signals[0]
    gap_size = abs(sig.entry_price - sig.target_1)
    sl_distance = abs(sig.stop_loss - sig.entry_price)
    assert sl_distance == pytest.approx(gap_size * 0.5, rel=0.01)


# ─── One signal per call + metadata ───

def test_returns_only_one_signal_on_multiple_gap_days():
    from strategies.gap_fill import GapFillStrategy
    day1 = make_day(datetime(2026, 1, 5), [(0, 100, 101, 99, 100, 5000)])
    day2 = make_day(datetime(2026, 1, 6), [(0, 103, 104, 102, 103, 3000)])
    day3 = make_day(datetime(2026, 1, 7), [(0, 106, 107, 105, 106, 3000)])
    df = pd.concat([day1, day2, day3])
    signals = GapFillStrategy().generate_signals(df, "RELIANCE")
    assert len(signals) == 1


def test_signal_strategy_name():
    from strategies.gap_fill import GapFillStrategy
    df = two_day_df(prev_close=100.0, today_open=102.0)
    signals = GapFillStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].strategy == "GAP_FILL"
