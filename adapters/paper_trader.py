"""Paper trader — simulated fills with SQLite trade journal."""
import logging
import sqlite3
from datetime import datetime
from core.entities.signal import Signal

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS trades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT    NOT NULL,
    direction   TEXT    NOT NULL,
    strategy    TEXT    NOT NULL,
    qty         INTEGER NOT NULL,
    entry_price REAL    NOT NULL,
    stop_loss   REAL    NOT NULL,
    target_1    REAL    NOT NULL,
    entry_time  TEXT    NOT NULL,
    exit_price  REAL,
    exit_time   TEXT,
    pnl         REAL
)
"""


class PaperTrader:
    """Simulated broker: fills signals immediately at given price, journals to SQLite."""

    def __init__(self, db_path: str, initial_capital: float) -> None:
        self.capital = initial_capital
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(_CREATE_TABLE)

    def fill(self, signal: Signal, qty: int, fill_price: float) -> int:
        """Record entry fill; return the new trade ID."""
        with sqlite3.connect(self._db_path) as conn:
            cur = conn.execute(
                """INSERT INTO trades
                   (symbol, direction, strategy, qty, entry_price, stop_loss, target_1, entry_time)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (signal.symbol, signal.direction, signal.strategy,
                 qty, fill_price, signal.stop_loss, signal.target_1,
                 signal.timestamp.isoformat()),
            )
            trade_id = cur.lastrowid
        logger.info("paper fill: %s %s x%d @ %.2f id=%d",
                    signal.direction, signal.symbol, qty, fill_price, trade_id)
        return trade_id

    def close_trade(self, trade_id: int, exit_price: float, exit_time: datetime) -> None:
        """Record exit fill and compute P&L."""
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT qty, entry_price, direction FROM trades WHERE id=? AND exit_price IS NULL",
                (trade_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"No open trade with id={trade_id}")
            qty, entry_price, direction = row
            mult = 1 if direction == "LONG" else -1
            pnl = mult * (exit_price - entry_price) * qty
            conn.execute(
                "UPDATE trades SET exit_price=?, exit_time=?, pnl=? WHERE id=?",
                (exit_price, exit_time.isoformat(), pnl, trade_id),
            )
        logger.info("paper close: id=%d exit=%.2f pnl=%.0f", trade_id, exit_price, pnl)

    def day_pnl(self) -> float:
        """Sum of P&L for all closed trades."""
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(pnl), 0.0) FROM trades WHERE pnl IS NOT NULL"
            ).fetchone()
        return float(row[0])

    def open_trades(self) -> list[dict]:
        """Return list of dicts for trades without an exit."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM trades WHERE exit_price IS NULL"
            ).fetchall()
        return [dict(r) for r in rows]

    def closed_today(self) -> list[dict]:
        """Return closed trades whose exit_time is today (for trade history panel)."""
        today = datetime.now().date().isoformat()
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM trades WHERE exit_price IS NOT NULL AND exit_time LIKE ? ORDER BY exit_time DESC",
                (f"{today}%",),
            ).fetchall()
        return [dict(r) for r in rows]

    def unrealized_pnl(self, ltp_map: dict[str, float]) -> float:
        """Sum of mark-to-market P&L for all open positions."""
        total = 0.0
        for t in self.open_trades():
            ltp = ltp_map.get(t["symbol"], t["entry_price"])
            mult = 1 if t["direction"] == "LONG" else -1
            total += mult * (ltp - t["entry_price"]) * t["qty"]
        return round(total, 2)
