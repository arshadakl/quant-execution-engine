"""Terminal dashboard — Rich-based live display of positions, signals, P&L."""
import io
from rich.console import Console
from rich.table import Table
from rich.text import Text


class TerminalDashboard:
    """Renders trading state as Rich tables/text, returns strings for testing."""

    def render_positions(self, positions: list[dict]) -> str:
        table = Table(title="Open Positions", show_lines=True)
        table.add_column("Symbol")
        table.add_column("Dir")
        table.add_column("Qty", justify="right")
        table.add_column("Entry", justify="right")
        table.add_column("LTP", justify="right")
        table.add_column("P&L", justify="right")
        for p in positions:
            pnl = p.get("pnl", 0.0)
            style = "green" if pnl >= 0 else "red"
            table.add_row(
                p["symbol"], p.get("direction", ""), str(p["qty"]),
                f"{p['entry_price']:.2f}", f"{p.get('current_price', 0):.2f}",
                Text(f"{pnl:+.2f}", style=style),
            )
        return _render_to_str(table)

    def render_signals(self, signals: list[dict]) -> str:
        table = Table(title="Signals", show_lines=True)
        table.add_column("Symbol")
        table.add_column("Dir")
        table.add_column("Strategy")
        table.add_column("Entry", justify="right")
        table.add_column("SL", justify="right")
        table.add_column("Target", justify="right")
        for s in signals:
            table.add_row(
                s["symbol"], s.get("direction", ""), s.get("strategy", ""),
                f"{s.get('entry', 0):.2f}",
                f"{s.get('sl', 0):.2f}",
                f"{s.get('target', 0):.2f}",
            )
        return _render_to_str(table)

    def render_summary(self, day_pnl: float, capital: float, open_count: int) -> str:
        style = "green" if day_pnl >= 0 else "red"
        text = Text()
        text.append("Day P&L: ", style="bold")
        text.append(f"{day_pnl:+.2f}", style=style)
        text.append(f"  |  Capital: {capital:,.0f}  |  Open: {open_count}")
        return _render_to_str(text)

    def print_dashboard(
        self,
        positions: list[dict],
        signals: list[dict],
        day_pnl: float,
        capital: float,
    ) -> str:
        parts = [
            self.render_summary(day_pnl, capital, len(positions)),
            self.render_positions(positions),
            self.render_signals(signals),
        ]
        return "\n".join(parts)


def _render_to_str(renderable) -> str:
    buf = io.StringIO()
    console = Console(file=buf, highlight=False)
    console.print(renderable)
    return buf.getvalue()
