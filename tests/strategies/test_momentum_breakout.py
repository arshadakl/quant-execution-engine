"""Tests for Momentum Breakout strategy."""
import pytest
import pandas as pd
from datetime import datetime, timedelta


def dt(m: int) -> datetime:
    """Return a datetime offset by m minutes from 09:15."""
    return datetime(2026, 1, 2, 9, 15) + timedelta(minutes=m)


def make_df(rows: list[tuple]) -> pd.DataFrame:
    idx = [r[0] for r in rows]
    return pd.DataFrame(
        [{"open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]}
         for r in rows],
        index=idx,
    )


def flat_bars(n: int, price: float = 100.0, volume: int = 1000) -> list[tuple]:
    """n flat bars near price with normal volume."""
    return [(dt(i * 5), price, price + 1, price - 1, price, volume) for i in range(n)]


# ─── Instantiation ───

def test_instantiates_with_defaults():
    from strategies.momentum_breakout import MomentumBreakoutStrategy
    s = MomentumBreakoutStrategy()
    assert s.params["lookback_bars"] == 20
    assert s.params["volume_multiplier"] == 1.5
    assert s.params["target_multiplier"] == 2.0


def test_is_i_strategy():
    from strategies.momentum_breakout import MomentumBreakoutStrategy
    from core.interfaces.i_strategy import IStrategy
    assert isinstance(MomentumBreakoutStrategy(), IStrategy)


def test_name():
    from strategies.momentum_breakout import MomentumBreakoutStrategy
    assert MomentumBreakoutStrategy().name == "MOMENTUM_BREAKOUT"


# ─── No signal ───

def test_no_signal_empty_df():
    from strategies.momentum_breakout import MomentumBreakoutStrategy
    assert MomentumBreakoutStrategy().generate_signals(pd.DataFrame(), "RELIANCE") == []


def test_no_signal_insufficient_bars():
    from strategies.momentum_breakout import MomentumBreakoutStrategy
    # Only 5 bars, lookback=20 → not enough history
    df = make_df(flat_bars(5))
    assert MomentumBreakoutStrategy().generate_signals(df, "RELIANCE") == []


def test_no_signal_breakout_without_volume_confirmation():
    from strategies.momentum_breakout import MomentumBreakoutStrategy
    # Price breaks out but volume is normal (not elevated)
    rows = flat_bars(21, price=100.0, volume=1000)
    rows.append((dt(110), 105, 110, 104, 109.0, 1200))  # breakout, low volume
    df = make_df(rows)
    signals = MomentumBreakoutStrategy().generate_signals(df, "RELIANCE")
    assert signals == []


def test_no_signal_when_price_stays_in_range():
    from strategies.momentum_breakout import MomentumBreakoutStrategy
    rows = flat_bars(22, price=100.0, volume=1000)
    df = make_df(rows)
    assert MomentumBreakoutStrategy().generate_signals(df, "RELIANCE") == []


# ─── LONG signal ───

def test_long_signal_on_high_volume_breakout():
    from strategies.momentum_breakout import MomentumBreakoutStrategy
    rows = flat_bars(21, price=100.0, volume=1000)
    # close > highest high of last 20 bars (101) AND volume > avg*1.5 (1500)
    rows.append((dt(110), 101, 112, 100, 111.0, 2500))
    df = make_df(rows)
    signals = MomentumBreakoutStrategy().generate_signals(df, "RELIANCE")
    assert len(signals) == 1
    assert signals[0].direction == "LONG"


def test_long_entry_is_close():
    from strategies.momentum_breakout import MomentumBreakoutStrategy
    rows = flat_bars(21, price=100.0, volume=1000)
    rows.append((dt(110), 101, 112, 100, 111.0, 2500))
    df = make_df(rows)
    signals = MomentumBreakoutStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].entry_price == pytest.approx(111.0)


def test_long_sl_is_lookback_low():
    from strategies.momentum_breakout import MomentumBreakoutStrategy
    rows = flat_bars(21, price=100.0, volume=1000)
    rows.append((dt(110), 101, 112, 100, 111.0, 2500))
    df = make_df(rows)
    signals = MomentumBreakoutStrategy().generate_signals(df, "RELIANCE")
    # SL = lowest low of last 20 bars = 100 - 1 = 99
    assert signals[0].stop_loss == pytest.approx(99.0)


def test_long_target_uses_multiplier():
    from strategies.momentum_breakout import MomentumBreakoutStrategy
    rows = flat_bars(21, price=100.0, volume=1000)
    rows.append((dt(110), 101, 112, 100, 111.0, 2500))
    df = make_df(rows)
    signals = MomentumBreakoutStrategy().generate_signals(df, "RELIANCE")
    sig = signals[0]
    risk = sig.entry_price - sig.stop_loss
    expected_target = sig.entry_price + risk * 2.0
    assert sig.target_1 == pytest.approx(expected_target, rel=0.001)


# ─── SHORT signal ───

def test_short_signal_on_high_volume_breakdown():
    from strategies.momentum_breakout import MomentumBreakoutStrategy
    rows = flat_bars(21, price=100.0, volume=1000)
    # close < lowest low of last 20 bars (99) AND high volume
    rows.append((dt(110), 99, 100, 88, 89.0, 2500))
    df = make_df(rows)
    signals = MomentumBreakoutStrategy().generate_signals(df, "RELIANCE")
    assert len(signals) == 1
    assert signals[0].direction == "SHORT"


def test_short_sl_is_lookback_high():
    from strategies.momentum_breakout import MomentumBreakoutStrategy
    rows = flat_bars(21, price=100.0, volume=1000)
    rows.append((dt(110), 99, 100, 88, 89.0, 2500))
    df = make_df(rows)
    signals = MomentumBreakoutStrategy().generate_signals(df, "RELIANCE")
    # SL = highest high of last 20 bars = 101
    assert signals[0].stop_loss == pytest.approx(101.0)


def test_short_target_below_entry():
    from strategies.momentum_breakout import MomentumBreakoutStrategy
    rows = flat_bars(21, price=100.0, volume=1000)
    rows.append((dt(110), 99, 100, 88, 89.0, 2500))
    df = make_df(rows)
    signals = MomentumBreakoutStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].target_1 < signals[0].entry_price


# ─── One signal per session ───

def test_only_first_signal_returned():
    from strategies.momentum_breakout import MomentumBreakoutStrategy
    rows = flat_bars(21, price=100.0, volume=1000)
    rows.append((dt(110), 101, 112, 100, 111.0, 2500))   # LONG breakout
    rows.append((dt(115), 110, 111, 88, 89.0, 3000))     # also breaks down — ignored
    df = make_df(rows)
    signals = MomentumBreakoutStrategy().generate_signals(df, "RELIANCE")
    assert len(signals) == 1


def test_signal_strategy_name():
    from strategies.momentum_breakout import MomentumBreakoutStrategy
    rows = flat_bars(21, price=100.0, volume=1000)
    rows.append((dt(110), 101, 112, 100, 111.0, 2500))
    df = make_df(rows)
    signals = MomentumBreakoutStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].strategy == "MOMENTUM_BREAKOUT"
