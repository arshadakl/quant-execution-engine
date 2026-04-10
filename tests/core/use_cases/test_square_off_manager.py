"""Tests for Square-off Manager."""
import pytest
from datetime import datetime, time
from unittest.mock import MagicMock, call


def _mock_paper_trader(open_trades: list) -> MagicMock:
    pt = MagicMock()
    pt.open_trades.return_value = open_trades
    return pt


def _open_trade(trade_id: int = 1, symbol: str = "RELIANCE") -> dict:
    return {"id": trade_id, "symbol": symbol, "qty": 10,
            "entry_price": 500.0, "direction": "LONG"}


def _ltp(symbol: str = "RELIANCE", price: float = 510.0) -> dict:
    return {symbol: price}


# ─── Instantiation ───

def test_instantiates_with_defaults():
    from core.use_cases.square_off_manager import SquareOffManager
    mgr = SquareOffManager()
    assert mgr.cutoff_time == time(15, 10)


def test_instantiates_with_custom_cutoff():
    from core.use_cases.square_off_manager import SquareOffManager
    mgr = SquareOffManager(cutoff_time=time(15, 0))
    assert mgr.cutoff_time == time(15, 0)


# ─── should_square_off ───

def test_should_square_off_after_cutoff():
    from core.use_cases.square_off_manager import SquareOffManager
    mgr = SquareOffManager(cutoff_time=time(15, 10))
    assert mgr.should_square_off(datetime(2026, 1, 2, 15, 11)) is True


def test_should_not_square_off_before_cutoff():
    from core.use_cases.square_off_manager import SquareOffManager
    mgr = SquareOffManager(cutoff_time=time(15, 10))
    assert mgr.should_square_off(datetime(2026, 1, 2, 14, 30)) is False


def test_should_square_off_exactly_at_cutoff():
    from core.use_cases.square_off_manager import SquareOffManager
    mgr = SquareOffManager(cutoff_time=time(15, 10))
    assert mgr.should_square_off(datetime(2026, 1, 2, 15, 10)) is True


# ─── close_all ───

def test_close_all_calls_close_on_each_open_trade():
    from core.use_cases.square_off_manager import SquareOffManager
    mgr = SquareOffManager()
    trades = [_open_trade(1, "RELIANCE"), _open_trade(2, "TCS")]
    ltp_map = {"RELIANCE": 510.0, "TCS": 3100.0}
    pt = _mock_paper_trader(trades)
    now = datetime(2026, 1, 2, 15, 11)
    mgr.close_all(paper_trader=pt, ltp_map=ltp_map, now=now)
    assert pt.close_trade.call_count == 2


def test_close_all_uses_ltp_for_each_symbol():
    from core.use_cases.square_off_manager import SquareOffManager
    mgr = SquareOffManager()
    trades = [_open_trade(1, "RELIANCE")]
    ltp_map = {"RELIANCE": 512.0}
    pt = _mock_paper_trader(trades)
    now = datetime(2026, 1, 2, 15, 11)
    mgr.close_all(paper_trader=pt, ltp_map=ltp_map, now=now)
    pt.close_trade.assert_called_once_with(
        trade_id=1, exit_price=512.0, exit_time=now
    )


def test_close_all_with_no_open_trades_is_noop():
    from core.use_cases.square_off_manager import SquareOffManager
    mgr = SquareOffManager()
    pt = _mock_paper_trader([])
    mgr.close_all(paper_trader=pt, ltp_map={}, now=datetime(2026, 1, 2, 15, 11))
    pt.close_trade.assert_not_called()


def test_close_all_uses_entry_price_when_ltp_missing():
    from core.use_cases.square_off_manager import SquareOffManager
    mgr = SquareOffManager()
    trades = [_open_trade(1, "RELIANCE")]  # entry_price=500
    pt = _mock_paper_trader(trades)
    # ltp_map has no RELIANCE → should fall back to entry_price
    now = datetime(2026, 1, 2, 15, 11)
    mgr.close_all(paper_trader=pt, ltp_map={}, now=now)
    pt.close_trade.assert_called_once_with(
        trade_id=1, exit_price=500.0, exit_time=now
    )


def test_close_all_returns_count_of_closed_trades():
    from core.use_cases.square_off_manager import SquareOffManager
    mgr = SquareOffManager()
    trades = [_open_trade(1), _open_trade(2), _open_trade(3)]
    pt = _mock_paper_trader(trades)
    ltp_map = {"RELIANCE": 510.0}
    count = mgr.close_all(paper_trader=pt, ltp_map=ltp_map,
                          now=datetime(2026, 1, 2, 15, 11))
    assert count == 3


# ─── Return type ───

def test_should_square_off_returns_bool():
    from core.use_cases.square_off_manager import SquareOffManager
    mgr = SquareOffManager()
    result = mgr.should_square_off(datetime(2026, 1, 2, 10, 0))
    assert type(result) is bool
