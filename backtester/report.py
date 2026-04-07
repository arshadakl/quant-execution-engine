"""HTML report generator for backtest results.

Produces a self-contained HTML file with:
  - Summary metrics table
  - Equity curve chart (Plotly)
  - Drawdown chart (Plotly)
  - Monthly P&L bar chart (Plotly)
  - Full trade log table
"""
import logging
from pathlib import Path
from typing import Any

from backtester.metrics import MetricsResult
from backtester.report_charts import drawdown_chart, equity_curve_chart, monthly_pnl_chart
from strategies.base_strategy import BacktestParams

logger = logging.getLogger(__name__)


def generate_report(
    trades: list[Any],
    metrics: MetricsResult,
    params: BacktestParams,
    output_dir: Path,
) -> Path:
    """Generate a self-contained HTML backtest report.

    Returns the path to the created file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{params.symbol}_{params.interval}_backtest.html"
    out_path = output_dir / filename

    html = _build_html(trades, metrics, params)
    out_path.write_text(html, encoding="utf-8")
    logger.info("Report written: %s", out_path)
    return out_path


def _build_html(trades: list[Any], metrics: MetricsResult, params: BacktestParams) -> str:
    equity_div = equity_curve_chart(trades, params.initial_capital) if trades else ""
    dd_div = drawdown_chart(trades, params.initial_capital) if trades else ""
    monthly_div = monthly_pnl_chart(trades)
    trade_rows = _trade_rows(trades)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Backtest Report — {params.symbol} {params.interval}</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  body{{font-family:sans-serif;background:#1a1a2e;color:#eee;margin:0;padding:20px}}
  h1,h2{{color:#2ecc71}} table{{width:100%;border-collapse:collapse;margin-bottom:24px}}
  th{{background:#16213e;padding:8px 12px;text-align:left;color:#2ecc71}}
  td{{padding:7px 12px;border-bottom:1px solid #2a2a4a}}
  tr:hover td{{background:#16213e}} .win{{color:#2ecc71}} .loss{{color:#e74c3c}}
  .card{{background:#16213e;border-radius:8px;padding:16px;margin-bottom:20px}}
  .metrics-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}}
  .metric{{background:#0f3460;border-radius:6px;padding:12px;text-align:center}}
  .metric .val{{font-size:1.5em;font-weight:bold;color:#2ecc71}}
  .metric .lbl{{font-size:.8em;color:#aaa;margin-top:4px}}
</style>
</head>
<body>
<h1>Backtest Report — {params.symbol} / {params.interval}</h1>
<p>{params.from_dt.date()} → {params.to_dt.date()} &nbsp;|&nbsp;
   Capital: ₹{params.initial_capital:,.0f}</p>

<div class="card">
<h2>Summary Metrics</h2>
<div class="metrics-grid">
  {_metric_card("Total Trades", metrics.total_trades)}
  {_metric_card("Win Rate", f"{metrics.win_rate:.1%}")}
  {_metric_card("Profit Factor", f"{metrics.profit_factor:.2f}")}
  {_metric_card("Expectancy", f"₹{metrics.expectancy:,.0f}")}
  {_metric_card("Sharpe Ratio", f"{metrics.sharpe_ratio:.2f}")}
  {_metric_card("Sortino Ratio", f"{metrics.sortino_ratio:.2f}")}
  {_metric_card("Max Drawdown", f"{metrics.max_drawdown_pct:.1%}")}
  {_metric_card("Calmar Ratio", f"{metrics.calmar_ratio:.2f}")}
  {_metric_card("Net P&L", f"₹{metrics.total_net_pnl:,.0f}")}
  {_metric_card("Total Return", f"{metrics.total_return_pct:.2%}")}
</div></div>

<div class="card"><h2>Equity Curve</h2>{equity_div}</div>
<div class="card"><h2>Drawdown</h2>{dd_div}</div>
<div class="card"><h2>Monthly P&L</h2>{monthly_div}</div>

<div class="card">
<h2>Trade Log</h2>
<table>
<thead><tr><th>#</th><th>Symbol</th><th>Direction</th><th>Entry Time</th>
<th>Exit Time</th><th>Entry ₹</th><th>Exit ₹</th><th>Qty</th><th>Net P&L</th></tr></thead>
<tbody>{trade_rows}</tbody>
</table></div>
</body></html>"""


def _metric_card(label: str, value: Any) -> str:
    return f'<div class="metric"><div class="val">{value}</div><div class="lbl">{label}</div></div>'


def _trade_rows(trades: list[Any]) -> str:
    if not trades:
        return '<tr><td colspan="9" style="text-align:center">No trades</td></tr>'
    rows = []
    for i, t in enumerate(trades, 1):
        cls = "win" if t.net_pnl >= 0 else "loss"
        rows.append(
            f"<tr><td>{i}</td><td>{t.symbol}</td>"
            f'<td class="{cls}">{t.direction}</td>'
            f"<td>{t.entry_time.strftime('%Y-%m-%d %H:%M')}</td>"
            f"<td>{t.exit_time.strftime('%Y-%m-%d %H:%M')}</td>"
            f"<td>₹{t.entry_price:.2f}</td><td>₹{t.exit_price:.2f}</td>"
            f"<td>{t.qty}</td>"
            f'<td class="{cls}">₹{t.net_pnl:,.2f}</td></tr>'
        )
    return "\n".join(rows)
