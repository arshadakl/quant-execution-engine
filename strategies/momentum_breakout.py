"""Momentum Breakout strategy.

Logic:
  For each bar with at least `lookback_bars` of history:
  - Compute the highest high and lowest low of the previous N bars.
  - Compute average volume of the previous N bars.
  - LONG  if close > prev_highest_high AND volume > avg_vol * volume_multiplier.
  - SHORT if close < prev_lowest_low  AND volume > avg_vol * volume_multiplier.
  Returns the first qualifying signal (one per session).

Risk / reward:
  LONG  SL = prev_lowest_low;  target = entry + (entry - SL) * target_multiplier
  SHORT SL = prev_highest_high; target = entry - (SL - entry) * target_multiplier
"""
import logging

import pandas as pd

from core.entities.signal import Signal
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

_DEFAULTS = {
    "lookback_bars": 20,
    "volume_multiplier": 1.5,
    "target_multiplier": 2.0,
}


class MomentumBreakoutStrategy(BaseStrategy):
    """High-volume breakout to new N-bar highs/lows."""

    def __init__(self, params: dict | None = None) -> None:
        super().__init__({**_DEFAULTS, **(params or {})})

    @property
    def name(self) -> str:
        return "MOMENTUM_BREAKOUT"

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        """Return at most one momentum breakout signal for the session."""
        n = self.params["lookback_bars"]
        vol_mult = self.params["volume_multiplier"]
        tgt_mult = self.params["target_multiplier"]

        if df.empty or len(df) <= n:
            return []

        for i in range(n, len(df)):
            bar = df.iloc[i]
            window = df.iloc[i - n: i]

            prev_high = float(window["high"].max())
            prev_low = float(window["low"].min())
            avg_vol = float(window["volume"].mean())

            close = float(bar["close"])
            vol = float(bar["volume"])

            if vol <= avg_vol * vol_mult:
                continue

            if close > prev_high:
                risk = close - prev_low
                return [self._signal(symbol, "LONG", close, prev_low,
                                     round(close + risk * tgt_mult, 4),
                                     df.index[i])]
            if close < prev_low:
                risk = prev_high - close
                return [self._signal(symbol, "SHORT", close, prev_high,
                                     round(close - risk * tgt_mult, 4),
                                     df.index[i])]
        return []

    def _signal(self, symbol, direction, entry, sl, target, ts) -> Signal:
        return Signal(
            strategy=self.name,
            symbol=symbol,
            direction=direction,
            entry_price=round(entry, 4),
            stop_loss=round(sl, 4),
            target_1=target,
            timestamp=ts,
        )
