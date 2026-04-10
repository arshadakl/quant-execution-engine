"""Web UI — FastAPI + HTMX dashboard with token auth."""
import logging
from pathlib import Path
from fastapi import FastAPI, Request, Header, HTTPException, Form, Cookie, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"

# Demo state — replaced by real services in production
_state: dict = {
    "positions": [
        {"symbol": "RELIANCE", "direction": "LONG", "qty": 5,
         "entry_price": 2850.50, "current_price": 2875.25, "pnl": 123.75},
        {"symbol": "TCS", "direction": "SHORT", "qty": 3,
         "entry_price": 3920.00, "current_price": 3908.50, "pnl": 34.50},
    ],
    "signals": [
        {"symbol": "INFY", "direction": "LONG", "strategy": "ORB",
         "entry": 1520.0, "sl": 1498.0, "target": 1564.0},
        {"symbol": "HDFCBANK", "direction": "LONG", "strategy": "EMA",
         "entry": 1654.0, "sl": 1635.0, "target": 1692.0},
    ],
    "history": [
        {"exit_time": "2026-04-10 10:32", "symbol": "WIPRO", "direction": "LONG",
         "entry_price": 445.0, "exit_price": 461.5, "qty": 20, "pnl": 330.0},
        {"exit_time": "2026-04-10 11:05", "symbol": "MARUTI", "direction": "SHORT",
         "entry_price": 11240.0, "exit_price": 11185.0, "qty": 5, "pnl": 275.0},
        {"exit_time": "2026-04-10 12:18", "symbol": "BAJFINANCE", "direction": "LONG",
         "entry_price": 6840.0, "exit_price": 6798.0, "qty": 5, "pnl": -210.0},
    ],
    "strategies": {"orb": True, "vwap": True, "momentum": True, "ema": True, "gap": True},
    "risk": {"max_daily_loss_pct": 0.03, "max_open_positions": 5},
    "summary": {"day_pnl": 553.25, "capital": 100_553.25, "open_count": 2},
}


def create_app(api_token: str = "changeme") -> FastAPI:
    app = FastAPI(title="AlgoTrader Dashboard", docs_url=None, redoc_url=None)
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    def _auth(
        x_api_token: str | None = Header(default=None),
        algo_token: str | None = Cookie(default=None),
    ) -> None:
        if x_api_token == api_token or algo_token == api_token:
            return
        raise HTTPException(status_code=401, detail="Unauthorized")

    # ── Login ──────────────────────────────────────────────────────────────

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

    # ── Dashboard ──────────────────────────────────────────────────────────

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request, _: None = Depends(_auth)):
        return templates.TemplateResponse(request, "dashboard.html", {"state": _state})

    @app.get("/partials/positions", response_class=HTMLResponse)
    async def positions(request: Request, _: None = Depends(_auth)):
        return templates.TemplateResponse(request, "partials/positions.html",
                                          {"positions": _state["positions"]})

    @app.get("/partials/signals", response_class=HTMLResponse)
    async def signals(request: Request, _: None = Depends(_auth)):
        return templates.TemplateResponse(request, "partials/signals.html",
                                          {"signals": _state["signals"]})

    @app.get("/partials/history", response_class=HTMLResponse)
    async def history(request: Request, _: None = Depends(_auth)):
        return templates.TemplateResponse(request, "partials/history.html",
                                          {"history": _state["history"]})

    @app.get("/partials/summary", response_class=HTMLResponse)
    async def summary(request: Request, _: None = Depends(_auth)):
        return templates.TemplateResponse(request, "partials/summary.html",
                                          {"summary": _state["summary"]})

    @app.post("/strategy/{name}/toggle", response_class=HTMLResponse)
    async def toggle_strategy(name: str, request: Request, _: None = Depends(_auth)):
        current = _state["strategies"].get(name, False)
        _state["strategies"][name] = not current
        logger.info("strategy %s toggled → %s", name, _state["strategies"][name])
        return templates.TemplateResponse(request, "partials/strategies.html",
                                          {"strategies": _state["strategies"]})

    @app.get("/risk", response_class=HTMLResponse)
    async def risk_get(request: Request, _: None = Depends(_auth)):
        return templates.TemplateResponse(request, "partials/risk.html",
                                          {"risk": _state["risk"]})

    @app.post("/risk", response_class=HTMLResponse)
    async def risk_post(request: Request,
                        max_daily_loss_pct: float = Form(...),
                        max_open_positions: int = Form(...),
                        _: None = Depends(_auth)):
        _state["risk"]["max_daily_loss_pct"] = max_daily_loss_pct
        _state["risk"]["max_open_positions"] = max_open_positions
        logger.info("risk params updated: %s", _state["risk"])
        return templates.TemplateResponse(request, "partials/risk.html",
                                          {"risk": _state["risk"]})

    return app
