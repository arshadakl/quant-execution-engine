"""Main entry point -- runs AlgoTrader (paper or live) + web dashboard in one process."""
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import uvicorn

from infrastructure.config.settings import get_settings, get_symbol_tokens
from infrastructure.dashboard.state_bridge import StateBridge
from infrastructure.dashboard.web_ui import create_app
from infrastructure.health_monitor import HealthMonitor
from adapters.broker.angel_broker import AngelBroker
from adapters.broker.execution_engine import ExecutionEngine
from adapters.notifications.telegram_notifier import TelegramNotifier
from adapters.paper_trader import PaperTrader
from core.use_cases.strategy_engine import StrategyEngine
from core.use_cases.risk_manager import RiskManager
from core.use_cases.position_sizer import PositionSizer
from core.use_cases.trading_bot import TradingBot
from strategies.orb import ORBStrategy
from strategies.vwap_reversion import VWAPReversionStrategy
from strategies.ema_crossover import EMACrossoverStrategy
from infrastructure.scheduler.jobs import JobScheduler
from infrastructure.reports.daily_report import generate_daily_report, save_daily_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s -- %(message)s",
)
logger = logging.getLogger(__name__)

DASHBOARD_TOKEN = os.environ.get("DASHBOARD_TOKEN")
if not DASHBOARD_TOKEN:
    print("\n  ERROR: DASHBOARD_TOKEN not set in .env\n")
    sys.exit(1)

DB_PATH = str(Path(__file__).parent.parent / "data" / "paper_trades.db")
Path(DB_PATH).parent.mkdir(exist_ok=True)
REPORTS_DIR = str(Path(__file__).parent.parent / "data" / "reports")


def _make_daily_report_fn(db_path: str, reports_dir: str, mode: str):
    def fn():
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            report = generate_daily_report(db_path, today, mode)
            save_daily_report(report, reports_dir)
            logger.info("daily report generated for %s", today)
        except Exception as exc:
            logger.error("daily report generation failed: %s", exc)
    return fn


async def main() -> None:
    settings = get_settings()
    mode = settings.trading.mode
    logger.info("AlgoTrader starting -- mode=%s", mode)

    bridge = StateBridge()
    health = HealthMonitor()
    broker = AngelBroker(settings.broker)
    telegram = TelegramNotifier(
        bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
    )

    logger.info("Logging into Angel One...")
    if not await broker.login():
        logger.error("Angel One login failed -- check .env credentials")
        sys.exit(1)
    health.record_heartbeat("broker")
    logger.info("Login OK")

    paper_trader = PaperTrader(db_path=DB_PATH, initial_capital=settings.trading.paper_capital)
    execution_engine = ExecutionEngine(broker) if mode == "live" else None
    if mode == "live":
        logger.warning("LIVE MODE ACTIVE — real orders will be placed on Angel One")
    risk_config = settings.risk
    risk_manager = RiskManager(
        max_daily_loss_pct=risk_config.max_daily_loss_percent / 100,
        max_open_positions=risk_config.max_open_positions,
        max_daily_trades=risk_config.max_daily_trades,
    )
    position_sizer = PositionSizer(
        risk_pct=risk_config.per_trade_risk_percent / 100,
        max_position_size_pct=risk_config.max_position_size_percent / 100,
    )
    strategy_engine = StrategyEngine(strategies=[
        ORBStrategy(), VWAPReversionStrategy(), EMACrossoverStrategy(),
    ])

    scheduler = JobScheduler()
    scheduler.register_daily_report_job(_make_daily_report_fn(DB_PATH, REPORTS_DIR, mode))
    scheduler.start()

    bot = TradingBot(
        mode=mode,
        broker=broker,
        strategy_engine=strategy_engine,
        risk_manager=risk_manager,
        position_sizer=position_sizer,
        paper_trader=paper_trader,
        telegram=telegram,
        health_monitor=health,
        state_bridge=bridge,
        symbol_tokens=get_symbol_tokens(),
        execution_engine=execution_engine,
    )

    app = create_app(
        api_token=DASHBOARD_TOKEN,
        bridge=bridge,
        bot=bot,
        db_path=DB_PATH,
        mode=mode,
        reports_dir=REPORTS_DIR,
    )

    loop_task = asyncio.create_task(bot.run_loop(interval_seconds=60))
    logger.info("Strategy loop started")
    logger.info("Dashboard >> http://127.0.0.1:8000/login")

    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    try:
        await server.serve()
    finally:
        bot.stop()
        scheduler.stop()
        loop_task.cancel()
        try:
            await broker.logout()
        except BaseException:
            pass  # loop is shutting down, logout best-effort
        logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
