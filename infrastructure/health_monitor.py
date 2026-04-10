"""Health monitor — component heartbeat tracking and staleness detection."""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Tracks last-seen timestamps for named components; reports staleness."""

    def __init__(
        self,
        heartbeat_interval: int = 30,
        stale_threshold: int = 90,
    ) -> None:
        self.heartbeat_interval = heartbeat_interval
        self.stale_threshold = stale_threshold
        self._heartbeats: dict[str, datetime] = {}

    def record_heartbeat(self, component: str) -> None:
        """Update the last-seen timestamp for a component."""
        self._heartbeats[component] = datetime.now()
        logger.debug("heartbeat: %s", component)

    def last_heartbeat(self, component: str) -> datetime | None:
        """Return the last heartbeat time, or None if never recorded."""
        return self._heartbeats.get(component)

    def is_healthy(self, component: str) -> bool:
        """Return True if the component has a heartbeat within stale_threshold seconds."""
        ts = self._heartbeats.get(component)
        if ts is None:
            return False
        age = (datetime.now() - ts).total_seconds()
        return age < self.stale_threshold

    def system_status(self) -> dict[str, dict]:
        """Return a dict of {component: {healthy, last_seen}} for all components."""
        return {
            name: {
                "healthy": self.is_healthy(name),
                "last_seen": ts.isoformat(),
            }
            for name, ts in self._heartbeats.items()
        }

    def all_healthy(self) -> bool:
        """Return True if every registered component is currently healthy."""
        return all(self.is_healthy(name) for name in self._heartbeats)
