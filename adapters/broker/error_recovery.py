"""Error recovery — exponential-backoff retry and in-memory state snapshot."""
import asyncio
import logging
import math
import random
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class ErrorRecovery:
    """Wraps async calls with retry logic and holds a recoverable state snapshot."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._snapshot: dict | None = None

    async def retry_async(self, fn: Callable[[], Coroutine], *args, **kwargs) -> Any:
        """Call fn (a coroutine factory or coroutine) with exponential-backoff retry."""
        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                # Support both callable and already-created coroutine
                coro = fn(*args, **kwargs) if callable(fn) else fn
                return await coro
            except Exception as exc:
                last_exc = exc
                if attempt == self.max_retries:
                    logger.error("retry exhausted after %d attempts: %s", attempt, exc)
                    break
                base = self.base_delay * (2 ** (attempt - 1))
                delay = min(base + random.uniform(0, base * 0.3), self.max_delay)
                logger.warning("attempt %d/%d failed (%s) — retrying in %.1fs",
                               attempt, self.max_retries, exc, delay)
                await asyncio.sleep(delay)
        raise last_exc  # type: ignore[misc]

    async def with_recovery(self, coro_fn: Callable[[], Coroutine]) -> Any:
        """Convenience wrapper: call coro_fn() with full retry logic."""
        return await self.retry_async(coro_fn)

    # ── State snapshot ──

    def save_state(self, state: dict) -> None:
        """Persist a shallow copy of state for crash recovery."""
        self._snapshot = dict(state)
        logger.info("state snapshot saved: %d keys", len(self._snapshot))

    def restore_state(self) -> dict | None:
        """Return the last saved snapshot, or None if none exists."""
        return self._snapshot

    def clear_state(self) -> None:
        """Discard the current snapshot."""
        self._snapshot = None
        logger.info("state snapshot cleared")
