"""Volatility filter — ATR(14) > min_atr_pct and price in [min_price, max_price]."""
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Compute ATR using Wilder's smoothing (EWM with alpha=1/period)."""
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


class VolatilityFilter:
    """Pass/fail filter: price in range AND ATR% above threshold."""

    def __init__(
        self,
        atr_period: int = 14,
        min_atr_pct: float = 0.015,
        min_price: float = 100.0,
        max_price: float = 5000.0,
    ) -> None:
        self.atr_period = atr_period
        self.min_atr_pct = min_atr_pct
        self.min_price = min_price
        self.max_price = max_price

    def passes(self, df: pd.DataFrame, symbol: str) -> bool:
        """Return True if volatility and price range conditions are met."""
        if df.empty or len(df) < self.atr_period:
            return False

        last_close = float(df["close"].iloc[-1])

        if not (self.min_price <= last_close <= self.max_price):
            logger.debug("%s failed price range: close=%.2f", symbol, last_close)
            return False

        atr = compute_atr(df, self.atr_period)
        atr_pct = float(atr.iloc[-1]) / last_close

        if atr_pct < self.min_atr_pct:
            logger.debug("%s failed ATR: atr_pct=%.4f", symbol, atr_pct)
            return False

        return True
