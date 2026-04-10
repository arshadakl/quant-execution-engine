"""Portfolio tracker — cash, open positions, day P&L, equity, drawdown."""
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PositionRecord:
    """Single open position."""
    symbol: str
    qty: int
    entry_price: float


class PortfolioTracker:
    """Tracks cash, open positions, day P&L and drawdown in real time."""

    def __init__(self, initial_capital: float) -> None:
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.day_pnl: float = 0.0
        self.peak_capital: float = initial_capital
        self.positions: dict[str, PositionRecord] = {}

    @property
    def open_position_count(self) -> int:
        return len(self.positions)

    def open_position(self, symbol: str, qty: int, entry_price: float) -> None:
        """Deduct cost from cash and record the position."""
        cost = qty * entry_price
        self.cash -= cost
        self.positions[symbol] = PositionRecord(symbol=symbol, qty=qty, entry_price=entry_price)
        logger.debug("opened %s x%d @ %.2f cost=%.0f", symbol, qty, entry_price, cost)

    def close_position(self, symbol: str, exit_price: float) -> None:
        """Return proceeds to cash, update day P&L, and remove position."""
        pos = self.positions[symbol]  # raises KeyError if not open
        proceeds = pos.qty * exit_price
        pnl = (exit_price - pos.entry_price) * pos.qty
        self.cash += proceeds
        self.day_pnl += pnl
        del self.positions[symbol]
        # update peak
        current_equity = self.cash
        if current_equity > self.peak_capital:
            self.peak_capital = current_equity
        logger.debug("closed %s @ %.2f pnl=%.0f day_pnl=%.0f", symbol, exit_price, pnl, self.day_pnl)

    def equity(self, mark_prices: dict[str, float]) -> float:
        """Cash + mark-to-market value of all open positions."""
        open_value = sum(
            pos.qty * mark_prices.get(pos.symbol, pos.entry_price)
            for pos in self.positions.values()
        )
        return self.cash + open_value

    def drawdown(self, mark_prices: dict[str, float]) -> float:
        """Current drawdown as fraction of peak: (equity - peak) / peak."""
        eq = self.equity(mark_prices)
        if self.peak_capital <= 0:
            return 0.0
        dd = (eq - self.peak_capital) / self.peak_capital
        return min(dd, 0.0)  # drawdown is non-positive
