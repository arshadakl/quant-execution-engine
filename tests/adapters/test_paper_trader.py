"""Tests for Paper Trader."""
import pytest
import sqlite3
import os
from datetime import datetime
from core.entities.signal import Signal


def _make_signal(symbol: str = "RELIANCE", direction: str = "LONG") -> Signal:
    sl = 490.0 if direction == "LONG" else 510.0
    target = 520.0 if direction == "LONG" else 480.0
    return Signal(
        symbol=symbol,
        direction=direction,
        entry_price=500.0,
        stop_loss=sl,
        target_1=target,
        timestamp=datetime(2026, 1, 2, 10, 0),
        strategy="test_strategy",
    )


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "paper_trades.db")


# ─── Instantiation ───

def test_instantiates_with_db_path(db_path):
    from adapters.paper_trader import PaperTrader
    pt = PaperTrader(db_path=db_path, initial_capital=100_000.0)
    assert pt.capital == 100_000.0


def test_creates_db_on_init(db_path):
    from adapters.paper_trader import PaperTrader
    PaperTrader(db_path=db_path, initial_capital=100_000.0)
    assert os.path.exists(db_path)


def test_creates_trades_table(db_path):
    from adapters.paper_trader import PaperTrader
    PaperTrader(db_path=db_path, initial_capital=100_000.0)
    conn = sqlite3.connect(db_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert "trades" in tables


# ─── Fill on signal ───

def test_fill_long_signal(tmp_path):
    from adapters.paper_trader import PaperTrader
    pt = PaperTrader(db_path=str(tmp_path / "test.db"), initial_capital=100_000.0)
    sig = _make_signal("RELIANCE", "LONG")
    trade_id = pt.fill(signal=sig, qty=10, fill_price=500.0)
    assert trade_id is not None


def test_fill_short_signal(tmp_path):
    from adapters.paper_trader import PaperTrader
    pt = PaperTrader(db_path=str(tmp_path / "test.db"), initial_capital=100_000.0)
    sig = _make_signal("RELIANCE", "SHORT")
    trade_id = pt.fill(signal=sig, qty=10, fill_price=500.0)
    assert trade_id is not None


def test_fill_persists_to_db(db_path):
    from adapters.paper_trader import PaperTrader
    pt = PaperTrader(db_path=db_path, initial_capital=100_000.0)
    sig = _make_signal()
    pt.fill(signal=sig, qty=10, fill_price=500.0)
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT * FROM trades").fetchall()
    conn.close()
    assert len(rows) == 1


def test_fill_records_correct_symbol(db_path):
    from adapters.paper_trader import PaperTrader
    pt = PaperTrader(db_path=db_path, initial_capital=100_000.0)
    sig = _make_signal("TCS")
    pt.fill(signal=sig, qty=5, fill_price=3000.0)
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT symbol FROM trades").fetchone()
    conn.close()
    assert row[0] == "TCS"


# ─── Close trade ───

def test_close_trade_records_exit(db_path):
    from adapters.paper_trader import PaperTrader
    pt = PaperTrader(db_path=db_path, initial_capital=100_000.0)
    sig = _make_signal()
    trade_id = pt.fill(signal=sig, qty=10, fill_price=500.0)
    pt.close_trade(trade_id=trade_id, exit_price=520.0,
                   exit_time=datetime(2026, 1, 2, 11, 0))
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT exit_price, pnl FROM trades WHERE id=?", (trade_id,)
    ).fetchone()
    conn.close()
    assert row[0] == pytest.approx(520.0)
    assert row[1] == pytest.approx(200.0)  # (520-500)*10


def test_close_trade_negative_pnl(db_path):
    from adapters.paper_trader import PaperTrader
    pt = PaperTrader(db_path=db_path, initial_capital=100_000.0)
    sig = _make_signal()
    trade_id = pt.fill(signal=sig, qty=10, fill_price=500.0)
    pt.close_trade(trade_id=trade_id, exit_price=490.0,
                   exit_time=datetime(2026, 1, 2, 11, 0))
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT pnl FROM trades WHERE id=?", (trade_id,)).fetchone()
    conn.close()
    assert row[0] == pytest.approx(-100.0)  # (490-500)*10


def test_close_nonexistent_trade_raises(db_path):
    from adapters.paper_trader import PaperTrader
    pt = PaperTrader(db_path=db_path, initial_capital=100_000.0)
    with pytest.raises((KeyError, ValueError)):
        pt.close_trade(trade_id=999, exit_price=500.0,
                       exit_time=datetime(2026, 1, 2, 11, 0))


# ─── Day P&L ───

def test_day_pnl_zero_initially(db_path):
    from adapters.paper_trader import PaperTrader
    pt = PaperTrader(db_path=db_path, initial_capital=100_000.0)
    assert pt.day_pnl() == pytest.approx(0.0)


def test_day_pnl_accumulates_closed_trades(db_path):
    from adapters.paper_trader import PaperTrader
    pt = PaperTrader(db_path=db_path, initial_capital=100_000.0)
    sig1 = _make_signal("RELIANCE")
    sig2 = _make_signal("TCS")
    id1 = pt.fill(signal=sig1, qty=10, fill_price=500.0)
    id2 = pt.fill(signal=sig2, qty=5, fill_price=500.0)
    pt.close_trade(id1, exit_price=510.0, exit_time=datetime(2026, 1, 2, 11, 0))
    pt.close_trade(id2, exit_price=490.0, exit_time=datetime(2026, 1, 2, 11, 5))
    # pnl1 = 100, pnl2 = -50
    assert pt.day_pnl() == pytest.approx(50.0)


# ─── Open trades ───

def test_open_trades_returns_unfilled_exits(db_path):
    from adapters.paper_trader import PaperTrader
    pt = PaperTrader(db_path=db_path, initial_capital=100_000.0)
    sig = _make_signal()
    pt.fill(signal=sig, qty=10, fill_price=500.0)
    open_trades = pt.open_trades()
    assert len(open_trades) == 1


def test_open_trades_excludes_closed(db_path):
    from adapters.paper_trader import PaperTrader
    pt = PaperTrader(db_path=db_path, initial_capital=100_000.0)
    sig = _make_signal()
    trade_id = pt.fill(signal=sig, qty=10, fill_price=500.0)
    pt.close_trade(trade_id, exit_price=510.0, exit_time=datetime(2026, 1, 2, 11, 0))
    assert pt.open_trades() == []
