"""Tests for VWAP Reversion strategy."""
import pytest
import pandas as pd
from datetime import datetime


def dt(h: int, m: int) -> datetime:
    return datetime(2026, 1, 2, h, m)


def make_df(rows: list[tuple]) -> pd.DataFrame:
    idx = [r[0] for r in rows]
    return pd.DataFrame(
        [{"open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]}
         for r in rows],
        index=idx,
    )


# ─── Instantiation ───

def test_vwap_instantiates_with_defaults():
    from strategies.vwap_reversion import VWAPReversionStrategy
    s = VWAPReversionStrategy()
    assert s.params["deviation_pct"] == 0.015
    assert s.params["target_multiplier"] == 1.5


def test_vwap_is_i_strategy():
    from strategies.vwap_reversion import VWAPReversionStrategy
    from core.interfaces.i_strategy import IStrategy
    assert isinstance(VWAPReversionStrategy(), IStrategy)


def test_vwap_name():
    from strategies.vwap_reversion import VWAPReversionStrategy
    assert VWAPReversionStrategy().name == "VWAP_REVERSION"


# ─── VWAP calculation ───

def test_vwap_computed_correctly():
    """Verify VWAP = sum(typical_price * volume) / sum(volume)."""
    from strategies.vwap_reversion import compute_vwap
    df = make_df([
        (dt(9, 15), 100, 102, 98, 100, 1000),   # typical = 100, contrib=100000
        (dt(9, 20), 100, 104, 99, 102, 2000),   # typical = 101.67, contrib=203333
    ])
    vwap = compute_vwap(df)
    # manual: tp1=(102+98+100)/3=100, tp2=(104+99+102)/3=101.67
    # vwap = (100*1000 + 101.67*2000) / 3000
    expected = (100 * 1000 + (104 + 99 + 102) / 3 * 2000) / 3000
    assert vwap.iloc[-1] == pytest.approx(expected, rel=0.001)


# ─── No signal ───

def test_no_signal_empty_df():
    from strategies.vwap_reversion import VWAPReversionStrategy
    assert VWAPReversionStrategy().generate_signals(pd.DataFrame(), "RELIANCE") == []


def test_no_signal_when_price_near_vwap():
    from strategies.vwap_reversion import VWAPReversionStrategy
    # All bars close to VWAP — no deviation beyond 1.5%
    df = make_df([
        (dt(9, 15), 100, 101, 99, 100, 5000),
        (dt(9, 20), 100, 101, 99, 100.5, 4000),
        (dt(9, 25), 100, 101, 99, 100.2, 4500),
    ])
    assert VWAPReversionStrategy().generate_signals(df, "RELIANCE") == []


# ─── LONG signal (price below VWAP) ───

def test_long_signal_when_close_below_vwap_by_deviation():
    from strategies.vwap_reversion import VWAPReversionStrategy
    # Build df where VWAP ≈ 100 then price drops sharply
    df = make_df([
        (dt(9, 15), 100, 101, 99, 100, 10000),
        (dt(9, 20), 100, 101, 99, 100, 10000),
        (dt(9, 25), 100, 101, 99, 100, 10000),
        (dt(9, 30), 98,  98,  97, 97.5, 5000),  # close ~2.5% below vwap ≈100
    ])
    signals = VWAPReversionStrategy().generate_signals(df, "RELIANCE")
    assert len(signals) == 1
    assert signals[0].direction == "LONG"


def test_long_entry_is_close_price():
    from strategies.vwap_reversion import VWAPReversionStrategy
    df = make_df([
        (dt(9, 15), 100, 101, 99, 100, 10000),
        (dt(9, 20), 100, 101, 99, 100, 10000),
        (dt(9, 25), 100, 101, 99, 100, 10000),
        (dt(9, 30), 97,  97,  96, 97.0, 5000),
    ])
    signals = VWAPReversionStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].entry_price == pytest.approx(97.0)


def test_long_sl_below_entry_by_deviation_distance():
    from strategies.vwap_reversion import VWAPReversionStrategy
    df = make_df([
        (dt(9, 15), 100, 101, 99, 100, 10000),
        (dt(9, 20), 100, 101, 99, 100, 10000),
        (dt(9, 25), 100, 101, 99, 100, 10000),
        (dt(9, 30), 97,  97,  96, 97.0, 5000),
    ])
    signals = VWAPReversionStrategy().generate_signals(df, "RELIANCE")
    sig = signals[0]
    # deviation_distance = vwap - close; SL = close - deviation_distance
    assert sig.stop_loss < sig.entry_price


def test_long_target_above_entry():
    from strategies.vwap_reversion import VWAPReversionStrategy
    df = make_df([
        (dt(9, 15), 100, 101, 99, 100, 10000),
        (dt(9, 20), 100, 101, 99, 100, 10000),
        (dt(9, 25), 100, 101, 99, 100, 10000),
        (dt(9, 30), 97,  97,  96, 97.0, 5000),
    ])
    signals = VWAPReversionStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].target_1 > signals[0].entry_price


# ─── SHORT signal (price above VWAP) ───

def test_short_signal_when_close_above_vwap_by_deviation():
    from strategies.vwap_reversion import VWAPReversionStrategy
    df = make_df([
        (dt(9, 15), 100, 101, 99, 100, 10000),
        (dt(9, 20), 100, 101, 99, 100, 10000),
        (dt(9, 25), 100, 101, 99, 100, 10000),
        (dt(9, 30), 103, 104, 102, 103.0, 5000),  # close ~3% above vwap ≈100
    ])
    signals = VWAPReversionStrategy().generate_signals(df, "RELIANCE")
    assert len(signals) == 1
    assert signals[0].direction == "SHORT"


def test_short_sl_above_entry():
    from strategies.vwap_reversion import VWAPReversionStrategy
    df = make_df([
        (dt(9, 15), 100, 101, 99, 100, 10000),
        (dt(9, 20), 100, 101, 99, 100, 10000),
        (dt(9, 25), 100, 101, 99, 100, 10000),
        (dt(9, 30), 103, 104, 102, 103.0, 5000),
    ])
    signals = VWAPReversionStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].stop_loss > signals[0].entry_price


def test_short_target_below_entry():
    from strategies.vwap_reversion import VWAPReversionStrategy
    df = make_df([
        (dt(9, 15), 100, 101, 99, 100, 10000),
        (dt(9, 20), 100, 101, 99, 100, 10000),
        (dt(9, 25), 100, 101, 99, 100, 10000),
        (dt(9, 30), 103, 104, 102, 103.0, 5000),
    ])
    signals = VWAPReversionStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].target_1 < signals[0].entry_price


# ─── One signal per session ───

def test_returns_only_first_signal():
    from strategies.vwap_reversion import VWAPReversionStrategy
    df = make_df([
        (dt(9, 15), 100, 101, 99, 100, 10000),
        (dt(9, 20), 100, 101, 99, 100, 10000),
        (dt(9, 25), 100, 101, 99, 100, 10000),
        (dt(9, 30), 97,  97,  96, 97.0, 5000),   # LONG signal
        (dt(9, 35), 103, 104, 102, 103.0, 5000),  # would be SHORT — ignored
    ])
    signals = VWAPReversionStrategy().generate_signals(df, "RELIANCE")
    assert len(signals) == 1


def test_signal_strategy_name():
    from strategies.vwap_reversion import VWAPReversionStrategy
    df = make_df([
        (dt(9, 15), 100, 101, 99, 100, 10000),
        (dt(9, 20), 100, 101, 99, 100, 10000),
        (dt(9, 25), 100, 101, 99, 100, 10000),
        (dt(9, 30), 97,  97,  96, 97.0, 5000),
    ])
    signals = VWAPReversionStrategy().generate_signals(df, "RELIANCE")
    assert signals[0].strategy == "VWAP_REVERSION"
