"""Chart builders for the backtest HTML report (Plotly figures)."""
from datetime import datetime
from typing import Any

import plotly.graph_objects as go
import pandas as pd


def equity_curve_chart(trades: list[Any], initial_capital: float) -> str:
    """Return Plotly equity curve as an HTML div string."""
    equity = [initial_capital]
    times = [trades[0].entry_time if trades else datetime.now()]
    for t in trades:
        equity.append(equity[-1] + t.net_pnl)
        times.append(t.exit_time)

    fig = go.Figure(go.Scatter(x=times, y=equity, mode="lines", name="Equity",
                               line=dict(color="#2ecc71", width=2)))
    fig.update_layout(title="Equity Curve", xaxis_title="Date",
                      yaxis_title="Portfolio Value (₹)", template="plotly_dark",
                      height=350, margin=dict(l=40, r=20, t=50, b=40))
    return fig.to_html(full_html=False, include_plotlyjs=False)


def drawdown_chart(trades: list[Any], initial_capital: float) -> str:
    """Return Plotly drawdown chart as an HTML div string."""
    equity = [initial_capital]
    times = [trades[0].entry_time if trades else datetime.now()]
    for t in trades:
        equity.append(equity[-1] + t.net_pnl)
        times.append(t.exit_time)

    peak = equity[0]
    drawdowns = []
    for v in equity:
        if v > peak:
            peak = v
        drawdowns.append((v - peak) / peak * 100)

    fig = go.Figure(go.Scatter(x=times, y=drawdowns, mode="lines", fill="tozeroy",
                               name="Drawdown", line=dict(color="#e74c3c", width=1.5)))
    fig.update_layout(title="Drawdown (%)", xaxis_title="Date",
                      yaxis_title="Drawdown %", template="plotly_dark",
                      height=280, margin=dict(l=40, r=20, t=50, b=40))
    return fig.to_html(full_html=False, include_plotlyjs=False)


def monthly_pnl_chart(trades: list[Any]) -> str:
    """Return Plotly monthly P&L bar chart as an HTML div string."""
    if not trades:
        fig = go.Figure()
        fig.update_layout(title="Monthly P&L", template="plotly_dark", height=280)
        return fig.to_html(full_html=False, include_plotlyjs=False)

    records = [{"month": t.exit_time.strftime("%Y-%m"), "pnl": t.net_pnl}
               for t in trades]
    df = pd.DataFrame(records).groupby("month")["pnl"].sum().reset_index()
    colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in df["pnl"]]
    fig = go.Figure(go.Bar(x=df["month"], y=df["pnl"], marker_color=colors,
                           name="Monthly P&L"))
    fig.update_layout(title="Monthly P&L (₹)", xaxis_title="Month",
                      yaxis_title="Net P&L (₹)", template="plotly_dark",
                      height=280, margin=dict(l=40, r=20, t=50, b=40))
    return fig.to_html(full_html=False, include_plotlyjs=False)
