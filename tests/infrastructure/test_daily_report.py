"""Tests for daily report generator."""
import json
import sqlite3
from pathlib import Path
from infrastructure.reports.daily_report import generate_daily_report, save_daily_report

_CREATE = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT, direction TEXT, strategy TEXT,
    qty INTEGER, entry_price REAL, stop_loss REAL, target_1 REAL,
    entry_time TEXT, exit_price REAL, exit_time TEXT, pnl REAL
)
"""


def _seed(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(_CREATE)
        conn.executemany(
            "INSERT INTO trades (symbol,direction,strategy,qty,entry_price,stop_loss,"
            "target_1,entry_time,exit_price,exit_time,pnl) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            [
                ("RELIANCE","LONG","ORB",10,2900.0,2870.0,2960.0,
                 "2026-04-14T09:30:00",2960.0,"2026-04-14T11:00:00",600.0),
                ("TCS","LONG","ORB",5,4200.0,4150.0,4300.0,
                 "2026-04-14T10:00:00",4150.0,"2026-04-14T11:30:00",-250.0),
                ("INFY","SHORT","VWAP",8,1800.0,1830.0,1750.0,
                 "2026-04-14T11:00:00",None,None,None),        # open trade
                ("WIPRO","LONG","EMA",20,550.0,540.0,570.0,
                 "2026-04-15T09:30:00",570.0,"2026-04-15T12:00:00",400.0),  # different date
            ]
        )


def test_counts_trades_on_date(tmp_path):
    db = str(tmp_path / "t.db"); _seed(db)
    r = generate_daily_report(db, "2026-04-14")
    assert r["total_trades"] == 3
    assert r["closed_trades"] == 2
    assert r["open_trades"] == 1


def test_pnl_sums_closed_trades_only(tmp_path):
    db = str(tmp_path / "t.db"); _seed(db)
    r = generate_daily_report(db, "2026-04-14")
    assert r["total_pnl"] == 350.0   # 600 + (-250)


def test_win_rate(tmp_path):
    db = str(tmp_path / "t.db"); _seed(db)
    r = generate_daily_report(db, "2026-04-14")
    assert r["win_rate"] == 0.5      # 1 win, 1 loss


def test_best_and_worst_trade(tmp_path):
    db = str(tmp_path / "t.db"); _seed(db)
    r = generate_daily_report(db, "2026-04-14")
    assert r["best_trade"] == 600.0
    assert r["worst_trade"] == -250.0


def test_ignores_other_dates(tmp_path):
    db = str(tmp_path / "t.db"); _seed(db)
    r = generate_daily_report(db, "2026-04-15")
    assert r["total_trades"] == 1
    assert r["total_pnl"] == 400.0


def test_empty_date_returns_zeros(tmp_path):
    db = str(tmp_path / "t.db"); _seed(db)
    r = generate_daily_report(db, "2026-01-01")
    assert r["total_trades"] == 0
    assert r["total_pnl"] == 0.0
    assert r["win_rate"] == 0.0


def test_save_writes_json(tmp_path):
    db = str(tmp_path / "t.db"); _seed(db)
    r = generate_daily_report(db, "2026-04-14")
    path = save_daily_report(r, str(tmp_path / "reports"))
    assert path.exists()
    assert json.loads(path.read_text())["total_pnl"] == 350.0


def test_save_creates_dir_if_missing(tmp_path):
    db = str(tmp_path / "t.db"); _seed(db)
    r = generate_daily_report(db, "2026-04-14")
    new_dir = tmp_path / "new_reports"
    assert not new_dir.exists()
    save_daily_report(r, str(new_dir))
    assert (new_dir / "2026-04-14.json").exists()
