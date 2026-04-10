"""Scanner ranker — applies filters and ranks candidates by composite score."""
import logging
import pandas as pd
from adapters.scanner.filters.volatility import compute_atr

logger = logging.getLogger(__name__)

_ATR_PERIOD = 14


def _score(df: pd.DataFrame) -> float:
    """Composite score: normalised volume * ATR% — higher is better."""
    if df.empty or len(df) < 2:
        return 0.0
    avg_vol = float(df["volume"].mean())
    last_close = float(df["close"].iloc[-1])
    if last_close == 0:
        return 0.0
    period = min(_ATR_PERIOD, len(df))
    atr_pct = float(compute_atr(df, period).iloc[-1]) / last_close
    return avg_vol * atr_pct


class ScannerRanker:
    """Apply filters to a symbol→DataFrame map and return top-N ranked symbols."""

    def __init__(
        self,
        filters: list | None = None,
        max_stocks: int = 15,
    ) -> None:
        self.filters = filters or []
        self.max_stocks = max_stocks

    def scan(self, candidates: dict[str, pd.DataFrame]) -> list[str]:
        """Return up to max_stocks symbols that pass all filters, ranked by score."""
        if not candidates:
            return []

        passed: list[tuple[float, str]] = []
        for symbol, df in candidates.items():
            if all(f.passes(df, symbol) for f in self.filters):
                passed.append((_score(df), symbol))
            else:
                logger.debug("%s filtered out", symbol)

        passed.sort(key=lambda t: t[0], reverse=True)
        return [sym for _, sym in passed[: self.max_stocks]]
