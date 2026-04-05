"""Tests for core entity dataclasses — all must be frozen and validated."""
import pytest
from datetime import datetime


# ─── Signal ───

def test_signal_creates_with_valid_data():
    from core.entities.signal import Signal
    sig = Signal(
        strategy="ORB",
        symbol="RELIANCE",
        direction="LONG",
        entry_price=2450.0,
        stop_loss=2430.0,
        target_1=2490.0,
        timestamp=datetime(2026, 1, 15, 9, 31),
        confidence=0.85,
    )
    assert sig.symbol == "RELIANCE"
    assert sig.direction == "LONG"
    assert sig.target_2 is None


def test_signal_is_frozen():
    from core.entities.signal import Signal
    sig = Signal(
        strategy="ORB", symbol="RELIANCE", direction="LONG",
        entry_price=2450.0, stop_loss=2430.0, target_1=2490.0,
        timestamp=datetime(2026, 1, 15, 9, 31),
    )
    with pytest.raises(Exception):  # FrozenInstanceError
        sig.symbol = "INFY"


def test_signal_rejects_invalid_direction():
    from core.entities.signal import Signal
    with pytest.raises(ValueError, match="direction"):
        Signal(
            strategy="ORB", symbol="RELIANCE", direction="SIDEWAYS",
            entry_price=2450.0, stop_loss=2430.0, target_1=2490.0,
            timestamp=datetime(2026, 1, 15, 9, 31),
        )


def test_signal_rejects_negative_entry_price():
    from core.entities.signal import Signal
    with pytest.raises(ValueError, match="entry_price"):
        Signal(
            strategy="ORB", symbol="RELIANCE", direction="LONG",
            entry_price=-100.0, stop_loss=2430.0, target_1=2490.0,
            timestamp=datetime(2026, 1, 15, 9, 31),
        )


def test_signal_rejects_confidence_out_of_range():
    from core.entities.signal import Signal
    with pytest.raises(ValueError, match="confidence"):
        Signal(
            strategy="ORB", symbol="RELIANCE", direction="LONG",
            entry_price=2450.0, stop_loss=2430.0, target_1=2490.0,
            timestamp=datetime(2026, 1, 15, 9, 31),
            confidence=1.5,
        )


# ─── Order ───

def test_order_creates_with_valid_data():
    from core.entities.order import Order, OrderStatus, OrderType, TransactionType
    order = Order(
        order_id="123456",
        symbol="RELIANCE",
        token="2885",
        transaction_type=TransactionType.BUY,
        order_type=OrderType.LIMIT,
        quantity=18,
        price=2450.0,
        trigger_price=None,
        status=OrderStatus.PENDING,
        timestamp=datetime(2026, 1, 15, 9, 31),
    )
    assert order.order_id == "123456"
    assert order.status == OrderStatus.PENDING


def test_order_is_frozen():
    from core.entities.order import Order, OrderStatus, OrderType, TransactionType
    order = Order(
        order_id="123456", symbol="RELIANCE", token="2885",
        transaction_type=TransactionType.BUY, order_type=OrderType.LIMIT,
        quantity=18, price=2450.0, trigger_price=None,
        status=OrderStatus.PENDING, timestamp=datetime(2026, 1, 15, 9, 31),
    )
    with pytest.raises(Exception):
        order.status = OrderStatus.FILLED


# ─── Trade ───

def test_trade_creates_open():
    from core.entities.trade import Trade
    trade = Trade(
        trade_id="T001",
        symbol="RELIANCE",
        strategy="ORB",
        direction="LONG",
        entry_price=2450.0,
        quantity=18,
        stop_loss=2430.0,
        target_1=2490.0,
        entry_time=datetime(2026, 1, 15, 9, 31),
    )
    assert trade.exit_price is None
    assert trade.pnl is None


def test_trade_is_frozen():
    from core.entities.trade import Trade
    trade = Trade(
        trade_id="T001", symbol="RELIANCE", strategy="ORB",
        direction="LONG", entry_price=2450.0, quantity=18,
        stop_loss=2430.0, target_1=2490.0,
        entry_time=datetime(2026, 1, 15, 9, 31),
    )
    with pytest.raises(Exception):
        trade.exit_price = 2490.0


# ─── Position ───

def test_position_long_unrealized_pnl():
    from core.entities.position import Position
    pos = Position(
        symbol="RELIANCE",
        direction="LONG",
        entry_price=2450.0,
        current_price=2470.0,
        quantity=18,
        stop_loss=2430.0,
        target_1=2490.0,
        strategy="ORB",
        entry_time=datetime(2026, 1, 15, 9, 31),
        entry_order_id="123456",
    )
    assert pos.unrealized_pnl == pytest.approx(18 * 20.0)
    assert pos.unrealized_pnl_percent == pytest.approx((20 / 2450) * 100)


def test_position_short_unrealized_pnl():
    from core.entities.position import Position
    pos = Position(
        symbol="INFY",
        direction="SHORT",
        entry_price=1580.0,
        current_price=1560.0,
        quantity=30,
        stop_loss=1600.0,
        target_1=1540.0,
        strategy="VWAP",
        entry_time=datetime(2026, 1, 15, 9, 45),
        entry_order_id="789012",
    )
    assert pos.unrealized_pnl == pytest.approx(30 * 20.0)


def test_trade_rejects_invalid_direction():
    from core.entities.trade import Trade
    with pytest.raises(ValueError, match="direction"):
        Trade(
            trade_id="T001", symbol="RELIANCE", strategy="ORB",
            direction="SIDEWAYS", entry_price=2450.0, quantity=18,
            stop_loss=2430.0, target_1=2490.0,
            entry_time=datetime(2026, 1, 15, 9, 31),
        )


def test_position_rejects_zero_quantity():
    from core.entities.position import Position
    with pytest.raises(ValueError, match="quantity"):
        Position(
            symbol="RELIANCE", direction="LONG",
            entry_price=2450.0, current_price=2470.0,
            quantity=0, stop_loss=2430.0, target_1=2490.0,
            strategy="ORB", entry_time=datetime(2026, 1, 15, 9, 31),
            entry_order_id="123456",
        )


def test_order_rejects_zero_quantity():
    from core.entities.order import Order, OrderStatus, OrderType, TransactionType
    with pytest.raises(ValueError, match="quantity"):
        Order(
            order_id="X", symbol="RELIANCE", token="2885",
            transaction_type=TransactionType.BUY, order_type=OrderType.MARKET,
            quantity=0, price=None, trigger_price=None,
            status=OrderStatus.PENDING, timestamp=datetime(2026, 1, 15, 9, 31),
        )


def test_signal_rejects_long_sl_above_entry():
    from core.entities.signal import Signal
    with pytest.raises(ValueError, match="stop_loss"):
        Signal(
            strategy="ORB", symbol="RELIANCE", direction="LONG",
            entry_price=2450.0, stop_loss=2480.0, target_1=2490.0,
            timestamp=datetime(2026, 1, 15, 9, 31),
        )


def test_signal_rejects_short_sl_below_entry():
    from core.entities.signal import Signal
    with pytest.raises(ValueError, match="stop_loss"):
        Signal(
            strategy="ORB", symbol="RELIANCE", direction="SHORT",
            entry_price=2450.0, stop_loss=2420.0, target_1=2410.0,
            timestamp=datetime(2026, 1, 15, 9, 31),
        )


def test_interfaces_are_runtime_checkable():
    from core.interfaces.i_broker import IOrderBroker, IDataBroker
    from core.interfaces.i_data_feed import IDataFeed
    # Protocols with @runtime_checkable support isinstance checks
    # A plain object is not an instance — but the check must not raise TypeError
    assert not isinstance(object(), IOrderBroker)
    assert not isinstance(object(), IDataBroker)
    assert not isinstance(object(), IDataFeed)
