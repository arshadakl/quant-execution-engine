"""APScheduler job definitions — scanner, strategy loop, square-off, daily report."""
import logging
from datetime import time
from typing import Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class JobScheduler:
    """Thin wrapper around APScheduler BackgroundScheduler."""

    def __init__(
        self,
        scan_time: time = time(8, 50),
        strategy_interval_seconds: int = 60,
        square_off_time: time = time(15, 10),
    ) -> None:
        self.scan_time = scan_time
        self.strategy_interval_seconds = strategy_interval_seconds
        self.square_off_time = square_off_time
        self._scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    def start(self) -> None:
        """Start the background scheduler."""
        self._scheduler.start()
        logger.info("scheduler started")

    def stop(self) -> None:
        """Shut down the background scheduler."""
        self._scheduler.shutdown()
        logger.info("scheduler stopped")

    def register_scanner_job(self, fn: Callable) -> None:
        """Run scanner once daily at scan_time."""
        self._scheduler.add_job(
            fn,
            CronTrigger(
                hour=self.scan_time.hour,
                minute=self.scan_time.minute,
                timezone="Asia/Kolkata",
            ),
            id="scanner",
            replace_existing=True,
        )
        logger.info("scanner job registered at %s", self.scan_time)

    def register_strategy_loop(self, fn: Callable) -> None:
        """Run strategy loop every strategy_interval_seconds."""
        self._scheduler.add_job(
            fn,
            IntervalTrigger(seconds=self.strategy_interval_seconds),
            id="strategy_loop",
            replace_existing=True,
        )
        logger.info("strategy loop registered every %ds", self.strategy_interval_seconds)

    def register_square_off_job(self, fn: Callable) -> None:
        """Run square-off once daily at square_off_time."""
        self._scheduler.add_job(
            fn,
            CronTrigger(
                hour=self.square_off_time.hour,
                minute=self.square_off_time.minute,
                timezone="Asia/Kolkata",
            ),
            id="square_off",
            replace_existing=True,
        )
        logger.info("square-off job registered at %s", self.square_off_time)

    def register_daily_report_job(self, fn: Callable) -> None:
        """Run daily report once after market close at 15:35."""
        self._scheduler.add_job(
            fn,
            CronTrigger(hour=15, minute=35, timezone="Asia/Kolkata"),
            id="daily_report",
            replace_existing=True,
        )
        logger.info("daily report job registered at 15:35")

    def remove_all_jobs(self) -> None:
        """Remove all registered jobs."""
        self._scheduler.remove_all_jobs()
        logger.info("all jobs removed")
