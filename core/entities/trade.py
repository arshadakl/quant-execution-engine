"""Trade entity — immutable record of a completed or open trade."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class ExitReason(str, Enum):
    TARGET_HIT = "TARGET_HIT"
    SL_HIT = "SL_HIT"
    SQUARE_OFF = "SQUARE_OFF"
    MANUAL = "MANUAL"


@dataclass(frozen=True)
class Trade:
    trade_id: str
    symbol: str
    strategy: str
    direction: str              # "LONG" or "SHORT"
    entry_price: float
    quantity: int
    stop_loss: float
    target_1: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    exit_reason: Optional[ExitReason] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None

    def __post_init__(self) -> None:
        if self.direction not in ("LONG", "SHORT"):
            raise ValueError(
                f"direction must be 'LONG' or 'SHORT', got {self.direction!r}"
            )
        if self.entry_price <= 0:
            raise ValueError(f"entry_price must be positive, got {self.entry_price}")
        if self.quantity <= 0:
            raise ValueError(f"quantity must be positive, got {self.quantity}")
        if self.stop_loss <= 0:
            raise ValueError(f"stop_loss must be positive, got {self.stop_loss}")
        if self.target_1 <= 0:
            raise ValueError(f"target_1 must be positive, got {self.target_1}")
