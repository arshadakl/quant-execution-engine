"""Gap Fill strategy.

Logic:
  Scan for overnight gaps between consecutive trading days.
  - Gap UP  (today_open > prev_close * (1 + min_gap_pct)) → SHORT: fade back to prev_close.
  - Gap DOWN (today_open < prev_close * (1 - min_gap_pct)) → LONG:  fill up to prev_close.

  Returns the first qualifying gap signal (one per call).

Entry  : first bar open of the gap day.
Target : prev_close (full gap fill).
SL     : entry ± gap_size * sl_multiplier (beyond entry in the wrong direction).
"""
import logging

import pandas as pd

from core.entities.signal import Signal
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

_DEFAULTS = {
    "min_gap_pct": 0.005,   # 0.5% minimum gap
    "sl_multiplier": 0.5,   # SL = gap_size * sl_multiplier beyond entry
}


class GapFillStrategy(BaseStrategy):
    """Fade overnight gaps expecting statistical reversion to prior close."""

    def __init__(self, params: dict | None = None) -> None:
        super().__init__({**_DEFAULTS, **(params or {})})

    @property
    def name(self) -> str:
        return "GAP_FILL"

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        """Return first gap fill signal found across all day boundaries in df."""
        if df.empty:
            return []

        dates = sorted(set(df.index.date))
        if len(dates) < 2:
            return []

        min_gap = self.params["min_gap_pct"]
        sl_mult = self.params["sl_multiplier"]

        for i in range(1, len(dates)):
            prev_day_bars = df[df.index.date == dates[i - 1]]
            today_bars = df[df.index.date == dates[i]]

            if prev_day_bars.empty or today_bars.empty:
                continue

            prev_close = float(prev_day_bars["close"].iloc[-1])
            today_open = float(today_bars["open"].iloc[0])
            today_ts = today_bars.index[0]
            gap_size = abs(today_open - prev_close)

            if today_open > prev_close * (1 + min_gap):
                sl = round(today_open + gap_size * sl_mult, 4)
                return [self._signal(symbol, "SHORT", today_open,
                                     sl, round(prev_close, 4), today_ts)]

            if today_open < prev_close * (1 - min_gap):
                sl = round(today_open - gap_size * sl_mult, 4)
                return [self._signal(symbol, "LONG", today_open,
                                     sl, round(prev_close, 4), today_ts)]
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
