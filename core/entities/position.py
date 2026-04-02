"""Position entity — open position with computed unrealized P&L."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Position:
    symbol: str
    direction: str          # "LONG" or "SHORT"
    entry_price: float
    current_price: float
    quantity: int
    stop_loss: float
    target_1: float
    strategy: str
    entry_time: datetime
    entry_order_id: str
    sl_order_id: Optional[str] = None
    target_order_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.direction not in ("LONG", "SHORT"):
            raise ValueError(
                f"direction must be 'LONG' or 'SHORT', got {self.direction!r}"
            )
        if self.entry_price <= 0:
            raise ValueError(f"entry_price must be positive, got {self.entry_price}")
        if self.quantity <= 0:
            raise ValueError(f"quantity must be positive, got {self.quantity}")

    @property
    def unrealized_pnl(self) -> float:
        if self.direction == "LONG":
            return (self.current_price - self.entry_price) * self.quantity
        return (self.entry_price - self.current_price) * self.quantity

    @property
    def unrealized_pnl_percent(self) -> float:
        cost_basis = self.entry_price * self.quantity
        return (self.unrealized_pnl / cost_basis) * 100
