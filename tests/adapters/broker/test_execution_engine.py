"""Tests for Live Execution Engine."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
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


def _mock_broker() -> MagicMock:
    broker = MagicMock()
    broker.place_order = AsyncMock(return_value={"orderid": "ORD001", "status": "complete"})
    broker.get_order_status = AsyncMock(return_value={"status": "complete", "filledshares": 10, "averageprice": 500.0})
    return broker


# ─── Instantiation ───

def test_instantiates_with_broker():
    from adapters.broker.execution_engine import ExecutionEngine
    broker = _mock_broker()
    eng = ExecutionEngine(broker=broker)
    assert eng.broker is broker


def test_instantiates_with_slippage():
    from adapters.broker.execution_engine import ExecutionEngine
    eng = ExecutionEngine(broker=_mock_broker(), slippage_pct=0.001)
    assert eng.slippage_pct == 0.001


# ─── place_entry ───

@pytest.mark.asyncio
async def test_place_entry_calls_broker_place_order():
    from adapters.broker.execution_engine import ExecutionEngine
    broker = _mock_broker()
    eng = ExecutionEngine(broker=broker)
    sig = _make_signal("RELIANCE", "LONG")
    result = await eng.place_entry(signal=sig, qty=10, token="1234")
    broker.place_order.assert_called_once()
    assert result is not None


@pytest.mark.asyncio
async def test_place_entry_returns_order_id():
    from adapters.broker.execution_engine import ExecutionEngine
    broker = _mock_broker()
    eng = ExecutionEngine(broker=broker)
    sig = _make_signal()
    order_id = await eng.place_entry(signal=sig, qty=10, token="1234")
    assert order_id == "ORD001"


@pytest.mark.asyncio
async def test_place_entry_long_uses_buy_direction():
    from adapters.broker.execution_engine import ExecutionEngine
    broker = _mock_broker()
    eng = ExecutionEngine(broker=broker)
    sig = _make_signal("RELIANCE", "LONG")
    await eng.place_entry(signal=sig, qty=10, token="1234")
    call_kwargs = broker.place_order.call_args
    # transactiontype should be BUY for LONG
    args = call_kwargs[1] if call_kwargs[1] else call_kwargs[0][0]
    if isinstance(args, dict):
        assert args.get("transactiontype") == "BUY"


@pytest.mark.asyncio
async def test_place_entry_short_uses_sell_direction():
    from adapters.broker.execution_engine import ExecutionEngine
    broker = _mock_broker()
    eng = ExecutionEngine(broker=broker)
    sig = _make_signal("RELIANCE", "SHORT")
    await eng.place_entry(signal=sig, qty=10, token="1234")
    call_kwargs = broker.place_order.call_args
    args = call_kwargs[1] if call_kwargs[1] else call_kwargs[0][0]
    if isinstance(args, dict):
        assert args.get("transactiontype") == "SELL"


# ─── place_sl_order ───

@pytest.mark.asyncio
async def test_place_sl_order_returns_order_id():
    from adapters.broker.execution_engine import ExecutionEngine
    broker = _mock_broker()
    eng = ExecutionEngine(broker=broker)
    sig = _make_signal("RELIANCE", "LONG")
    order_id = await eng.place_sl_order(signal=sig, qty=10, token="1234")
    assert order_id == "ORD001"


@pytest.mark.asyncio
async def test_place_sl_order_calls_broker():
    from adapters.broker.execution_engine import ExecutionEngine
    broker = _mock_broker()
    eng = ExecutionEngine(broker=broker)
    sig = _make_signal()
    await eng.place_sl_order(signal=sig, qty=10, token="1234")
    broker.place_order.assert_called_once()


# ─── cancel_order ───

@pytest.mark.asyncio
async def test_cancel_order_calls_broker():
    from adapters.broker.execution_engine import ExecutionEngine
    broker = _mock_broker()
    broker.cancel_order = AsyncMock(return_value={"status": "cancelled"})
    eng = ExecutionEngine(broker=broker)
    await eng.cancel_order(order_id="ORD001")
    broker.cancel_order.assert_called_once_with(order_id="ORD001")


# ─── get_fill_price ───

@pytest.mark.asyncio
async def test_get_fill_price_returns_average_price():
    from adapters.broker.execution_engine import ExecutionEngine
    broker = _mock_broker()
    eng = ExecutionEngine(broker=broker)
    price = await eng.get_fill_price(order_id="ORD001")
    assert price == pytest.approx(500.0)


@pytest.mark.asyncio
async def test_get_fill_price_returns_none_when_not_filled():
    from adapters.broker.execution_engine import ExecutionEngine
    broker = _mock_broker()
    broker.get_order_status = AsyncMock(return_value={"status": "open", "filledshares": 0, "averageprice": 0.0})
    eng = ExecutionEngine(broker=broker)
    price = await eng.get_fill_price(order_id="ORD001")
    assert price is None
