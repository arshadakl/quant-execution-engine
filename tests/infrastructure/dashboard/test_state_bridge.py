import threading
from infrastructure.dashboard.state_bridge import StateBridge


def test_get_returns_default_empty_positions():
    b = StateBridge()
    assert b.get("positions") == []


def test_set_and_get_roundtrip():
    b = StateBridge()
    b.set("positions", [{"symbol": "RELIANCE"}])
    assert b.get("positions") == [{"symbol": "RELIANCE"}]


def test_snapshot_returns_copy():
    b = StateBridge()
    snap = b.snapshot()
    snap["positions"].append({"symbol": "FAKE"})
    assert b.get("positions") == []   # mutation of snap must not affect bridge


def test_concurrent_writes_do_not_corrupt():
    b = StateBridge()
    errors = []

    def writer(i):
        try:
            for _ in range(100):
                b.set("positions", [{"symbol": f"SYM{i}"}])
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == []


def test_update_summary_merges_fields():
    b = StateBridge()
    b.update_summary(day_pnl=1500.0, capital=101500.0, open_count=2)
    assert b.get("summary")["day_pnl"] == 1500.0
    assert b.get("summary")["open_count"] == 2


def test_update_health_stores_system_status():
    from unittest.mock import MagicMock
    b = StateBridge()
    monitor = MagicMock()
    monitor.system_status.return_value = {"broker": {"healthy": True, "last_seen": "2026-04-11T10:00:00"}}
    b.update_health(monitor)
    health = b.get("health")
    assert health == {"broker": {"healthy": True, "last_seen": "2026-04-11T10:00:00"}}
    monitor.system_status.assert_called_once()
