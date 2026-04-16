"""Report routes -- /reports list, /reports/{date} HTMX detail."""
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from infrastructure.reports.daily_report import generate_daily_report, save_daily_report

logger = logging.getLogger(__name__)
_TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_report_router(
    auth_dep, db_path: str, mode: str, reports_dir: str
) -> APIRouter:
    router = APIRouter()
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    @router.get("/reports", response_class=HTMLResponse)
    async def reports_page(request: Request, _: None = Depends(auth_dep)):
        rd = Path(reports_dir)
        dates = (
            sorted(
                [p.stem for p in rd.glob("*.json") if p.stem.count("-") == 2],
                reverse=True,
            )
            if rd.exists() else []
        )
        return templates.TemplateResponse(request, "reports.html", {"dates": dates})

    @router.get("/reports/{date}", response_class=HTMLResponse)
    async def report_detail(date: str, request: Request, _: None = Depends(auth_dep)):
        path = Path(reports_dir) / f"{date}.json"
        if not path.exists():
            try:
                report = generate_daily_report(db_path, date, mode)
                save_daily_report(report, reports_dir)
            except Exception as exc:
                logger.error("on-demand report failed for %s: %s", date, exc)
                return HTMLResponse(
                    f'<div class="bg-bg1 border border-loss/40 px-4 py-3 text-loss text-[11px]">'
                    f'&#9888; Could not generate report: {exc}</div>'
                )
        report = json.loads(path.read_text())
        return templates.TemplateResponse(
            request, "partials/report_detail.html", {"report": report}
        )

    return router
