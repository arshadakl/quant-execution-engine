"""Web UI -- FastAPI + HTMX dashboard with token auth."""
import logging
from pathlib import Path
from typing import TYPE_CHECKING
from fastapi import FastAPI, Request, Header, HTTPException, Form, Cookie, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from infrastructure.dashboard.state_bridge import StateBridge

if TYPE_CHECKING:
    from core.use_cases.trading_bot import TradingBot

logger = logging.getLogger(__name__)
_TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app(
    api_token: str = "changeme",
    bridge: StateBridge | None = None,
    bot: "TradingBot | None" = None,
) -> FastAPI:
    _bridge = bridge or StateBridge()
    app = FastAPI(title="AlgoTrader Dashboard", docs_url=None, redoc_url=None)
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    def _auth(
        x_api_token: str | None = Header(default=None),
        algo_token: str | None = Cookie(default=None),
    ) -> None:
        if x_api_token == api_token or algo_token == api_token:
            return
        raise HTTPException(status_code=401, detail="Unauthorized")

    def _summary_ctx() -> dict:
        return {
            "summary": _bridge.get("summary"),
            "mode": _bridge.get("mode"),
            "kill_switch": _bridge.get("kill_switch"),
        }

    @app.get("/login", response_class=HTMLResponse)
    async def login_get(request: Request):
        return templates.TemplateResponse(request, "login.html", {})

    @app.post("/login")
    async def login_post(request: Request, token: str = Form(...)):
        if token != api_token:
            return templates.TemplateResponse(
                request, "login.html", {"error": "Invalid token"}, status_code=401
            )
        resp = RedirectResponse(url="/", status_code=303)
        resp.set_cookie("algo_token", token, httponly=True, samesite="strict")
        return resp

    @app.get("/logout")
    async def logout():
        resp = RedirectResponse(url="/login", status_code=303)
        resp.delete_cookie("algo_token")
        return resp

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request, _: None = Depends(_auth)):
        return templates.TemplateResponse(
            request, "dashboard.html", {"state": _bridge.snapshot()}
        )

    @app.get("/partials/positions", response_class=HTMLResponse)
    async def positions(request: Request, _: None = Depends(_auth)):
        return templates.TemplateResponse(
            request, "partials/positions.html",
            {"positions": _bridge.get("positions")},
        )

    @app.get("/partials/signals", response_class=HTMLResponse)
    async def signals(request: Request, _: None = Depends(_auth)):
        return templates.TemplateResponse(
            request, "partials/signals.html",
            {"signals": _bridge.get("signals")},
        )

    @app.get("/partials/history", response_class=HTMLResponse)
    async def history(request: Request, _: None = Depends(_auth)):
        return templates.TemplateResponse(
            request, "partials/history.html",
            {"history": _bridge.get("history")},
        )

    @app.get("/partials/summary", response_class=HTMLResponse)
    async def summary(request: Request, _: None = Depends(_auth)):
        return templates.TemplateResponse(request, "partials/summary.html", _summary_ctx())

    @app.get("/partials/health", response_class=HTMLResponse)
    async def health_partial(request: Request, _: None = Depends(_auth)):
        return templates.TemplateResponse(
            request, "partials/health.html",
            {"health": _bridge.get("health")},
        )

    @app.post("/strategy/{name}/toggle", response_class=HTMLResponse)
    async def toggle_strategy(name: str, request: Request, _: None = Depends(_auth)):
        current = (_bridge.get("strategies") or {}).get(name, False)
        new_val = not current
        if bot:
            bot.toggle_strategy(name, new_val)
        else:
            strategies = dict(_bridge.get("strategies") or {})
            strategies[name] = new_val
            _bridge.set("strategies", strategies)
        logger.info("strategy %s toggled -> %s", name, new_val)
        return templates.TemplateResponse(
            request, "partials/strategies.html",
            {"strategies": _bridge.get("strategies")},
        )

    @app.get("/risk", response_class=HTMLResponse)
    async def risk_get(request: Request, _: None = Depends(_auth)):
        return templates.TemplateResponse(
            request, "partials/risk.html", {"risk": _bridge.get("risk")}
        )

    @app.post("/risk", response_class=HTMLResponse)
    async def risk_post(
        request: Request,
        max_daily_loss_pct: float = Form(...),
        max_open_positions: int = Form(...),
        _: None = Depends(_auth),
    ):
        risk = {"max_daily_loss_pct": max_daily_loss_pct,
                "max_open_positions": max_open_positions}
        _bridge.set("risk", risk)
        if bot:
            bot.risk_manager.max_daily_loss_pct = max_daily_loss_pct
            bot.risk_manager.max_open_positions = max_open_positions
        logger.info("risk params updated: %s", risk)
        return templates.TemplateResponse(
            request, "partials/risk.html", {"risk": _bridge.get("risk")}
        )

    @app.post("/kill-switch", response_class=HTMLResponse)
    async def kill_switch(request: Request, active: bool = Form(...), _: None = Depends(_auth)):
        if bot:
            bot.set_kill_switch(active)
        else:
            _bridge.set("kill_switch", active)
        logger.warning("kill switch set via dashboard: %s", active)
        return templates.TemplateResponse(request, "partials/summary.html", _summary_ctx())
    return app
