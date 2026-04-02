"""Order entity — immutable representation of a broker order."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    OPEN = "OPEN"


@dataclass(frozen=True)
class Order:
    order_id: str
    symbol: str
    token: str                      # Angel One symbol token
    transaction_type: TransactionType
    order_type: OrderType
    quantity: int
    price: Optional[float]
    trigger_price: Optional[float]
    status: OrderStatus
    timestamp: datetime
    fill_price: Optional[float] = None

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError(f"quantity must be positive, got {self.quantity}")
        if self.order_type == OrderType.LIMIT and (
            self.price is None or self.price <= 0
        ):
            raise ValueError("LIMIT order must have a positive price")
