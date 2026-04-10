"""Live execution engine — order placement, fill monitor, OCO logic."""
import logging
from core.entities.signal import Signal

logger = logging.getLogger(__name__)

_VARIETY = "NORMAL"
_PRODUCT = "INTRADAY"
_ORDER_TYPE = "MARKET"
_SL_ORDER_TYPE = "STOPLOSS_MARKET"
_EXCHANGE = "NSE"


class ExecutionEngine:
    """Async wrapper around the Angel One broker for order placement and monitoring."""

    def __init__(self, broker, slippage_pct: float = 0.0005) -> None:
        self.broker = broker
        self.slippage_pct = slippage_pct

    async def place_entry(self, signal: Signal, qty: int, token: str) -> str:
        """Place a market entry order. Returns the order ID."""
        side = "BUY" if signal.direction == "LONG" else "SELL"
        params = {
            "variety": _VARIETY,
            "tradingsymbol": signal.symbol,
            "symboltoken": token,
            "transactiontype": side,
            "exchange": _EXCHANGE,
            "ordertype": _ORDER_TYPE,
            "producttype": _PRODUCT,
            "quantity": str(qty),
            "price": "0",
        }
        resp = await self.broker.place_order(params)
        order_id = resp["orderid"]
        logger.info("entry order %s: %s %s x%d id=%s", side, signal.symbol, signal.direction, qty, order_id)
        return order_id

    async def place_sl_order(self, signal: Signal, qty: int, token: str) -> str:
        """Place a stoploss-market order opposite to signal direction. Returns order ID."""
        side = "SELL" if signal.direction == "LONG" else "BUY"
        params = {
            "variety": "STOPLOSS",
            "tradingsymbol": signal.symbol,
            "symboltoken": token,
            "transactiontype": side,
            "exchange": _EXCHANGE,
            "ordertype": _SL_ORDER_TYPE,
            "producttype": _PRODUCT,
            "quantity": str(qty),
            "price": "0",
            "triggerprice": str(signal.stop_loss),
        }
        resp = await self.broker.place_order(params)
        order_id = resp["orderid"]
        logger.info("SL order placed: %s sl=%.2f id=%s", signal.symbol, signal.stop_loss, order_id)
        return order_id

    async def cancel_order(self, order_id: str) -> None:
        """Cancel an open order."""
        await self.broker.cancel_order(order_id=order_id)
        logger.info("order cancelled: %s", order_id)

    async def get_fill_price(self, order_id: str) -> float | None:
        """Return average fill price if order is complete, else None."""
        status = await self.broker.get_order_status(order_id)
        if status.get("status") == "complete" and float(status.get("filledshares", 0)) > 0:
            return float(status["averageprice"])
        return None
