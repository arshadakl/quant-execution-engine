"""Tests for ORB (Opening Range Breakout) strategy."""
import pytest
import pandas as pd
from datetime import datetime


def make_df(rows: list[tuple]) -> pd.DataFrame:
    """rows: [(datetime, open, high, low, close, volume)]"""
    idx = [r[0] for r in rows]
    return pd.DataFrame(
        [{"open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]}
         for r in rows],
        index=idx,
    )


def dt(h: int, m: int) -> datetime:
    return datetime(2026, 1, 2, h, m)


# Opening range = 09:15–09:29 (first 15 min), range_high=105, range_low=98
OPENING_RANGE = [
    (dt(9, 15), 100, 105, 98, 102, 5000),
    (dt(9, 20), 102, 104, 99, 103, 4000),
    (dt(9, 25), 103, 105, 98, 101, 3500),
]

# ─── Instantiation ───

def test_orb_instantiates_with_default_params():
    from strategies.orb import ORBStrategy
    s = ORBStrategy()
    assert s.params["opening_range_minutes"] == 15
    assert s.params["breakout_buffer_pct"] == 0.001
    assert s.params["target_multiplier"] == 2.0


def test_orb_is_i_strategy():
    from strategies.orb import ORBStrategy
    from core.interfaces.i_strategy import IStrategy
    assert isinstance(ORBStrategy(), IStrategy)


def test_orb_name():
    from strategies.orb import ORBStrategy
    assert ORBStrategy().name == "ORB"


# ─── No signal cases ───

def test_no_signal_when_df_empty():
    from strategies.orb import ORBStrategy
    result = ORBStrategy().generate_signals(pd.DataFrame(), "RELIANCE")
    assert result == []


def test_no_signal_when_only_opening_range_bars():
    from strategies.orb import ORBStrategy
    df = make_df(OPENING_RANGE)
    result = ORBStrategy().generate_signals(df, "RELIANCE")
    assert result == []


def test_no_signal_when_price_stays_within_range():
    from strategies.orb import ORBStrategy
    df = make_df(OPENING_RANGE + [
        (dt(9, 30), 101, 104, 99, 102, 3000),
        (dt(9, 35), 102, 104, 100, 103, 2800),
    ])
    result = ORBStrategy().generate_signals(df, "RELIANCE")
    assert result == []


# ─── LONG signal ───

def test_long_signal_on_breakout_above_range_high():
    from strategies.orb import ORBStrategy
    # range_high=105, buffer=0.1% → breakout level ≈ 105.105
    df = make_df(OPENING_RANGE + [
        (dt(9, 30), 105, 106, 104, 105.2, 6000),  # close > 105.105 → LONG
    ])
    signals = ORBStrategy().generate_signals(df, "RELIANCE")
    assert len(signals) == 1
    assert signals[0].direction == "LONG"


def test_long_signal_entry_price_is_breakout_close():
    from strategies.orb import ORBStrategy
    df = make_df(OPENING_RANGE + [
        (dt(9, 30), 105, 106, 104, 105.5, 6000),
    ])
    signals = ORBStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].entry_price == pytest.approx(105.5)


def test_long_signal_sl_is_range_low():
    from strategies.orb import ORBStrategy
    df = make_df(OPENING_RANGE + [
        (dt(9, 30), 105, 106, 104, 105.5, 6000),
    ])
    signals = ORBStrategy().generate_signals(df, "RELIANCE")
    # SL = range_low = 98
    assert signals[0].stop_loss == pytest.approx(98.0)


def test_long_signal_target_uses_multiplier():
    from strategies.orb import ORBStrategy
    # range = 105 - 98 = 7; target = 105.5 + 7*2 = 119.5
    df = make_df(OPENING_RANGE + [
        (dt(9, 30), 105, 106, 104, 105.5, 6000),
    ])
    signals = ORBStrategy().generate_signals(df, "RELIANCE")
    expected_target = 105.5 + (105 - 98) * 2.0
    assert signals[0].target_1 == pytest.approx(expected_target)


# ─── SHORT signal ───

def test_short_signal_on_breakdown_below_range_low():
    from strategies.orb import ORBStrategy
    # range_low=98, buffer=0.1% → breakdown level ≈ 97.902
    df = make_df(OPENING_RANGE + [
        (dt(9, 30), 99, 100, 97, 97.8, 6000),  # close < 97.902 → SHORT
    ])
    signals = ORBStrategy().generate_signals(df, "RELIANCE")
    assert len(signals) == 1
    assert signals[0].direction == "SHORT"


def test_short_signal_sl_is_range_high():
    from strategies.orb import ORBStrategy
    df = make_df(OPENING_RANGE + [
        (dt(9, 30), 99, 100, 97, 97.5, 6000),
    ])
    signals = ORBStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].stop_loss == pytest.approx(105.0)


def test_short_signal_target_uses_multiplier():
    from strategies.orb import ORBStrategy
    # range=7; target = 97.5 - 7*2 = 83.5
    df = make_df(OPENING_RANGE + [
        (dt(9, 30), 99, 100, 97, 97.5, 6000),
    ])
    signals = ORBStrategy().generate_signals(df, "RELIANCE")
    expected_target = 97.5 - (105 - 98) * 2.0
    assert signals[0].target_1 == pytest.approx(expected_target)


# ─── One signal per day ───

def test_only_first_breakout_signal_returned():
    from strategies.orb import ORBStrategy
    df = make_df(OPENING_RANGE + [
        (dt(9, 30), 105, 106, 104, 105.5, 6000),   # LONG breakout
        (dt(9, 35), 106, 108, 97, 97.0, 8000),     # also breaks down — ignored
    ])
    signals = ORBStrategy().generate_signals(df, "RELIANCE")
    assert len(signals) == 1


def test_signal_strategy_name_is_orb():
    from strategies.orb import ORBStrategy
    df = make_df(OPENING_RANGE + [
        (dt(9, 30), 105, 106, 104, 105.5, 6000),
    ])
    signals = ORBStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].strategy == "ORB"
