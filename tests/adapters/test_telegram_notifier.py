"""Tests for Telegram Notifier."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from core.entities.signal import Signal


def _make_signal(symbol: str = "RELIANCE", direction: str = "LONG") -> Signal:
    return Signal(
        symbol=symbol, direction=direction,
        entry_price=500.0, stop_loss=490.0, target_1=520.0,
        timestamp=datetime(2026, 1, 2, 10, 0), strategy="ORB",
    )


# ─── Instantiation ───

def test_instantiates_with_token_and_chat():
    from adapters.notifications.telegram_notifier import TelegramNotifier
    tn = TelegramNotifier(bot_token="abc:123", chat_id="456")
    assert tn.bot_token == "abc:123"
    assert tn.chat_id == "456"


def test_instantiates_disabled_when_no_token():
    from adapters.notifications.telegram_notifier import TelegramNotifier
    tn = TelegramNotifier(bot_token="", chat_id="456")
    assert tn.enabled is False


def test_instantiates_enabled_when_token_set():
    from adapters.notifications.telegram_notifier import TelegramNotifier
    tn = TelegramNotifier(bot_token="abc:123", chat_id="456")
    assert tn.enabled is True


# ─── send_message ───

@pytest.mark.asyncio
async def test_send_message_calls_telegram_api():
    from adapters.notifications.telegram_notifier import TelegramNotifier
    tn = TelegramNotifier(bot_token="tok", chat_id="123")
    with patch.object(tn, "_post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = True
        await tn.send_message("hello")
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_send_message_skipped_when_disabled():
    from adapters.notifications.telegram_notifier import TelegramNotifier
    tn = TelegramNotifier(bot_token="", chat_id="123")
    with patch.object(tn, "_post", new_callable=AsyncMock) as mock_post:
        await tn.send_message("hello")
        mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_send_message_does_not_raise_on_api_error():
    from adapters.notifications.telegram_notifier import TelegramNotifier
    tn = TelegramNotifier(bot_token="tok", chat_id="123")
    with patch.object(tn, "_post", new_callable=AsyncMock, side_effect=Exception("network")):
        # Should swallow the error — notifier must never crash the main flow
        await tn.send_message("hello")


# ─── Trade entry notification ───

@pytest.mark.asyncio
async def test_notify_entry_sends_message():
    from adapters.notifications.telegram_notifier import TelegramNotifier
    tn = TelegramNotifier(bot_token="tok", chat_id="123")
    with patch.object(tn, "send_message", new_callable=AsyncMock) as mock_send:
        sig = _make_signal("RELIANCE", "LONG")
        await tn.notify_entry(signal=sig, qty=10, fill_price=501.0)
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "RELIANCE" in text
        assert "LONG" in text


@pytest.mark.asyncio
async def test_notify_entry_includes_fill_price():
    from adapters.notifications.telegram_notifier import TelegramNotifier
    tn = TelegramNotifier(bot_token="tok", chat_id="123")
    with patch.object(tn, "send_message", new_callable=AsyncMock) as mock_send:
        sig = _make_signal()
        await tn.notify_entry(signal=sig, qty=10, fill_price=501.5)
        text = mock_send.call_args[0][0]
        assert "501" in text


# ─── Trade exit notification ───

@pytest.mark.asyncio
async def test_notify_exit_sends_message():
    from adapters.notifications.telegram_notifier import TelegramNotifier
    tn = TelegramNotifier(bot_token="tok", chat_id="123")
    with patch.object(tn, "send_message", new_callable=AsyncMock) as mock_send:
        await tn.notify_exit(symbol="RELIANCE", exit_price=520.0, pnl=200.0)
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "RELIANCE" in text
        assert "200" in text


@pytest.mark.asyncio
async def test_notify_exit_shows_loss():
    from adapters.notifications.telegram_notifier import TelegramNotifier
    tn = TelegramNotifier(bot_token="tok", chat_id="123")
    with patch.object(tn, "send_message", new_callable=AsyncMock) as mock_send:
        await tn.notify_exit(symbol="TCS", exit_price=490.0, pnl=-100.0)
        text = mock_send.call_args[0][0]
        assert "100" in text


# ─── Kill switch alert ───

@pytest.mark.asyncio
async def test_notify_kill_switch_sends_urgent_message():
    from adapters.notifications.telegram_notifier import TelegramNotifier
    tn = TelegramNotifier(bot_token="tok", chat_id="123")
    with patch.object(tn, "send_message", new_callable=AsyncMock) as mock_send:
        await tn.notify_kill_switch(day_pnl=-3100.0)
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "3100" in text or "kill" in text.lower() or "KILL" in text


# ─── Error alert ───

@pytest.mark.asyncio
async def test_notify_error_sends_message():
    from adapters.notifications.telegram_notifier import TelegramNotifier
    tn = TelegramNotifier(bot_token="tok", chat_id="123")
    with patch.object(tn, "send_message", new_callable=AsyncMock) as mock_send:
        await tn.notify_error(context="broker login", error="TokenExpired")
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "TokenExpired" in text or "broker login" in text


# ─── Daily summary ───

@pytest.mark.asyncio
async def test_notify_daily_summary_sends_message():
    from adapters.notifications.telegram_notifier import TelegramNotifier
    tn = TelegramNotifier(bot_token="tok", chat_id="123")
    with patch.object(tn, "send_message", new_callable=AsyncMock) as mock_send:
        await tn.notify_daily_summary(
            day_pnl=1500.0, total_trades=8, win_rate=0.625, capital=101_500.0
        )
        mock_send.assert_called_once()
        text = mock_send.call_args[0][0]
        assert "1500" in text or "1,500" in text
