"""Telegram notifier — trade alerts, daily summary, kill switch and error notifications."""
import logging
from core.entities.signal import Signal

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier:
    """Sends formatted messages to a Telegram chat via Bot API."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = bool(bot_token)

    async def send_message(self, text: str) -> None:
        """Send a plain-text message; swallows errors to never crash the main flow."""
        if not self.enabled:
            return
        try:
            await self._post(text)
        except Exception as exc:
            logger.error("telegram send failed: %s", exc)

    async def notify_entry(self, signal: Signal, qty: int, fill_price: float) -> None:
        icon = "🟢" if signal.direction == "LONG" else "🔴"
        text = (
            f"{icon} ENTRY  {signal.direction} {signal.symbol}\n"
            f"Fill: ₹{fill_price:.2f}  Qty: {qty}\n"
            f"SL: ₹{signal.stop_loss:.2f}  Target: ₹{signal.target_1:.2f}\n"
            f"Strategy: {signal.strategy}"
        )
        await self.send_message(text)

    async def notify_exit(self, symbol: str, exit_price: float, pnl: float) -> None:
        icon = "✅" if pnl >= 0 else "❌"
        sign = "+" if pnl >= 0 else ""
        text = (
            f"{icon} EXIT  {symbol}\n"
            f"Price: ₹{exit_price:.2f}  P&L: {sign}₹{pnl:.2f}"
        )
        await self.send_message(text)

    async def notify_kill_switch(self, day_pnl: float) -> None:
        text = (
            f"🚨 KILL SWITCH TRIGGERED\n"
            f"Daily loss limit breached — all trading halted.\n"
            f"Day P&L: ₹{day_pnl:,.2f}"
        )
        await self.send_message(text)

    async def notify_error(self, context: str, error: str) -> None:
        text = f"⚠️ ERROR [{context}]\n{error}"
        await self.send_message(text)

    async def notify_daily_summary(
        self,
        day_pnl: float,
        total_trades: int,
        win_rate: float,
        capital: float,
    ) -> None:
        sign = "+" if day_pnl >= 0 else ""
        text = (
            f"📊 DAILY SUMMARY\n"
            f"P&L: {sign}₹{day_pnl:,.2f}\n"
            f"Trades: {total_trades}  Win Rate: {win_rate*100:.1f}%\n"
            f"Capital: ₹{capital:,.2f}"
        )
        await self.send_message(text)

    async def _post(self, text: str) -> None:
        """HTTP POST to Telegram Bot API (imported lazily to avoid hard dep in tests)."""
        import httpx
        url = _TELEGRAM_API.format(token=self.bot_token)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={"chat_id": self.chat_id, "text": text})
            resp.raise_for_status()
