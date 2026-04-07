"""BaseStrategy ABC and BacktestParams — shared foundation for all strategies."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pandas as pd

from core.entities.signal import Signal

_VALID_INTERVALS = {"1m", "3m", "5m", "10m", "15m", "30m", "1h", "1d"}


@dataclass(frozen=True)
class BacktestParams:
    """Parameters that define a single backtest run."""

    symbol: str
    token: str
    interval: str
    from_dt: datetime
    to_dt: datetime
    initial_capital: float = 100000.0

    def __post_init__(self) -> None:
        if self.interval not in _VALID_INTERVALS:
            raise ValueError(
                f"interval {self.interval!r} invalid. Valid: {sorted(_VALID_INTERVALS)}"
            )
        if self.from_dt >= self.to_dt:
            raise ValueError(
                f"from_dt ({self.from_dt}) must be before to_dt ({self.to_dt})"
            )
        if self.initial_capital <= 0:
            raise ValueError(
                f"initial_capital must be positive, got {self.initial_capital}"
            )


class BaseStrategy(ABC):
    """Abstract base for all trading strategies.

    Subclasses must implement `name` (property) and `generate_signals`.
    """

    def __init__(self, params: dict) -> None:
        self._params = params

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique strategy identifier."""

    @property
    def params(self) -> dict:
        """Strategy parameters — used by optimizer for grid search."""
        return self._params

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        """Analyze OHLCV df and return trade signals.

        df: timezone-naive IST DatetimeIndex, columns: open high low close volume.
        Returns empty list when no signal is generated.
        """
