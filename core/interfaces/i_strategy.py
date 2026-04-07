"""IStrategy protocol — pluggable strategy interface."""
from typing import Protocol, runtime_checkable

import pandas as pd

from core.entities.signal import Signal


@runtime_checkable
class IStrategy(Protocol):
    """Protocol for all trading strategies.

    Every strategy must implement name, params, and generate_signals.
    """

    @property
    def name(self) -> str:
        """Unique strategy identifier."""
        ...

    @property
    def params(self) -> dict:
        """Strategy parameters dict — used by the optimizer."""
        ...

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        """Analyze df and return zero or more trade signals.

        df: OHLCV DataFrame indexed by datetime (timezone-naive IST).
        symbol: trading symbol string (e.g. 'RELIANCE').
        """
        ...
