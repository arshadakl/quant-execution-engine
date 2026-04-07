"""Tests for TradeSimulator — fill simulation with Indian market charges."""
import pytest
import pandas as pd
from datetime import datetime
from core.entities.signal import Signal


def make_signal(direction="LONG", entry=100.0, sl=95.0, target=110.0):
    return Signal(
        strategy="test",
        symbol="RELIANCE",
        direction=direction,
        entry_price=entry,
        stop_loss=sl if direction == "LONG" else sl + 2 * (entry - sl),
        target_1=target,
        timestamp=datetime(2026, 1, 2, 9, 15),
    )


def make_df(rows: list[tuple]) -> pd.DataFrame:
    """rows: [(time_str, open, high, low, close, volume), ...]"""
    idx = [datetime.strptime(r[0], "%H:%M") for r in rows]
    idx = [t.replace(year=2026, month=1, day=2) for t in idx]
    return pd.DataFrame(
        [{"open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]}
         for r in rows],
        index=idx,
    )


# ─── TradeCharges ───

def test_charges_total_sums_all_fields():
    from backtester.charges import TradeCharges
    c = TradeCharges(brokerage=20, stt=12.5, exchange_charges=3.25,
                     gst=4.19, sebi_charges=0.1, stamp_duty=1.5)
    assert abs(c.total - (20 + 12.5 + 3.25 + 4.19 + 0.1 + 1.5)) < 0.01


def test_charges_is_frozen():
    from backtester.charges import TradeCharges
    c = TradeCharges(brokerage=20, stt=12.5, exchange_charges=3.25,
                     gst=4.19, sebi_charges=0.1, stamp_duty=1.5)
    with pytest.raises((AttributeError, TypeError)):
        c.brokerage = 0


# ─── calculate_charges ───

def test_brokerage_capped_at_20_per_side():
    from backtester.charges import calculate_charges
    # 1000 shares at ₹500 = ₹5,00,000 turnover → 0.03% = ₹150, capped at ₹20 each side
    c = calculate_charges(entry_price=500.0, exit_price=510.0, qty=1000)
    assert c.brokerage == pytest.approx(40.0, abs=0.01)  # ₹20 × 2 sides


def test_brokerage_below_cap_uses_percentage():
    from backtester.charges import calculate_charges
    # 1 share at ₹100 = ₹100 turnover → 0.03% = ₹0.03 < ₹20, so use percentage
    c = calculate_charges(entry_price=100.0, exit_price=100.0, qty=1)
    assert c.brokerage < 20.0


def test_stt_charged_on_sell_side_only_intraday():
    from backtester.charges import calculate_charges
    # STT = 0.025% of sell turnover only
    c = calculate_charges(entry_price=100.0, exit_price=110.0, qty=100)
    sell_turnover = 110.0 * 100
    expected_stt = sell_turnover * 0.00025
    assert c.stt == pytest.approx(expected_stt, rel=0.01)


def test_gst_is_18_percent_of_brokerage_plus_exchange_sebi():
    from backtester.charges import calculate_charges
    c = calculate_charges(entry_price=100.0, exit_price=100.0, qty=100)
    expected_gst = (c.brokerage + c.exchange_charges + c.sebi_charges) * 0.18
    assert c.gst == pytest.approx(expected_gst, rel=0.01)


def test_stamp_duty_on_buy_side_only():
    from backtester.charges import calculate_charges
    # Stamp duty = 0.015% of buy turnover
    c = calculate_charges(entry_price=200.0, exit_price=210.0, qty=50)
    buy_turnover = 200.0 * 50
    expected_stamp = buy_turnover * 0.00015
    assert c.stamp_duty == pytest.approx(expected_stamp, rel=0.01)


# ─── TradeSimulator ───

def test_simulate_long_exits_at_target():
    from backtester.trade_simulator import TradeSimulator
    sig = make_signal("LONG", entry=100.0, sl=95.0, target=110.0)
    df = make_df([
        ("09:15", 100.0, 101.0, 99.0, 100.5, 1000),   # signal bar
        ("09:16", 100.5, 101.0, 99.5, 100.8, 900),    # entry bar
        ("09:17", 101.0, 109.0, 100.5, 108.0, 1100),  # no exit yet
        ("09:18", 108.0, 112.0, 107.5, 111.0, 1200),  # high > 110 → target hit
    ])
    trade = TradeSimulator().simulate(sig, df, qty=10)
    assert trade is not None
    assert trade.exit_price == pytest.approx(110.0, abs=0.01)
    assert trade.direction == "LONG"


def test_simulate_long_exits_at_stop_loss():
    from backtester.trade_simulator import TradeSimulator
    sig = make_signal("LONG", entry=100.0, sl=95.0, target=110.0)
    df = make_df([
        ("09:15", 100.0, 101.0, 99.0, 100.5, 1000),
        ("09:16", 100.5, 101.0, 99.5, 100.8, 900),
        ("09:17", 100.0, 100.5, 93.0, 94.0, 1100),   # low < 95 → SL hit
    ])
    trade = TradeSimulator().simulate(sig, df, qty=10)
    assert trade is not None
    assert trade.exit_price == pytest.approx(95.0, abs=0.01)


def test_simulate_long_exits_at_end_of_data():
    from backtester.trade_simulator import TradeSimulator
    sig = make_signal("LONG", entry=100.0, sl=95.0, target=110.0)
    df = make_df([
        ("09:15", 100.0, 101.0, 99.0, 100.5, 1000),
        ("09:16", 100.5, 101.0, 99.5, 100.8, 900),
        ("09:17", 101.0, 103.0, 100.5, 102.0, 800),  # no exit — end of data
    ])
    trade = TradeSimulator().simulate(sig, df, qty=10)
    assert trade is not None
    assert trade.exit_price == pytest.approx(102.0, abs=0.01)  # last close


def test_simulate_short_exits_at_target():
    from backtester.trade_simulator import TradeSimulator
    sig = make_signal("SHORT", entry=100.0, sl=92.0, target=90.0)
    # For SHORT: sl must be above entry → fix signal manually
    from core.entities.signal import Signal
    sig = Signal(strategy="test", symbol="RELIANCE", direction="SHORT",
                 entry_price=100.0, stop_loss=105.0, target_1=90.0,
                 timestamp=datetime(2026, 1, 2, 9, 15))
    df = make_df([
        ("09:15", 100.0, 101.0, 99.0, 100.5, 1000),
        ("09:16", 100.5, 101.0, 99.5, 100.2, 900),
        ("09:17", 100.0, 100.5, 88.0, 89.0, 1100),  # low < 90 → target hit
    ])
    trade = TradeSimulator().simulate(sig, df, qty=10)
    assert trade is not None
    assert trade.exit_price == pytest.approx(90.0, abs=0.01)


def test_simulate_short_exits_at_stop_loss():
    from backtester.trade_simulator import TradeSimulator
    from core.entities.signal import Signal
    sig = Signal(strategy="test", symbol="RELIANCE", direction="SHORT",
                 entry_price=100.0, stop_loss=105.0, target_1=90.0,
                 timestamp=datetime(2026, 1, 2, 9, 15))
    df = make_df([
        ("09:15", 100.0, 101.0, 99.0, 100.5, 1000),
        ("09:16", 100.5, 101.0, 99.5, 100.2, 900),
        ("09:17", 103.0, 107.0, 102.0, 106.0, 800),  # high > 105 → SL hit
    ])
    trade = TradeSimulator().simulate(sig, df, qty=10)
    assert trade is not None
    assert trade.exit_price == pytest.approx(105.0, abs=0.01)


def test_simulate_returns_none_when_all_bars_before_signal():
    from backtester.trade_simulator import TradeSimulator
    sig = make_signal()  # timestamp = 09:15
    # all df bars are before signal timestamp → no entry possible
    df = make_df([("09:10", 100.0, 101.0, 99.0, 100.5, 1000),
                  ("09:11", 100.5, 101.5, 99.5, 101.0, 900)])
    trade = TradeSimulator().simulate(sig, df, qty=10)
    assert trade is None


def test_simulated_trade_gross_pnl_long():
    from backtester.trade_simulator import TradeSimulator
    sig = make_signal("LONG", entry=100.0, sl=95.0, target=110.0)
    df = make_df([
        ("09:15", 100.0, 101.0, 99.0, 100.5, 1000),
        ("09:16", 100.0, 101.0, 99.5, 100.8, 900),
        ("09:17", 101.0, 112.0, 100.5, 111.0, 1200),
    ])
    trade = TradeSimulator().simulate(sig, df, qty=10)
    assert trade is not None
    assert trade.gross_pnl == pytest.approx((trade.exit_price - trade.entry_price) * 10, abs=0.1)


def test_simulated_trade_net_pnl_less_than_gross():
    from backtester.trade_simulator import TradeSimulator
    sig = make_signal("LONG", entry=100.0, sl=95.0, target=110.0)
    df = make_df([
        ("09:15", 100.0, 101.0, 99.0, 100.5, 1000),
        ("09:16", 100.0, 101.0, 99.5, 100.8, 900),
        ("09:17", 101.0, 112.0, 100.5, 111.0, 1200),
    ])
    trade = TradeSimulator().simulate(sig, df, qty=10)
    assert trade is not None
    assert trade.net_pnl < trade.gross_pnl
