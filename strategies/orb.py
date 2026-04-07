"""ORB — Opening Range Breakout strategy.

Logic:
  1. Identify opening range: high/low of the first `opening_range_minutes` of data.
  2. For each bar after the range:
     - LONG if close > range_high * (1 + buffer)
     - SHORT if close < range_low  * (1 - buffer)
  3. Return only the first signal (one per session).

Stop loss : opposite side of the range (range_low for LONG, range_high for SHORT).
Target    : entry ± range_size * target_multiplier.
"""
import logging
from datetime import timedelta

import pandas as pd

from core.entities.signal import Signal
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

_DEFAULTS = {
    "opening_range_minutes": 15,
    "breakout_buffer_pct": 0.001,   # 0.1%
    "target_multiplier": 2.0,
}


class ORBStrategy(BaseStrategy):
    """Opening Range Breakout strategy."""

    def __init__(self, params: dict | None = None) -> None:
        merged = {**_DEFAULTS, **(params or {})}
        super().__init__(merged)

    @property
    def name(self) -> str:
        return "ORB"

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        """Return at most one ORB signal for the session."""
        if df.empty:
            return []

        or_end = df.index[0] + timedelta(minutes=self.params["opening_range_minutes"])
        or_bars = df[df.index < or_end]
        post_bars = df[df.index >= or_end]

        if or_bars.empty or post_bars.empty:
            return []

        range_high = float(or_bars["high"].max())
        range_low = float(or_bars["low"].min())
        range_size = range_high - range_low

        if range_size <= 0:
            return []

        buf = self.params["breakout_buffer_pct"]
        mult = self.params["target_multiplier"]
        long_level = range_high * (1 + buf)
        short_level = range_low * (1 - buf)

        for ts, bar in post_bars.iterrows():
            close = float(bar["close"])
            if close > long_level:
                return [self._signal(symbol, "LONG", close, range_low,
                                     close + range_size * mult, ts)]
            if close < short_level:
                return [self._signal(symbol, "SHORT", close, range_high,
                                     close - range_size * mult, ts)]
        return []

    def _signal(self, symbol, direction, entry, sl, target, ts) -> Signal:
        return Signal(
            strategy=self.name,
            symbol=symbol,
            direction=direction,
            entry_price=round(entry, 4),
            stop_loss=round(sl, 4),
            target_1=round(target, 4),
            timestamp=ts,
        )
