"""Signal entity — immutable trading signal produced by a strategy."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class Signal:
    strategy: str
    symbol: str
    direction: str        # "LONG" or "SHORT"
    entry_price: float
    stop_loss: float
    target_1: float
    timestamp: datetime
    confidence: float = 1.0
    target_2: Optional[float] = None

    def __post_init__(self) -> None:
        if self.direction not in ("LONG", "SHORT"):
            raise ValueError(
                f"direction must be 'LONG' or 'SHORT', got {self.direction!r}"
            )
        if self.entry_price <= 0:
            raise ValueError(f"entry_price must be positive, got {self.entry_price}")
        if self.stop_loss <= 0:
            raise ValueError(f"stop_loss must be positive, got {self.stop_loss}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"confidence must be between 0 and 1, got {self.confidence}"
            )
        if self.direction == "LONG":
            if self.stop_loss >= self.entry_price:
                raise ValueError(
                    f"LONG stop_loss ({self.stop_loss}) must be below "
                    f"entry_price ({self.entry_price})"
                )
            if self.target_1 <= self.entry_price:
                raise ValueError(
                    f"LONG target_1 ({self.target_1}) must be above "
                    f"entry_price ({self.entry_price})"
                )
        else:  # SHORT
            if self.stop_loss <= self.entry_price:
                raise ValueError(
                    f"SHORT stop_loss ({self.stop_loss}) must be above "
                    f"entry_price ({self.entry_price})"
                )
            if self.target_1 >= self.entry_price:
                raise ValueError(
                    f"SHORT target_1 ({self.target_1}) must be below "
                    f"entry_price ({self.entry_price})"
                )
