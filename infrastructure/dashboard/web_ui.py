"""Web UI — FastAPI + HTMX dashboard with token auth."""
import logging
from pathlib import Path
from fastapi import FastAPI, Request, Header, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"

# In-memory state (replaced by real services in production)
_state: dict = {
    "positions": [],
    "signals": [],
    "history": [],
    "strategies": {"orb": True, "vwap": True, "momentum": True, "ema": True, "gap": True},
    "risk": {"max_daily_loss_pct": 0.03, "max_open_positions": 5},
    "summary": {"day_pnl": 0.0, "capital": 100_000.0, "open_count": 0},
}


def _check_auth(token: str | None, api_token: str) -> None:
    if token != api_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


def create_app(api_token: str = "changeme") -> FastAPI:
    app = FastAPI(title="AlgoTrader Dashboard", docs_url=None, redoc_url=None)
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    def auth(x_api_token: str | None = None) -> None:
        _check_auth(x_api_token, api_token)

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request, x_api_token: str | None = Header(default=None)):
        _check_auth(x_api_token, api_token)
        return templates.TemplateResponse(request, "dashboard.html", {"state": _state})

    @app.get("/partials/positions", response_class=HTMLResponse)
    async def positions(request: Request, x_api_token: str | None = Header(default=None)):
        _check_auth(x_api_token, api_token)
        return templates.TemplateResponse(request, "partials/positions.html",
                                          {"positions": _state["positions"]})

    @app.get("/partials/signals", response_class=HTMLResponse)
    async def signals(request: Request, x_api_token: str | None = Header(default=None)):
        _check_auth(x_api_token, api_token)
        return templates.TemplateResponse(request, "partials/signals.html",
                                          {"signals": _state["signals"]})

    @app.get("/partials/history", response_class=HTMLResponse)
    async def history(request: Request, x_api_token: str | None = Header(default=None)):
        _check_auth(x_api_token, api_token)
        return templates.TemplateResponse(request, "partials/history.html",
                                          {"history": _state["history"]})

    @app.get("/partials/summary", response_class=HTMLResponse)
    async def summary(request: Request, x_api_token: str | None = Header(default=None)):
        _check_auth(x_api_token, api_token)
        return templates.TemplateResponse(request, "partials/summary.html",
                                          {"summary": _state["summary"]})

    @app.post("/strategy/{name}/toggle", response_class=HTMLResponse)
    async def toggle_strategy(name: str, request: Request,
                               x_api_token: str | None = Header(default=None)):
        _check_auth(x_api_token, api_token)
        current = _state["strategies"].get(name, False)
        _state["strategies"][name] = not current
        logger.info("strategy %s toggled → %s", name, _state["strategies"][name])
        return templates.TemplateResponse(request, "partials/strategies.html",
                                          {"strategies": _state["strategies"]})

    @app.get("/risk", response_class=HTMLResponse)
    async def risk_get(request: Request, x_api_token: str | None = Header(default=None)):
        _check_auth(x_api_token, api_token)
        return templates.TemplateResponse(request, "partials/risk.html",
                                          {"risk": _state["risk"]})

    @app.post("/risk", response_class=HTMLResponse)
    async def risk_post(request: Request,
                        max_daily_loss_pct: float = Form(...),
                        max_open_positions: int = Form(...),
                        x_api_token: str | None = Header(default=None)):
        _check_auth(x_api_token, api_token)
        _state["risk"]["max_daily_loss_pct"] = max_daily_loss_pct
        _state["risk"]["max_open_positions"] = max_open_positions
        logger.info("risk params updated: %s", _state["risk"])
        return templates.TemplateResponse(request, "partials/risk.html",
                                          {"risk": _state["risk"]})

    return app
