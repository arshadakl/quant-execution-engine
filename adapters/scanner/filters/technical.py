"""Technical filter — RSI 30–70, EMA 9/21/50 proximity, VWAP positioning."""
import logging
import pandas as pd

logger = logging.getLogger(__name__)

_MIN_BARS = 50  # need enough bars to warm up EMA50 + RSI14


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI using EWM smoothing."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    alpha = 1.0 / period
    avg_gain = gain.ewm(alpha=alpha, adjust=False).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False).mean()
    # avg_loss=0 + avg_gain=0 → RSI=50; avg_loss=0 + avg_gain>0 → RSI=100
    rsi = pd.Series(index=close.index, dtype=float)
    both_zero = (avg_gain == 0) & (avg_loss == 0)
    loss_zero = (avg_loss == 0) & ~both_zero
    normal = ~both_zero & ~loss_zero
    rsi[both_zero] = 50.0
    rsi[loss_zero] = 100.0
    rsi[normal] = 100 - (100 / (1 + avg_gain[normal] / avg_loss[normal]))
    return rsi


def compute_emas(close: pd.Series, periods: tuple[int, ...] = (9, 21, 50)) -> dict[int, pd.Series]:
    """Return dict of {period: EMA series} for each period."""
    return {p: close.ewm(span=p, adjust=False).mean() for p in periods}


def compute_vwap(df: pd.DataFrame) -> pd.Series:
    """Session VWAP: cumulative(typical_price * volume) / cumulative(volume)."""
    typical = (df["high"] + df["low"] + df["close"]) / 3
    return (typical * df["volume"]).cumsum() / df["volume"].cumsum()


class TechnicalFilter:
    """Pass/fail filter: RSI in range, close near EMAs, close vs VWAP check."""

    def __init__(
        self,
        rsi_low: int = 30,
        rsi_high: int = 70,
        ema_periods: tuple[int, ...] = (9, 21, 50),
    ) -> None:
        self.rsi_low = rsi_low
        self.rsi_high = rsi_high
        self.ema_periods = ema_periods

    def passes(self, df: pd.DataFrame, symbol: str) -> bool:
        """Return True if RSI, EMA, and VWAP conditions are satisfied."""
        if df.empty or len(df) < _MIN_BARS:
            return False

        close = df["close"]
        last_close = float(close.iloc[-1])

        rsi = compute_rsi(close)
        last_rsi = float(rsi.iloc[-1])
        if not (self.rsi_low <= last_rsi <= self.rsi_high):
            logger.debug("%s failed RSI: rsi=%.2f", symbol, last_rsi)
            return False

        emas = compute_emas(close, self.ema_periods)
        ema_vals = {p: float(s.iloc[-1]) for p, s in emas.items()}

        # Close must be within 3% of the fastest EMA (tightest proximity check)
        fast_period = min(self.ema_periods)
        fast_ema = ema_vals[fast_period]
        proximity_pct = abs(last_close - fast_ema) / fast_ema
        if proximity_pct > 0.03:
            logger.debug("%s failed EMA proximity: %.4f from EMA%d", symbol, proximity_pct, fast_period)
            return False

        vwap = compute_vwap(df)
        last_vwap = float(vwap.iloc[-1])
        vwap_dist_pct = abs(last_close - last_vwap) / last_vwap
        if vwap_dist_pct > 0.03:
            logger.debug("%s failed VWAP proximity: %.4f", symbol, vwap_dist_pct)
            return False

        return True
