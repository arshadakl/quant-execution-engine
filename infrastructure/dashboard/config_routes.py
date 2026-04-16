"""Config route — /config GET read-only view of current settings."""
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from infrastructure.config.settings import get_settings, get_symbol_tokens

logger = logging.getLogger(__name__)
_TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_config_router(auth_dep) -> APIRouter:
    router = APIRouter()
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    @router.get("/config", response_class=HTMLResponse)
    async def config_page(request: Request, _: None = Depends(auth_dep)):
        settings = get_settings()
        return templates.TemplateResponse(request, "config.html", {
            "trading": settings.trading,
            "risk": settings.risk,
            "symbols": list(get_symbol_tokens().keys()),
        })

    return router
