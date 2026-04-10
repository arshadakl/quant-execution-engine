"""Tests for Scheduler jobs."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import time


# ─── Instantiation ───

def test_instantiates_with_defaults():
    from infrastructure.scheduler.jobs import JobScheduler
    js = JobScheduler()
    assert js.scan_time == time(8, 50)
    assert js.strategy_interval_seconds == 60
    assert js.square_off_time == time(15, 10)


def test_instantiates_with_custom_params():
    from infrastructure.scheduler.jobs import JobScheduler
    js = JobScheduler(
        scan_time=time(9, 0),
        strategy_interval_seconds=30,
        square_off_time=time(15, 0),
    )
    assert js.scan_time == time(9, 0)
    assert js.strategy_interval_seconds == 30
    assert js.square_off_time == time(15, 0)


# ─── Scheduler lifecycle ───

def test_start_starts_apscheduler():
    from infrastructure.scheduler.jobs import JobScheduler
    js = JobScheduler()
    with patch.object(js._scheduler, "start") as mock_start:
        js.start()
        mock_start.assert_called_once()


def test_stop_stops_apscheduler():
    from infrastructure.scheduler.jobs import JobScheduler
    js = JobScheduler()
    with patch.object(js._scheduler, "shutdown") as mock_stop:
        js.stop()
        mock_stop.assert_called_once()


# ─── Job registration ───

def test_register_scanner_job():
    from infrastructure.scheduler.jobs import JobScheduler
    js = JobScheduler()
    fn = MagicMock()
    js.register_scanner_job(fn)
    jobs = js._scheduler.get_jobs()
    assert any(j.func is fn or j.func.__wrapped__ is fn
               for j in jobs
               if hasattr(j, "func") and j.func is not None
               ) or len(jobs) >= 1  # job exists


def test_register_strategy_loop_job():
    from infrastructure.scheduler.jobs import JobScheduler
    js = JobScheduler()
    fn = MagicMock()
    js.register_strategy_loop(fn)
    jobs = js._scheduler.get_jobs()
    assert len(jobs) >= 1


def test_register_square_off_job():
    from infrastructure.scheduler.jobs import JobScheduler
    js = JobScheduler()
    fn = MagicMock()
    js.register_square_off_job(fn)
    jobs = js._scheduler.get_jobs()
    assert len(jobs) >= 1


def test_register_daily_report_job():
    from infrastructure.scheduler.jobs import JobScheduler
    js = JobScheduler()
    fn = MagicMock()
    js.register_daily_report_job(fn)
    jobs = js._scheduler.get_jobs()
    assert len(jobs) >= 1


# ─── Multiple registrations add multiple jobs ───

def test_multiple_registrations_stack():
    from infrastructure.scheduler.jobs import JobScheduler
    js = JobScheduler()
    js.register_scanner_job(MagicMock())
    js.register_strategy_loop(MagicMock())
    js.register_square_off_job(MagicMock())
    js.register_daily_report_job(MagicMock())
    assert len(js._scheduler.get_jobs()) == 4


# ─── Remove all jobs ───

def test_remove_all_jobs_clears_scheduler():
    from infrastructure.scheduler.jobs import JobScheduler
    js = JobScheduler()
    js.register_scanner_job(MagicMock())
    js.register_strategy_loop(MagicMock())
    js.remove_all_jobs()
    assert len(js._scheduler.get_jobs()) == 0
