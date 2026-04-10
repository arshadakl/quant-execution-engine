"""Pre-market filter — gap detection and volume spike screening."""
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def compute_gap_pct(prev_close: float, today_open: float) -> float:
    """Return signed gap percentage: (today_open - prev_close) / prev_close."""
    return (today_open - prev_close) / prev_close


class PreMarketFilter:
    """Pass/fail: gap >= min_gap_pct (abs) AND today's avg volume >= volume_spike_mult * prev avg."""

    def __init__(
        self,
        min_gap_pct: float = 0.005,
        volume_spike_mult: float = 1.5,
    ) -> None:
        self.min_gap_pct = min_gap_pct
        self.volume_spike_mult = volume_spike_mult

    def passes(
        self,
        prev_day: pd.DataFrame,
        today: pd.DataFrame,
        symbol: str,
    ) -> bool:
        """Return True if gap and volume spike conditions are met."""
        if prev_day.empty or today.empty:
            return False

        prev_close = float(prev_day["close"].iloc[-1])
        today_open = float(today["open"].iloc[0])

        gap = compute_gap_pct(prev_close, today_open)
        if abs(gap) < self.min_gap_pct:
            logger.debug("%s failed gap: gap_pct=%.4f", symbol, gap)
            return False

        prev_avg_vol = float(prev_day["volume"].mean())
        today_avg_vol = float(today["volume"].mean())

        if today_avg_vol < self.volume_spike_mult * prev_avg_vol:
            logger.debug(
                "%s failed volume spike: today_vol=%.0f prev_avg=%.0f",
                symbol, today_avg_vol, prev_avg_vol,
            )
            return False

        return True
