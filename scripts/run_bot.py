"""Main entry point — runs the trading bot."""
import logging

logger = logging.getLogger(__name__)


def main() -> None:
    from infrastructure.config.settings import get_settings
    settings = get_settings()
    logger.info("AlgoTrader India starting in %s mode", settings.trading.mode)


if __name__ == "__main__":
    main()
