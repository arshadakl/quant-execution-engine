"""IBroker protocols — IOrderBroker + IDataBroker.
Adapters must implement these. Business logic depends only on these protocols.
"""
from datetime import datetime
from typing import Optional, Protocol

import pandas as pd

from core.entities.order import Order


class IOrderBroker(Protocol):
    """Protocol for placing and managing orders."""

    async def place_order(
        self,
        symbol: str,
        token: str,
        qty: int,
        order_type: str,
        transaction_type: str,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
    ) -> str:
        """Place an order. Returns order_id."""
        ...

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order. Returns True if successful."""
        ...

    async def get_order_status(self, order_id: str) -> dict:
        """Get current status of an order."""
        ...

    async def get_orders(self) -> list[Order]:
        """Get all orders for today."""
        ...


class IDataBroker(Protocol):
    """Protocol for fetching market data."""

    async def get_historical(
        self,
        symbol: str,
        token: str,
        interval: str,
        from_dt: datetime,
        to_dt: datetime,
    ) -> pd.DataFrame:
        """Fetch OHLCV candles. Returns DataFrame with columns:
        open, high, low, close, volume. Index: datetime."""
        ...

    async def get_ltp(
        self, symbol_token_pairs: list[tuple[str, str, str]]
    ) -> dict[str, float]:
        """Get last traded price.
        symbol_token_pairs: [(exchange, tradingsymbol, symboltoken), ...]
        Returns: {tradingsymbol: ltp}
        """
        ...

    async def get_funds(self) -> dict:
        """Get account funds and margin details."""
        ...

    async def get_positions(self) -> list:
        """Get current open positions from broker."""
        ...
