"""Tests for EMA Crossover strategy."""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def dt(m: int) -> datetime:
    return datetime(2026, 1, 2, 9, 15) + timedelta(minutes=m * 5)


def make_df(closes: list[float], volume: int = 1000) -> pd.DataFrame:
    idx = [dt(i) for i in range(len(closes))]
    return pd.DataFrame(
        [{"open": c - 0.5, "high": c + 1, "low": c - 1, "close": c, "volume": volume}
         for c in closes],
        index=idx,
    )


def trending_then_cross(n_down: int = 30, n_up: int = 10) -> pd.DataFrame:
    """n_down bars of slow downtrend → n_up bars of sharp uptrend forcing crossover."""
    down = [100 - i * 0.3 for i in range(n_down)]
    # sharp up from last down price to trigger fast EMA to cross above slow EMA
    last = down[-1]
    up = [last + i * 2.5 for i in range(1, n_up + 1)]
    return make_df(down + up)


def trending_then_cross_short(n_up: int = 30, n_down: int = 10) -> pd.DataFrame:
    """n_up bars of slow uptrend → n_down bars of sharp downtrend for SHORT signal."""
    up = [100 + i * 0.3 for i in range(n_up)]
    last = up[-1]
    down = [last - i * 2.5 for i in range(1, n_down + 1)]
    return make_df(up + down)


# ─── Instantiation ───

def test_instantiates_with_defaults():
    from strategies.ema_crossover import EMACrossoverStrategy
    s = EMACrossoverStrategy()
    assert s.params["fast_period"] == 9
    assert s.params["slow_period"] == 21
    assert s.params["target_multiplier"] == 2.0


def test_is_i_strategy():
    from strategies.ema_crossover import EMACrossoverStrategy
    from core.interfaces.i_strategy import IStrategy
    assert isinstance(EMACrossoverStrategy(), IStrategy)


def test_name():
    from strategies.ema_crossover import EMACrossoverStrategy
    assert EMACrossoverStrategy().name == "EMA_CROSSOVER"


# ─── compute_ema ───

def test_compute_ema_length_matches_series():
    from strategies.ema_crossover import compute_ema
    s = pd.Series([100.0] * 30)
    assert len(compute_ema(s, 9)) == 30


def test_compute_ema_flat_series_equals_constant():
    from strategies.ema_crossover import compute_ema
    s = pd.Series([100.0] * 30)
    ema = compute_ema(s, 9)
    assert abs(ema.iloc[-1] - 100.0) < 0.001


def test_compute_ema_rising_series_fast_above_slow():
    from strategies.ema_crossover import compute_ema
    s = pd.Series([float(i) for i in range(1, 51)])
    fast = compute_ema(s, 9)
    slow = compute_ema(s, 21)
    assert fast.iloc[-1] > slow.iloc[-1]


# ─── No signal ───

def test_no_signal_empty_df():
    from strategies.ema_crossover import EMACrossoverStrategy
    assert EMACrossoverStrategy().generate_signals(pd.DataFrame(), "RELIANCE") == []


def test_no_signal_insufficient_bars():
    from strategies.ema_crossover import EMACrossoverStrategy
    df = make_df([100.0] * 15)   # need > slow_period(21)
    assert EMACrossoverStrategy().generate_signals(df, "RELIANCE") == []


def test_no_signal_flat_price_no_crossover():
    from strategies.ema_crossover import EMACrossoverStrategy
    df = make_df([100.0] * 40)
    assert EMACrossoverStrategy().generate_signals(df, "RELIANCE") == []


# ─── LONG signal ───

def test_long_signal_on_bullish_crossover():
    from strategies.ema_crossover import EMACrossoverStrategy
    df = trending_then_cross()
    signals = EMACrossoverStrategy().generate_signals(df, "RELIANCE")
    assert len(signals) == 1
    assert signals[0].direction == "LONG"


def test_long_entry_is_close_at_crossover():
    from strategies.ema_crossover import EMACrossoverStrategy
    df = trending_then_cross()
    signals = EMACrossoverStrategy().generate_signals(df, "RELIANCE")
    # entry price must match one of the bar closes
    assert signals[0].entry_price in [round(c, 4) for c in df["close"].values]


def test_long_sl_below_entry():
    from strategies.ema_crossover import EMACrossoverStrategy
    df = trending_then_cross()
    signals = EMACrossoverStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].stop_loss < signals[0].entry_price


def test_long_target_above_entry():
    from strategies.ema_crossover import EMACrossoverStrategy
    df = trending_then_cross()
    signals = EMACrossoverStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].target_1 > signals[0].entry_price


def test_long_target_uses_multiplier():
    from strategies.ema_crossover import EMACrossoverStrategy
    df = trending_then_cross()
    signals = EMACrossoverStrategy().generate_signals(df, "RELIANCE")
    sig = signals[0]
    risk = sig.entry_price - sig.stop_loss
    assert sig.target_1 == pytest.approx(sig.entry_price + risk * 2.0, rel=0.01)


# ─── SHORT signal ───

def test_short_signal_on_bearish_crossover():
    from strategies.ema_crossover import EMACrossoverStrategy
    df = trending_then_cross_short()
    signals = EMACrossoverStrategy().generate_signals(df, "RELIANCE")
    assert len(signals) == 1
    assert signals[0].direction == "SHORT"


def test_short_sl_above_entry():
    from strategies.ema_crossover import EMACrossoverStrategy
    df = trending_then_cross_short()
    signals = EMACrossoverStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].stop_loss > signals[0].entry_price


def test_short_target_below_entry():
    from strategies.ema_crossover import EMACrossoverStrategy
    df = trending_then_cross_short()
    signals = EMACrossoverStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].target_1 < signals[0].entry_price


# ─── One signal per session + metadata ───

def test_only_first_signal_returned():
    from strategies.ema_crossover import EMACrossoverStrategy
    # Zigzag: multiple crossovers possible — only first returned
    zz = [100 - i * 0.5 for i in range(25)] + [100 + i * 3 for i in range(15)]
    df = make_df(zz)
    signals = EMACrossoverStrategy().generate_signals(df, "RELIANCE")
    assert len(signals) <= 1


def test_signal_strategy_name():
    from strategies.ema_crossover import EMACrossoverStrategy
    df = trending_then_cross()
    signals = EMACrossoverStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].strategy == "EMA_CROSSOVER"
