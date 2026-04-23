"""TradingBot — wires all trading components into a single async orchestrator."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from adapters.broker.error_recovery import ErrorRecovery
from core.entities.signal import Signal
from core.use_cases.risk_manager import RiskState
from infrastructure.dashboard.state_bridge import StateBridge

logger = logging.getLogger(__name__)

_CANDLE_INTERVAL = "5m"
_HISTORY_HOURS = 2  # 2h sufficient for all strategies; cuts API payload


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
        execution_engine: Any = None,
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
        self.execution_engine = execution_engine
        self._risk_state = RiskState()
        self._stop = asyncio.Event()
        self._recovery = ErrorRecovery(max_retries=3, base_delay=3.0, max_delay=15.0)
        self._symbol_delay: float = 3.5  # inter-symbol sleep; override in tests
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
                df = await self._recovery.retry_async(
                    self.broker.get_historical,
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
            await asyncio.sleep(self._symbol_delay)  # Angel One historical: ~0.3 req/s

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
            if self.mode == "live" and self.execution_engine is not None:
                token = self.symbol_tokens.get(signal.symbol, "")
                await self.execution_engine.place_entry(signal, qty, token)
                await self.execution_engine.place_sl_order(signal, qty, token)
            self.paper_trader.fill(signal, qty, fill_price)
            self._risk_state.last_trade_time = now
            self._risk_state.daily_trades += 1
            # update open_positions mid-cycle so subsequent signals see the accurate count
            self._risk_state.open_positions += 1
            await self.telegram.notify_entry(signal, qty, fill_price)

        await self._refresh_position_ltps(ltp_map)
        self._update_dashboard_state(ltp_map)

    async def _refresh_position_ltps(self, ltp_map: dict[str, float]) -> None:
        """Fetch real-time LTP for open positions and update ltp_map in place."""
        open_trades = self.paper_trader.open_trades()
        if not open_trades:
            return
        pairs = [
            ("NSE", t["symbol"], self.symbol_tokens[t["symbol"]])
            for t in open_trades
            if t["symbol"] in self.symbol_tokens
        ]
        if not pairs:
            return
        try:
            live_ltp = await self.broker.get_ltp(pairs)
            ltp_map.update(live_ltp)
        except Exception as exc:
            logger.warning("position LTP refresh failed: %s", exc)

    def _update_dashboard_state(self, ltp_map: dict[str, float]) -> None:
        """Push current paper trader state into the state bridge."""
        raw = self.paper_trader.open_trades()
        positions = []
        for t in raw:
            ltp = ltp_map.get(t["symbol"], t["entry_price"])
            mult = 1 if t["direction"] == "LONG" else -1
            pnl = round(mult * (ltp - t["entry_price"]) * t["qty"], 2)
            target_pct = round(
                mult * (t["target_1"] - t["entry_price"]) / t["entry_price"] * 100, 1
            )
            positions.append({**t, "current_price": ltp, "pnl": pnl, "target_pct": target_pct})

        realized_pnl = self.paper_trader.day_pnl()
        unrealized_pnl = self.paper_trader.unrealized_pnl(ltp_map)
        total_pnl = round(realized_pnl + unrealized_pnl, 2)
        self._risk_state.daily_pnl = realized_pnl  # kill-switch uses realized only

        self._risk_state.open_positions = len(positions)
        self.state_bridge.set("positions", positions)
        self.state_bridge.set("history", self.paper_trader.closed_today())
        self.state_bridge.update_summary(
            day_pnl=total_pnl,
            capital=self.paper_trader.capital,
            open_count=len(positions),
        )
        # record broker heartbeat after a successful data cycle
        self.health_monitor.record_heartbeat("broker")
        self.state_bridge.update_health(self.health_monitor)
