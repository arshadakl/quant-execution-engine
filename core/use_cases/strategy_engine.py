"""Strategy engine — runs multiple strategies and aggregates signals."""
import logging
import pandas as pd
from core.entities.signal import Signal

logger = logging.getLogger(__name__)


class StrategyEngine:
    """Runs each enabled strategy against a symbol's DataFrame and collects signals."""

    def __init__(
        self,
        strategies: list,
        enabled: dict[str, bool] | None = None,
    ) -> None:
        self.strategies = strategies
        self._enabled = enabled or {}

    def run(self, symbol: str, df: pd.DataFrame) -> list[Signal]:
        """Return all signals produced by enabled strategies for the given symbol/df."""
        signals: list[Signal] = []
        for strategy in self.strategies:
            if not self._enabled.get(strategy.name, True):
                logger.debug("strategy %s is disabled, skipping", strategy.name)
                continue
            try:
                new = strategy.generate_signals(df, symbol)
                signals.extend(new)
            except Exception as exc:
                logger.error("strategy %s raised %s: %s", strategy.name, type(exc).__name__, exc)
        return signals
