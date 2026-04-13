"""Backtest routes -- /backtest GET form, /backtest/run POST results."""
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING


from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from backtester.optimizer import run_backtest
from strategies.base_strategy import BacktestParams
from strategies.ema_crossover import EMACrossoverStrategy
from strategies.gap_fill import GapFillStrategy
from strategies.momentum_breakout import MomentumBreakoutStrategy
from strategies.orb import ORBStrategy
from strategies.vwap_reversion import VWAPReversionStrategy
from infrastructure.config.settings import get_symbol_tokens

if TYPE_CHECKING:
    from core.use_cases.trading_bot import TradingBot

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"

_STRATEGY_MAP = {
    "orb": ORBStrategy,
    "vwap": VWAPReversionStrategy,
    "ema": EMACrossoverStrategy,
    "momentum": MomentumBreakoutStrategy,
    "gap_fill": GapFillStrategy,
}

# ORB and VWAP are intraday strategies — need 5m candles
_STRATEGY_INTERVALS: dict[str, str] = {
    "orb": "5m", "vwap": "5m",
    "ema": "1d", "momentum": "1d", "gap_fill": "1d",
}




_CAPITAL_PER_TRADE = 50_000  # ₹50,000 allocation per trade


async def _fetch_and_run(
    broker,
    symbol: str,
    token: str,
    strategy_name: str,
    from_date: str,
    to_date: str,
) -> dict:
    from_dt = datetime.strptime(from_date, "%Y-%m-%d")
    to_dt = datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59)
    if from_dt >= to_dt:
        return {"error": "from_date must be before to_date"}
    interval = _STRATEGY_INTERVALS.get(strategy_name, "1d")
    df = await broker.get_historical(symbol, token, interval, from_dt, to_dt)
    if df.empty or len(df) < 5:
        return {"error": "Not enough data returned for that date range"}
    last_price = float(df["close"].iloc[-1])
    qty = max(1, int(_CAPITAL_PER_TRADE / last_price))
    params = BacktestParams(symbol=symbol, token=token, interval=interval, from_dt=from_dt, to_dt=to_dt)
    trades, metrics = run_backtest(_STRATEGY_MAP[strategy_name](), df, params, qty=qty)
    return {"metrics": metrics, "trades": trades, "qty_used": qty}


def create_backtest_router(auth_dep, bot_ref: list) -> APIRouter:
    """Return APIRouter for backtest routes.

    auth_dep  -- the _auth Depends callable from create_app
    bot_ref   -- single-element list holding the TradingBot (mutable ref)
    """
    router = APIRouter()
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    symbols = list(get_symbol_tokens().keys())
    _RESULTS = "partials/backtest_results.html"

    def _tmpl(req, ctx):
        return templates.TemplateResponse(req, _RESULTS, ctx)

    @router.get("/backtest", response_class=HTMLResponse)
    async def backtest_page(request: Request, _: None = Depends(auth_dep)):
        return templates.TemplateResponse(request, "backtest.html", {
            "symbols": symbols,
            "strategies": list(_STRATEGY_MAP.keys()),
        })

    @router.post("/backtest/run", response_class=HTMLResponse)
    async def backtest_run(
        request: Request,
        symbol: str = Form(...),
        strategy: str = Form(...),
        from_date: str = Form(...),
        to_date: str = Form(...),
        _: None = Depends(auth_dep),
    ):
        bot: "TradingBot | None" = bot_ref[0]
        ctx: dict = {"symbol": symbol, "strategy": strategy}
        if strategy not in _STRATEGY_MAP:
            ctx["error"] = f"Unknown strategy: {strategy}"
            return _tmpl(request, ctx)
        if bot is None:
            ctx["error"] = "Bot is not running -- start the bot first (python scripts/run_bot.py)"
            return _tmpl(request, ctx)
        token = get_symbol_tokens().get(symbol)
        if not token:
            ctx["error"] = f"Unknown symbol: {symbol}"
            return _tmpl(request, ctx)
        try:
            ctx.update(await _fetch_and_run(bot.broker, symbol, token, strategy, from_date, to_date))
        except (ValueError, RuntimeError) as exc:
            logger.error("Backtest error: %s", exc)
            ctx["error"] = str(exc)
        return _tmpl(request, ctx)

    return router
