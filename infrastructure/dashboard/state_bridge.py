"""Thread-safe shared state between trading bot and FastAPI dashboard."""
import copy
import threading
from typing import Any

_DEFAULTS: dict = {
    "positions": [],
    "signals": [],
    "history": [],
    "strategies": {"orb": True, "vwap": True, "momentum": True, "ema": True, "gap": True},
    "risk": {"max_daily_loss_pct": 0.03, "max_open_positions": 5},
    "summary": {"day_pnl": 0.0, "capital": 0.0, "open_count": 0},
    "mode": "paper",
    "kill_switch": False,
    "health": {},
}


class StateBridge:
    """Thread-safe key-value store. Bot writes, dashboard reads."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: dict = copy.deepcopy(_DEFAULTS)

    def get(self, key: str) -> Any:
        """Get value by key. Returns None if key missing."""
        with self._lock:
            return copy.deepcopy(self._data.get(key))

    def set(self, key: str, value: Any) -> None:
        """Set key-value pair. Thread-safe."""
        with self._lock:
            self._data[key] = value

    def snapshot(self) -> dict:
        """Return deep copy of all state. Safe for mutation."""
        with self._lock:
            return copy.deepcopy(self._data)

    def update_summary(
        self, day_pnl: float, capital: float, open_count: int
    ) -> None:
        """Replace summary metrics (day_pnl, capital, open_count)."""
        with self._lock:
            self._data["summary"] = {
                "day_pnl": day_pnl,
                "capital": capital,
                "open_count": open_count,
            }

    def update_health(self, health_monitor: Any) -> None:
        """Store health monitor status snapshot."""
        status = health_monitor.system_status()
        with self._lock:
            self._data["health"] = status
