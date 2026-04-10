"""Square-off manager — time-based forced exit of all open positions."""
import logging
from datetime import datetime, time

logger = logging.getLogger(__name__)


class SquareOffManager:
    """Forces close of all open paper trades at or after cutoff_time."""

    def __init__(self, cutoff_time: time = time(15, 10)) -> None:
        self.cutoff_time = cutoff_time

    def should_square_off(self, now: datetime) -> bool:
        """Return True if current time has reached or passed the cutoff."""
        return bool(now.time() >= self.cutoff_time)

    def close_all(
        self,
        paper_trader,
        ltp_map: dict[str, float],
        now: datetime,
    ) -> int:
        """Close every open trade at its LTP (falls back to entry_price). Returns count."""
        trades = paper_trader.open_trades()
        for trade in trades:
            symbol = trade["symbol"]
            exit_price = ltp_map.get(symbol, trade["entry_price"])
            paper_trader.close_trade(
                trade_id=trade["id"],
                exit_price=exit_price,
                exit_time=now,
            )
            logger.info("square-off: %s id=%d exit=%.2f", symbol, trade["id"], exit_price)
        return len(trades)
