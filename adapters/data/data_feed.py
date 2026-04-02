"""DataFeed — real-time WebSocket tick subscription via Angel One SmartWebSocketV2.
Implements IDataFeed protocol.
"""
import asyncio
import logging
from typing import Callable, Optional

from SmartApi.smartWebSocketV2 import SmartWebSocketV2

logger = logging.getLogger(__name__)

_SUBSCRIPTION_MODE = 1          # LTP mode (1=LTP, 2=QUOTE, 3=SNAP_QUOTE)
_SESSION_CORRELATION = "algo-feed"
_MAX_RETRY = 5


class DataFeed:
    """WebSocket tick feed with auto-resubscription on reconnect.
    Implements IDataFeed protocol.
    """

    def __init__(
        self,
        auth_token: str,
        api_key: str,
        client_id: str,
        feed_token: str,
    ) -> None:
        self._auth_token = auth_token
        self._api_key = api_key
        self._client_id = client_id
        self._feed_token = feed_token
        self._sws: Optional[SmartWebSocketV2] = None
        self._tick_callback: Optional[Callable[[dict], None]] = None
        self._subscribed_tokens: list[dict] = []

    def set_tick_callback(self, callback: Callable[[dict], None]) -> None:
        """Register callback invoked on every incoming tick."""
        self._tick_callback = callback

    async def connect(self) -> None:
        """Initialize WebSocket and start connection in background thread."""
        self._sws = SmartWebSocketV2(
            self._auth_token,
            self._api_key,
            self._client_id,
            self._feed_token,
            max_retry_attempt=_MAX_RETRY,
        )
        self._sws.on_open = self._on_open
        self._sws.on_data = self._on_data
        self._sws.on_error = self._on_error
        self._sws.on_close = self._on_close
        await asyncio.to_thread(self._sws.connect)

    def subscribe(self, tokens: list[dict]) -> None:
        """Subscribe to tick stream.
        tokens: [{"exchangeType": 1, "tokens": ["2885", "1594"]}]
        """
        self._subscribed_tokens = tokens
        if self._sws:
            self._sws.subscribe(_SESSION_CORRELATION, _SUBSCRIPTION_MODE, tokens)

    async def disconnect(self) -> None:
        """Close WebSocket connection gracefully."""
        if self._sws:
            await asyncio.to_thread(self._sws.close_connection)
            self._sws = None
            logger.info("DataFeed disconnected")

    # ─── Internal WebSocket callbacks ───

    def _on_open(self, wsapp) -> None:
        logger.info("WebSocket connected")
        if self._subscribed_tokens and self._sws:
            self._sws.subscribe(
                _SESSION_CORRELATION, _SUBSCRIPTION_MODE, self._subscribed_tokens
            )

    def _on_data(self, wsapp, message: dict) -> None:
        if self._tick_callback:
            self._tick_callback(message)

    def _on_error(self, wsapp, error) -> None:
        logger.error("WebSocket error: %s", error)

    def _on_close(self, wsapp, close_status_code, close_msg) -> None:
        logger.warning(
            "WebSocket closed: status=%s msg=%s", close_status_code, close_msg
        )
