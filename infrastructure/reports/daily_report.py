"""Daily report generator — reads trades from SQLite, writes JSON to reports dir."""
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_daily_report(db_path: str, date: str, mode: str = "paper") -> dict:
    """Return report dict for all trades with entry_time on `date` (YYYY-MM-DD)."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM trades WHERE entry_time LIKE ? ORDER BY entry_time",
            (f"{date}%",),
        ).fetchall()
    trades = [dict(r) for r in rows]
    closed = [t for t in trades if t["pnl"] is not None]
    pnls = [t["pnl"] for t in closed]
    winners = [p for p in pnls if p > 0]
    losers = [p for p in pnls if p < 0]
    total_pnl = sum(pnls)
    return {
        "date": date,
        "mode": mode,
        "generated_at": datetime.now().isoformat(),
        "total_trades": len(trades),
        "closed_trades": len(closed),
        "open_trades": len(trades) - len(closed),
        "winning_trades": len(winners),
        "losing_trades": len(losers),
        "win_rate": round(len(winners) / len(closed), 4) if closed else 0.0,
        "total_pnl": round(total_pnl, 2),
        "avg_pnl": round(total_pnl / len(closed), 2) if closed else 0.0,
        "best_trade": round(max(pnls), 2) if pnls else 0.0,
        "worst_trade": round(min(pnls), 2) if pnls else 0.0,
        "trades": trades,
    }


def save_daily_report(report: dict, reports_dir: str) -> Path:
    """Write report dict to {reports_dir}/{date}.json and return the path."""
    Path(reports_dir).mkdir(parents=True, exist_ok=True)
    path = Path(reports_dir) / f"{report['date']}.json"
    path.write_text(json.dumps(report, indent=2, default=str))
    logger.info("daily report saved: %s", path)
    return path
