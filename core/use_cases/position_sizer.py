"""Position sizer — risk-based quantity calculator."""
import logging
import math

logger = logging.getLogger(__name__)


class PositionSizer:
    """Calculate share quantity using fixed-risk formula: risk_amount / sl_distance."""

    def __init__(self, risk_pct: float = 0.01, max_qty: int = 500) -> None:
        self.risk_pct = risk_pct
        self.max_qty = max_qty

    def calculate(self, capital: float, entry: float, stop_loss: float) -> int:
        """Return integer share quantity, capped at max_qty."""
        if capital <= 0:
            return 0
        sl_distance = entry - stop_loss
        if sl_distance <= 0:
            return 0
        risk_amount = capital * self.risk_pct
        qty = int(math.floor(risk_amount / sl_distance))
        qty = min(qty, self.max_qty)
        logger.debug(
            "position size: capital=%.0f risk=%.0f sl_dist=%.2f qty=%d",
            capital, risk_amount, sl_distance, qty,
        )
        return qty
