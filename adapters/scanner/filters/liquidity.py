"""Liquidity filter — screens stocks by average volume and daily turnover."""
import logging
import pandas as pd

logger = logging.getLogger(__name__)

_CR = 1_00_00_000  # 1 Crore in rupees


class LiquidityFilter:
    """Pass/fail filter: average volume >= min_volume AND avg turnover >= min_turnover_cr."""

    def __init__(
        self,
        min_volume: int = 500_000,
        min_turnover_cr: float = 10.0,
    ) -> None:
        self.min_volume = min_volume
        self.min_turnover_cr = min_turnover_cr

    def passes(self, df: pd.DataFrame, symbol: str) -> bool:
        """Return True if df meets volume and turnover thresholds."""
        if df.empty or len(df) < 2:
            return False

        avg_volume = df["volume"].mean()
        avg_turnover_cr = (df["close"] * df["volume"]).mean() / _CR

        ok = bool(avg_volume >= self.min_volume and avg_turnover_cr >= self.min_turnover_cr)
        if not ok:
            logger.debug(
                "%s failed liquidity: avg_vol=%.0f avg_turnover=%.2fCr",
                symbol, avg_volume, avg_turnover_cr,
            )
        return ok
