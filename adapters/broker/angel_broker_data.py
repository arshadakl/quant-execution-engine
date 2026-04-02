"""AngelBrokerDataMixin — market data methods for AngelBroker.
Separated to keep angel_broker.py under 150 lines.
Requires self._smart (SmartConnect) and self.ensure_authenticated().
"""
import asyncio
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class AngelBrokerDataMixin:
    """Mixin providing market data methods backed by Angel One SmartAPI."""

    # ─── Interval mapping ───
    _INTERVAL_MAP: dict[str, str] = {
        "1m": "ONE_MINUTE",
        "3m": "THREE_MINUTE",
        "5m": "FIVE_MINUTE",
        "10m": "TEN_MINUTE",
        "15m": "FIFTEEN_MINUTE",
        "30m": "THIRTY_MINUTE",
        "1h": "ONE_HOUR",
        "1d": "ONE_DAY",
    }

    def _build_candle_params(
        self, token: str, interval: str, from_dt: datetime, to_dt: datetime
    ) -> dict:
        """Build Angel One candle data request params."""
        angel_interval = self._INTERVAL_MAP.get(interval)
        if not angel_interval:
            raise ValueError(
                f"Unsupported interval: {interval!r}. "
                f"Valid: {list(self._INTERVAL_MAP.keys())}"
            )
        return {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": angel_interval,
            "fromdate": from_dt.strftime("%Y-%m-%d %H:%M"),
            "todate": to_dt.strftime("%Y-%m-%d %H:%M"),
        }

    def _parse_candles(self, rows: list) -> "pd.DataFrame":
        """Convert raw candle rows to a timezone-aware IST DataFrame."""
        import pandas as pd
        if not rows:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df = pd.DataFrame(
            rows,
            columns=["timestamp", "open", "high", "low", "close", "volume"],
        )
        df["timestamp"] = (
            pd.to_datetime(df["timestamp"], utc=True)
            .dt.tz_convert("Asia/Kolkata")
            .dt.tz_localize(None)
        )
        return df.set_index("timestamp")

    async def get_historical(
        self,
        symbol: str,
        token: str,
        interval: str,
        from_dt: datetime,
        to_dt: datetime,
    ) -> "pd.DataFrame":
        """Fetch OHLCV candles. Returns DataFrame indexed by IST datetime.
        Columns: open, high, low, close, volume.
        """
        if not await self.ensure_authenticated():
            raise RuntimeError("Not authenticated — call login() first")
        params = self._build_candle_params(token, interval, from_dt, to_dt)
        response = await asyncio.to_thread(self._smart.getCandleData, params)
        return self._parse_candles(response.get("data") or [])

    async def get_ltp(
        self, symbol_token_pairs: list[tuple[str, str, str]]
    ) -> dict[str, float]:
        """Get LTP for multiple symbols. Returns {tradingsymbol: ltp}."""
        if not await self.ensure_authenticated():
            raise RuntimeError("Not authenticated — call login() first")
        result: dict[str, float] = {}
        for exchange, tradingsymbol, symboltoken in symbol_token_pairs:
            try:
                data = await asyncio.to_thread(
                    self._smart.ltpData, exchange, tradingsymbol, symboltoken
                )
                if data.get("status") and data.get("data"):
                    result[tradingsymbol] = float(data["data"]["ltp"])
            except Exception as exc:
                logger.warning("LTP fetch failed for %s: %s", tradingsymbol, exc)
        if len(result) < len(symbol_token_pairs):
            logger.warning(
                "LTP partial result: %d/%d symbols fetched",
                len(result), len(symbol_token_pairs),
            )
        return result

    async def get_funds(self) -> dict[str, Any]:
        """Get account margin and available cash."""
        if not await self.ensure_authenticated():
            raise RuntimeError("Not authenticated — call login() first")
        data = await asyncio.to_thread(self._smart.rmsLimit)
        return data.get("data") or {}

    async def get_positions(self) -> list[dict[str, Any]]:
        """Get all open positions from broker."""
        if not await self.ensure_authenticated():
            raise RuntimeError("Not authenticated — call login() first")
        data = await asyncio.to_thread(self._smart.position)
        return data.get("data") or []

    async def get_orders(self) -> list[dict[str, Any]]:
        """Get today's order book."""
        if not await self.ensure_authenticated():
            raise RuntimeError("Not authenticated — call login() first")
        data = await asyncio.to_thread(self._smart.orderBook)
        return data.get("data") or []
