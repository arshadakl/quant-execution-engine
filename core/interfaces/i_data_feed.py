"""IDataFeed protocol — real-time tick subscription interface."""
from typing import Callable, Protocol, runtime_checkable


@runtime_checkable
class IDataFeed(Protocol):
    """Protocol for real-time market data feed."""

    def set_tick_callback(self, callback: Callable[[dict], None]) -> None:
        """Register callback invoked on every incoming tick."""
        ...

    async def connect(self) -> None:
        """Establish WebSocket connection."""
        ...

    def subscribe(self, tokens: list[dict]) -> None:
        """Subscribe to tick data.
        tokens: [{"exchangeType": 1, "tokens": ["2885", "1594"]}]
        """
        ...

    async def disconnect(self) -> None:
        """Close WebSocket connection gracefully."""
        ...
