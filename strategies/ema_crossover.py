"""EMA Crossover strategy.

Logic:
  Compute fast EMA and slow EMA on close prices.
  - LONG  when fast EMA crosses above slow EMA (previous bar: fast < slow,
           current bar: fast > slow).
  - SHORT when fast EMA crosses below slow EMA (previous bar: fast > slow,
           current bar: fast < slow).
  Returns the first crossover signal (one per session).

Risk / reward:
  SL     = slow EMA at signal bar (price should not violate the slow trend).
  Target = entry ± risk * target_multiplier.
"""
import logging

import pandas as pd

from core.entities.signal import Signal
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

_DEFAULTS = {
    "fast_period": 9,
    "slow_period": 21,
    "target_multiplier": 2.0,
}


def compute_ema(series: pd.Series, period: int) -> pd.Series:
    """Return exponential moving average with given span."""
    return series.ewm(span=period, adjust=False).mean()


class EMACrossoverStrategy(BaseStrategy):
    """9/21 EMA crossover strategy."""

    def __init__(self, params: dict | None = None) -> None:
        super().__init__({**_DEFAULTS, **(params or {})})

    @property
    def name(self) -> str:
        return "EMA_CROSSOVER"

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        """Return at most one EMA crossover signal for the session."""
        slow = self.params["slow_period"]
        if df.empty or len(df) <= slow:
            return []

        fast_ema = compute_ema(df["close"], self.params["fast_period"])
        slow_ema = compute_ema(df["close"], slow)
        mult = self.params["target_multiplier"]

        for i in range(1, len(df)):
            prev_fast, prev_slow = fast_ema.iloc[i - 1], slow_ema.iloc[i - 1]
            curr_fast, curr_slow = fast_ema.iloc[i], slow_ema.iloc[i]
            entry = float(df["close"].iloc[i])
            sl = float(curr_slow)
            ts = df.index[i]

            # Bullish crossover — strictly from below to above
            if prev_fast < prev_slow and curr_fast > curr_slow:
                risk = max(entry - sl, 0.01)
                return [self._signal(symbol, "LONG", entry,
                                     round(sl, 4),
                                     round(entry + risk * mult, 4), ts)]
            # Bearish crossover — strictly from above to below
            if prev_fast > prev_slow and curr_fast < curr_slow:
                risk = max(sl - entry, 0.01)
                return [self._signal(symbol, "SHORT", entry,
                                     round(sl, 4),
                                     round(entry - risk * mult, 4), ts)]
        return []

    def _signal(self, symbol, direction, entry, sl, target, ts) -> Signal:
        return Signal(
            strategy=self.name,
            symbol=symbol,
            direction=direction,
            entry_price=round(entry, 4),
            stop_loss=sl,
            target_1=target,
            timestamp=ts,
        )
