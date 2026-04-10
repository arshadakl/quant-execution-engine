"""Tests for Error Recovery — API failure handler, retry logic, state restore."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call


# ─── Instantiation ───

def test_instantiates_with_defaults():
    from adapters.broker.error_recovery import ErrorRecovery
    er = ErrorRecovery()
    assert er.max_retries == 3
    assert er.base_delay == 1.0
    assert er.max_delay == 30.0


def test_instantiates_with_custom_params():
    from adapters.broker.error_recovery import ErrorRecovery
    er = ErrorRecovery(max_retries=5, base_delay=2.0, max_delay=60.0)
    assert er.max_retries == 5
    assert er.base_delay == 2.0
    assert er.max_delay == 60.0


# ─── retry_async: success on first call ───

@pytest.mark.asyncio
async def test_retry_succeeds_on_first_attempt():
    from adapters.broker.error_recovery import ErrorRecovery
    er = ErrorRecovery()
    fn = AsyncMock(return_value="ok")
    result = await er.retry_async(fn)
    assert result == "ok"
    fn.assert_called_once()


@pytest.mark.asyncio
async def test_retry_returns_correct_value():
    from adapters.broker.error_recovery import ErrorRecovery
    er = ErrorRecovery()
    fn = AsyncMock(return_value={"orderid": "ORD001"})
    result = await er.retry_async(fn)
    assert result == {"orderid": "ORD001"}


# ─── retry_async: retry on failure ───

@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt():
    from adapters.broker.error_recovery import ErrorRecovery
    er = ErrorRecovery(max_retries=3, base_delay=0.0)
    fn = AsyncMock(side_effect=[Exception("timeout"), "ok"])
    result = await er.retry_async(fn)
    assert result == "ok"
    assert fn.call_count == 2


@pytest.mark.asyncio
async def test_retry_exhausts_all_attempts_then_raises():
    from adapters.broker.error_recovery import ErrorRecovery
    er = ErrorRecovery(max_retries=3, base_delay=0.0)
    fn = AsyncMock(side_effect=Exception("always fails"))
    with pytest.raises(Exception, match="always fails"):
        await er.retry_async(fn)
    assert fn.call_count == 3


@pytest.mark.asyncio
async def test_retry_count_matches_max_retries():
    from adapters.broker.error_recovery import ErrorRecovery
    er = ErrorRecovery(max_retries=5, base_delay=0.0)
    fn = AsyncMock(side_effect=RuntimeError("boom"))
    with pytest.raises(RuntimeError):
        await er.retry_async(fn)
    assert fn.call_count == 5


# ─── Exponential backoff (with zero delay for tests) ───

@pytest.mark.asyncio
async def test_retry_uses_exponential_backoff():
    from adapters.broker.error_recovery import ErrorRecovery
    er = ErrorRecovery(max_retries=3, base_delay=0.0)
    delays = []
    original_sleep = asyncio.sleep

    async def capture_sleep(delay):
        delays.append(delay)

    fn = AsyncMock(side_effect=[Exception("x"), Exception("x"), "ok"])
    with patch("asyncio.sleep", side_effect=capture_sleep):
        result = await er.retry_async(fn)

    assert result == "ok"
    # Second attempt delay >= first attempt delay (exponential)
    assert len(delays) == 2
    assert delays[1] >= delays[0]


@pytest.mark.asyncio
async def test_retry_delay_capped_at_max_delay():
    from adapters.broker.error_recovery import ErrorRecovery
    er = ErrorRecovery(max_retries=10, base_delay=10.0, max_delay=5.0)
    delays = []

    async def capture_sleep(delay):
        delays.append(delay)

    fn = AsyncMock(side_effect=[Exception("x")] * 9 + ["ok"])
    with patch("asyncio.sleep", side_effect=capture_sleep):
        await er.retry_async(fn)

    assert all(d <= 5.0 for d in delays)


# ─── with_recovery decorator ───

@pytest.mark.asyncio
async def test_with_recovery_wraps_coroutine():
    from adapters.broker.error_recovery import ErrorRecovery
    er = ErrorRecovery(max_retries=2, base_delay=0.0)
    call_count = 0

    async def fragile():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("dropped")
        return "recovered"

    result = await er.with_recovery(fragile)
    assert result == "recovered"
    assert call_count == 2


@pytest.mark.asyncio
async def test_with_recovery_raises_after_exhaustion():
    from adapters.broker.error_recovery import ErrorRecovery
    er = ErrorRecovery(max_retries=2, base_delay=0.0)

    async def always_fails():
        raise ConnectionError("dead")

    with pytest.raises(ConnectionError):
        await er.with_recovery(always_fails)


# ─── State snapshot ───

def test_save_and_restore_state():
    from adapters.broker.error_recovery import ErrorRecovery
    er = ErrorRecovery()
    state = {"positions": [{"symbol": "RELIANCE", "qty": 10}], "day_pnl": 500.0}
    er.save_state(state)
    restored = er.restore_state()
    assert restored == state


def test_restore_state_returns_none_when_no_snapshot():
    from adapters.broker.error_recovery import ErrorRecovery
    er = ErrorRecovery()
    assert er.restore_state() is None


def test_clear_state_removes_snapshot():
    from adapters.broker.error_recovery import ErrorRecovery
    er = ErrorRecovery()
    er.save_state({"x": 1})
    er.clear_state()
    assert er.restore_state() is None


def test_save_state_overwrites_previous():
    from adapters.broker.error_recovery import ErrorRecovery
    er = ErrorRecovery()
    er.save_state({"v": 1})
    er.save_state({"v": 2})
    assert er.restore_state()["v"] == 2
