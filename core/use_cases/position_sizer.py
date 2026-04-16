"""Position sizer — risk-based quantity calculator with capital percentage cap."""
import logging
import math

logger = logging.getLogger(__name__)


class PositionSizer:
    """Calculate share quantity using fixed-risk formula with a capital percentage cap.

    Formula:
        risk_qty       = floor( capital * risk_pct / (entry - stop_loss) )
        max_by_capital = floor( capital * max_position_size_pct / entry )
        final_qty      = min( risk_qty, max_by_capital, max_qty )

    This prevents a tiny SL distance from inflating quantity beyond what the
    capital allocation policy allows.
    """

    def __init__(
        self,
        risk_pct: float = 0.01,
        max_qty: int = 500,
        max_position_size_pct: float = 0.15,
    ) -> None:
        self.risk_pct = risk_pct
        self.max_qty = max_qty
        self.max_position_size_pct = max_position_size_pct

    def calculate(self, capital: float, entry: float, stop_loss: float) -> int:
        """Return integer share quantity, capped by risk, capital %, and max_qty."""
        if capital <= 0:
            return 0
        sl_distance = entry - stop_loss
        if sl_distance <= 0:
            return 0
        risk_amount = capital * self.risk_pct
        risk_qty = int(math.floor(risk_amount / sl_distance))
        max_by_capital = int(math.floor(capital * self.max_position_size_pct / entry))
        qty = min(risk_qty, max_by_capital, self.max_qty)
        logger.debug(
            "position size: capital=%.0f risk_qty=%d cap_qty=%d qty=%d",
            capital, risk_qty, max_by_capital, qty,
        )
        return qty
