"""Risk Manager — validates signals against daily limits, time gate, and cooldown."""
import logging
from dataclasses import dataclass, field
from datetime import datetime, time

logger = logging.getLogger(__name__)


@dataclass
class RiskState:
    """Mutable snapshot of current risk exposure."""
    daily_pnl: float = 0.0
    open_positions: int = 0
    daily_trades: int = 0
    last_trade_time: datetime | None = None
    kill_switch: bool = False


class RiskManager:
    """Validates a signal against configurable risk rules."""

    def __init__(
        self,
        max_daily_loss_pct: float = 0.03,
        max_open_positions: int = 5,
        max_daily_trades: int = 10,
        trade_start: time = time(9, 15),
        trade_end: time = time(15, 15),
        cooldown_seconds: int = 300,
    ) -> None:
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_open_positions = max_open_positions
        self.max_daily_trades = max_daily_trades
        self.trade_start = trade_start
        self.trade_end = trade_end
        self.cooldown_seconds = cooldown_seconds

    def validate(
        self,
        state: RiskState,
        capital: float,
        signal_time: datetime,
    ) -> tuple[bool, str]:
        """Return (True, "") if signal is allowed, else (False, reason)."""
        if state.kill_switch:
            return False, "kill switch active"

        max_loss = capital * self.max_daily_loss_pct
        if state.daily_pnl <= -max_loss:
            logger.warning("daily loss limit breached: pnl=%.0f limit=%.0f",
                           state.daily_pnl, max_loss)
            return False, f"daily loss limit breached: pnl={state.daily_pnl:.0f}"

        sig_time = signal_time.time()
        if sig_time < self.trade_start or sig_time > self.trade_end:
            return False, f"outside trading time window: {sig_time}"

        if state.open_positions >= self.max_open_positions:
            return False, f"max open positions reached: {state.open_positions}"

        if state.daily_trades >= self.max_daily_trades:
            return False, f"max daily trades reached: {state.daily_trades}"

        if state.last_trade_time is not None:
            elapsed = (signal_time - state.last_trade_time).total_seconds()
            if elapsed < self.cooldown_seconds:
                return False, f"cooldown active: {elapsed:.0f}s elapsed"

        return True, ""
