"""VWAP Reversion strategy.

Logic:
  1. Compute session VWAP = cumsum(typical_price * volume) / cumsum(volume).
  2. For each bar check deviation of close from VWAP.
  3. LONG  when close < VWAP * (1 - deviation_pct)  — oversold, fade back to VWAP.
  4. SHORT when close > VWAP * (1 + deviation_pct)  — overbought, fade back to VWAP.
  5. Return first signal only (one per session).

Risk / reward:
  deviation_distance = abs(close - vwap)
  SL     = entry ∓ deviation_distance          (equal distance on wrong side)
  Target = entry ± deviation_distance * target_multiplier
"""
import logging

import pandas as pd

from core.entities.signal import Signal
from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

_DEFAULTS = {
    "deviation_pct": 0.015,       # 1.5%
    "target_multiplier": 1.5,
}


def compute_vwap(df: pd.DataFrame) -> pd.Series:
    """Return cumulative session VWAP series indexed like df."""
    typical = (df["high"] + df["low"] + df["close"]) / 3
    cum_tp_vol = (typical * df["volume"]).cumsum()
    cum_vol = df["volume"].cumsum()
    return cum_tp_vol / cum_vol


class VWAPReversionStrategy(BaseStrategy):
    """VWAP mean-reversion strategy."""

    def __init__(self, params: dict | None = None) -> None:
        super().__init__({**_DEFAULTS, **(params or {})})

    @property
    def name(self) -> str:
        return "VWAP_REVERSION"

    def generate_signals(self, df: pd.DataFrame, symbol: str) -> list[Signal]:
        """Return at most one VWAP reversion signal for the session."""
        if df.empty:
            return []

        vwap = compute_vwap(df)
        dev = self.params["deviation_pct"]
        mult = self.params["target_multiplier"]

        for ts, bar in df.iterrows():
            close = float(bar["close"])
            v = float(vwap.loc[ts])
            dist = abs(close - v)

            if close < v * (1 - dev):
                return [self._signal(symbol, "LONG", close,
                                     round(close - dist, 4),
                                     round(close + dist * mult, 4), ts)]
            if close > v * (1 + dev):
                return [self._signal(symbol, "SHORT", close,
                                     round(close + dist, 4),
                                     round(close - dist * mult, 4), ts)]
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
