"""TradingBot — wires all trading components into a single async orchestrator."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from core.entities.signal import Signal
from core.use_cases.risk_manager import RiskState
from infrastructure.dashboard.state_bridge import StateBridge

logger = logging.getLogger(__name__)

_CANDLE_INTERVAL = "5m"
_HISTORY_HOURS = 6  # fetch last 6h of candles for strategy analysis


class TradingBot:
    """Connects broker, strategies, risk, position sizer, paper trader, and dashboard."""

    def __init__(
        self,
        mode: str,
        broker: Any,
        strategy_engine: Any,
        risk_manager: Any,
        position_sizer: Any,
        paper_trader: Any,
        telegram: Any,
        health_monitor: Any,
        state_bridge: StateBridge,
        symbol_tokens: dict[str, str],
    ) -> None:
        self.mode = mode
        self.broker = broker
        self.strategy_engine = strategy_engine
        self.risk_manager = risk_manager
        self.position_sizer = position_sizer
        self.paper_trader = paper_trader
        self.telegram = telegram
        self.health_monitor = health_monitor
        self.state_bridge = state_bridge
        self.symbol_tokens = symbol_tokens
        self._risk_state = RiskState()
        self._stop = asyncio.Event()
        state_bridge.set("mode", mode)

    # ── Public controls ────────────────────────────────────────────────────

    def set_kill_switch(self, active: bool) -> None:
        """Activate or deactivate the kill switch."""
        self._risk_state.kill_switch = active
        self.state_bridge.set("kill_switch", active)
        logger.warning("kill switch set to %s", active)

    def toggle_strategy(self, name: str, enabled: bool) -> None:
        """Enable or disable a strategy by name."""
        self.strategy_engine._enabled[name] = enabled
        strategies = dict(self.state_bridge.get("strategies") or {})
        strategies[name] = enabled
        self.state_bridge.set("strategies", strategies)

    async def run_loop(self, interval_seconds: int = 60) -> None:
        """Strategy loop — runs until stop() is called."""
        logger.info("trading bot loop started (mode=%s)", self.mode)
        while not self._stop.is_set():
            try:
                await self._strategy_cycle()
            except Exception as exc:
                logger.error("strategy cycle error: %s", exc)
                await self.telegram.notify_error("strategy_cycle", str(exc))
            await asyncio.sleep(interval_seconds)

    def stop(self) -> None:
        """Signal the run_loop to exit after current cycle."""
        self._stop.set()

    # ── Core cycle ─────────────────────────────────────────────────────────

    async def _strategy_cycle(self) -> None:
        """One tick: fetch data, generate signals, validate, fill, update dashboard."""
        now = datetime.now()
        ltp_map: dict[str, float] = {}
        pending_signals: list[Signal] = []

        for symbol, token in self.symbol_tokens.items():
            try:
                df = await self.broker.get_historical(
                    symbol, token, _CANDLE_INTERVAL,
                    now - timedelta(hours=_HISTORY_HOURS), now,
                )
                if df.empty or len(df) < 10:
                    continue
                signals = self.strategy_engine.run(symbol, df)
                pending_signals.extend(signals)
                ltp_map[symbol] = float(df["close"].iloc[-1])
            except Exception as exc:
                logger.error("data/strategy error for %s: %s", symbol, exc)

        self.health_monitor.record_heartbeat("strategy_loop")
        self.state_bridge.set("signals", [
            {
                "symbol": s.symbol,
                "direction": s.direction,
                "strategy": s.strategy,
                "entry": s.entry_price,
                "sl": s.stop_loss,
                "target": s.target_1,
            }
            for s in pending_signals
        ])

        for signal in pending_signals:
            ok, reason = self.risk_manager.validate(
                self._risk_state, self.paper_trader.capital, signal.timestamp
            )
            if not ok:
                logger.debug("signal rejected (%s): %s %s", reason, signal.direction, signal.symbol)
                continue

            qty = self.position_sizer.calculate(
                self.paper_trader.capital, signal.entry_price, signal.stop_loss
            )
            if qty <= 0:
                continue

            fill_price = ltp_map.get(signal.symbol, signal.entry_price)
            self.paper_trader.fill(signal, qty, fill_price)
            self._risk_state.last_trade_time = now
            await self.telegram.notify_entry(signal, qty, fill_price)

        self._update_dashboard_state(ltp_map)

    def _update_dashboard_state(self, ltp_map: dict[str, float]) -> None:
        """Push current paper trader state into the state bridge."""
        raw = self.paper_trader.open_trades()
        positions = []
        for t in raw:
            ltp = ltp_map.get(t["symbol"], t["entry_price"])
            mult = 1 if t["direction"] == "LONG" else -1
            pnl = round(mult * (ltp - t["entry_price"]) * t["qty"], 2)
            positions.append({**t, "current_price": ltp, "pnl": pnl})

        day_pnl = self.paper_trader.day_pnl()
        self._risk_state.daily_pnl = day_pnl

        self._risk_state.open_positions = len(positions)
        self.state_bridge.set("positions", positions)
        self.state_bridge.update_summary(
            day_pnl=day_pnl,
            capital=self.paper_trader.capital,
            open_count=len(positions),
        )
        self.state_bridge.update_health(self.health_monitor)
