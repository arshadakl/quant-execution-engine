"""IDataCacher protocol — OHLCV cache interface."""
from datetime import datetime
from pathlib import Path
from typing import Optional, Protocol, runtime_checkable

import pandas as pd


@runtime_checkable
class IDataCacher(Protocol):
    """Protocol for Parquet-backed OHLCV cache."""

    def cache_path(self, symbol: str, interval: str) -> Path:
        """Return the file path for a given symbol+interval cache."""
        ...

    def exists(self, symbol: str, interval: str) -> bool:
        """Return True if a cache file exists for symbol+interval."""
        ...

    def save(self, symbol: str, interval: str, df: pd.DataFrame) -> None:
        """Persist df, merging with any existing cache and deduplicating."""
        ...

    def load(
        self,
        symbol: str,
        interval: str,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Load cached data, optionally filtered by date range."""
        ...

    def clear(self, symbol: str, interval: str) -> None:
        """Delete the cache file if it exists."""
        ...
