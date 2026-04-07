"""TradeSimulator — simulates fills and exits against OHLCV data."""
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd

from backtester.charges import TradeCharges, calculate_charges
from core.entities.signal import Signal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SimulatedTrade:
    """Result of one simulated round-trip trade."""

    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    qty: int
    entry_time: datetime
    exit_time: datetime
    charges: TradeCharges

    @property
    def gross_pnl(self) -> float:
        if self.direction == "LONG":
            return (self.exit_price - self.entry_price) * self.qty
        return (self.entry_price - self.exit_price) * self.qty

    @property
    def net_pnl(self) -> float:
        return self.gross_pnl - self.charges.total


class TradeSimulator:
    """Replays a Signal against OHLCV bars to produce a SimulatedTrade."""

    def simulate(
        self,
        signal: Signal,
        df: pd.DataFrame,
        qty: int,
        slippage_pct: float = 0.0005,
    ) -> Optional[SimulatedTrade]:
        """Simulate entry + exit for signal on df.

        Entry: first bar at or after signal.timestamp — open ± slippage.
        Exit: SL/target breach on candle high/low, or last bar close.
        Returns None if no entry bar found.
        """
        entry_bars = df[df.index >= signal.timestamp]
        if entry_bars.empty:
            return None

        entry_bar = entry_bars.iloc[0]
        if signal.direction == "LONG":
            entry_price = entry_bar["open"] * (1 + slippage_pct)
        else:
            entry_price = entry_bar["open"] * (1 - slippage_pct)
        entry_time = entry_bars.index[0]

        exit_price, exit_time = self._find_exit(
            signal, df, entry_time, entry_price
        )
        charges = calculate_charges(entry_price, exit_price, qty)

        return SimulatedTrade(
            symbol=signal.symbol,
            direction=signal.direction,
            entry_price=round(entry_price, 4),
            exit_price=round(exit_price, 4),
            qty=qty,
            entry_time=entry_time,
            exit_time=exit_time,
            charges=charges,
        )

    def _find_exit(
        self,
        signal: Signal,
        df: pd.DataFrame,
        entry_time: datetime,
        entry_price: float,
    ) -> tuple[float, datetime]:
        """Scan bars after entry for SL/target breach; fall back to last close."""
        post_entry = df[df.index > entry_time]

        for ts, bar in post_entry.iterrows():
            if signal.direction == "LONG":
                if bar["low"] <= signal.stop_loss:
                    return signal.stop_loss, ts
                if bar["high"] >= signal.target_1:
                    return signal.target_1, ts
            else:
                if bar["high"] >= signal.stop_loss:
                    return signal.stop_loss, ts
                if bar["low"] <= signal.target_1:
                    return signal.target_1, ts

        last = df.iloc[-1]
        return last["close"], df.index[-1]
