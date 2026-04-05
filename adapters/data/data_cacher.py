"""DataCacher — Parquet-backed cache-first OHLCV storage.

Files are named {symbol}_{interval}.parquet under cache_dir.
Saves always merge with existing data and deduplicate on index.
Timezone convention: all stored indices are timezone-naive (IST stripped).
"""
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

_OHLCV_COLS = ["open", "high", "low", "close", "volume"]
_SAFE_SYMBOL = re.compile(r"^[A-Z0-9\-&\.]{1,30}$")
_SAFE_INTERVAL = re.compile(r"^[a-z0-9]{1,5}$")


class DataCacher:
    """Parquet-backed OHLCV cache with merge/dedup on write.
    Implements IDataCacher protocol.
    """

    def __init__(self, cache_dir: Path) -> None:
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def cache_path(self, symbol: str, interval: str) -> Path:
        """Return the Parquet file path for this symbol+interval."""
        self._validate_key(symbol, interval)
        return self._dir / f"{symbol}_{interval}.parquet"

    def exists(self, symbol: str, interval: str) -> bool:
        """Return True if a cache file exists for this symbol+interval."""
        return self.cache_path(symbol, interval).exists()

    def save(self, symbol: str, interval: str, df: pd.DataFrame) -> None:
        """Merge df into the cache, deduplicating on index, then write atomically.

        Raises ValueError for invalid symbol/interval or missing OHLCV columns.
        Overwrites corrupt cache with new data and logs a warning.
        """
        self._validate_columns(df)
        df = _strip_tz(df)
        path = self.cache_path(symbol, interval)
        merged = _merge(df, path)
        _atomic_write(merged, path)
        logger.info("Cacher: saved %s/%s (%d rows total)", symbol, interval, len(merged))

    def load(
        self,
        symbol: str,
        interval: str,
        from_dt: Optional[datetime] = None,
        to_dt: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Load cached OHLCV data, optionally filtered by date range.

        Returns an empty DataFrame if no cache exists.
        """
        path = self.cache_path(symbol, interval)
        if not path.exists():
            return pd.DataFrame(columns=_OHLCV_COLS)

        df = pd.read_parquet(path)
        if from_dt is not None:
            df = df[df.index >= _naive(from_dt)]
        if to_dt is not None:
            df = df[df.index <= _naive(to_dt)]
        return df

    def clear(self, symbol: str, interval: str) -> None:
        """Delete the cache file if it exists."""
        path = self.cache_path(symbol, interval)
        if path.exists():
            path.unlink()
            logger.info("Cacher: cleared %s/%s", symbol, interval)

    # ─── Private helpers ───

    def _validate_key(self, symbol: str, interval: str) -> None:
        if not _SAFE_SYMBOL.match(symbol):
            raise ValueError(f"Invalid symbol: {symbol!r}")
        if not _SAFE_INTERVAL.match(interval):
            raise ValueError(f"Invalid interval: {interval!r}")

    def _validate_columns(self, df: pd.DataFrame) -> None:
        missing = set(_OHLCV_COLS) - set(df.columns)
        if missing:
            raise ValueError(f"DataFrame missing required columns: {missing}")


# ─── Module-level helpers (keep class under 150 lines) ───

def _strip_tz(df: pd.DataFrame) -> pd.DataFrame:
    """Return df with timezone-naive DatetimeIndex (strip tz if present)."""
    if hasattr(df.index, "tz") and df.index.tz is not None:
        return df.tz_localize(None)
    return df


def _naive(dt: datetime) -> datetime:
    """Return timezone-naive datetime (strip tzinfo if present)."""
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


def _merge(new_df: pd.DataFrame, path: Path) -> pd.DataFrame:
    """Read existing cache, concat with new_df, dedup and sort."""
    if not path.exists():
        return new_df.sort_index()
    try:
        existing = pd.read_parquet(path)
    except Exception as exc:
        logger.warning("Cacher: corrupt cache at %s — overwriting. Cause: %s", path.name, exc)
        return new_df.sort_index()
    merged = pd.concat([existing, new_df])
    merged = merged[~merged.index.duplicated(keep="last")]
    return merged.sort_index()


def _atomic_write(df: pd.DataFrame, path: Path) -> None:
    """Write df to a temp file then atomically rename to path."""
    tmp = path.with_suffix(".tmp")
    df.to_parquet(tmp)
    tmp.replace(path)
