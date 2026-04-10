"""Tests for Health Monitor."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


# ─── Instantiation ───

def test_instantiates_with_defaults():
    from infrastructure.health_monitor import HealthMonitor
    hm = HealthMonitor()
    assert hm.heartbeat_interval == 30
    assert hm.stale_threshold == 90


def test_instantiates_with_custom_params():
    from infrastructure.health_monitor import HealthMonitor
    hm = HealthMonitor(heartbeat_interval=60, stale_threshold=180)
    assert hm.heartbeat_interval == 60
    assert hm.stale_threshold == 180


# ─── Heartbeat ───

def test_record_heartbeat_updates_timestamp():
    from infrastructure.health_monitor import HealthMonitor
    hm = HealthMonitor()
    before = datetime.now()
    hm.record_heartbeat("broker")
    assert hm.last_heartbeat("broker") >= before


def test_last_heartbeat_returns_none_for_unknown_component():
    from infrastructure.health_monitor import HealthMonitor
    hm = HealthMonitor()
    assert hm.last_heartbeat("unknown") is None


def test_record_heartbeat_updates_existing():
    from infrastructure.health_monitor import HealthMonitor
    hm = HealthMonitor()
    hm.record_heartbeat("broker")
    first = hm.last_heartbeat("broker")
    hm.record_heartbeat("broker")
    second = hm.last_heartbeat("broker")
    assert second >= first


# ─── is_healthy ───

def test_is_healthy_true_for_recent_heartbeat():
    from infrastructure.health_monitor import HealthMonitor
    hm = HealthMonitor(stale_threshold=90)
    hm.record_heartbeat("broker")
    assert hm.is_healthy("broker") is True


def test_is_healthy_false_for_stale_heartbeat():
    from infrastructure.health_monitor import HealthMonitor
    hm = HealthMonitor(stale_threshold=90)
    stale_time = datetime.now() - timedelta(seconds=100)
    hm._heartbeats["broker"] = stale_time
    assert hm.is_healthy("broker") is False


def test_is_healthy_false_for_unknown_component():
    from infrastructure.health_monitor import HealthMonitor
    hm = HealthMonitor()
    assert hm.is_healthy("never_registered") is False


def test_is_healthy_at_exact_threshold_is_false():
    from infrastructure.health_monitor import HealthMonitor
    hm = HealthMonitor(stale_threshold=90)
    hm._heartbeats["broker"] = datetime.now() - timedelta(seconds=90)
    assert hm.is_healthy("broker") is False


# ─── system_status ───

def test_system_status_returns_dict():
    from infrastructure.health_monitor import HealthMonitor
    hm = HealthMonitor()
    hm.record_heartbeat("broker")
    hm.record_heartbeat("websocket")
    status = hm.system_status()
    assert isinstance(status, dict)
    assert "broker" in status
    assert "websocket" in status


def test_system_status_healthy_components():
    from infrastructure.health_monitor import HealthMonitor
    hm = HealthMonitor()
    hm.record_heartbeat("broker")
    status = hm.system_status()
    assert status["broker"]["healthy"] is True


def test_system_status_stale_component():
    from infrastructure.health_monitor import HealthMonitor
    hm = HealthMonitor(stale_threshold=90)
    hm._heartbeats["broker"] = datetime.now() - timedelta(seconds=120)
    status = hm.system_status()
    assert status["broker"]["healthy"] is False


def test_system_status_includes_last_seen():
    from infrastructure.health_monitor import HealthMonitor
    hm = HealthMonitor()
    hm.record_heartbeat("broker")
    status = hm.system_status()
    assert "last_seen" in status["broker"]


# ─── all_healthy ───

def test_all_healthy_true_when_all_ok():
    from infrastructure.health_monitor import HealthMonitor
    hm = HealthMonitor()
    hm.record_heartbeat("broker")
    hm.record_heartbeat("websocket")
    assert hm.all_healthy() is True


def test_all_healthy_false_when_one_stale():
    from infrastructure.health_monitor import HealthMonitor
    hm = HealthMonitor(stale_threshold=90)
    hm.record_heartbeat("broker")
    hm._heartbeats["websocket"] = datetime.now() - timedelta(seconds=200)
    assert hm.all_healthy() is False


def test_all_healthy_true_when_no_components():
    from infrastructure.health_monitor import HealthMonitor
    hm = HealthMonitor()
    assert hm.all_healthy() is True
