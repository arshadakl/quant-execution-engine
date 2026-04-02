"""Trade entity — immutable record of a completed or open trade."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


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
    exit_reason: Optional[str] = None  # "TARGET_HIT" | "SL_HIT" | "SQUARE_OFF" | "MANUAL"
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
