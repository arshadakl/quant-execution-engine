# Quant Execution Engine

A fully automated intraday trading bot for NSE/BSE built on Angel One SmartAPI.
Async-first, clean architecture, paper trading → live trading.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Quant Execution Engine                        │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │  Stock   │  │ Strategy │  │   Risk   │  │Execution │            │
│  │ Scanner  │──│  Engine  │──│ Manager  │──│  Engine  │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
│       │              │              │              │                 │
│       ▼              ▼              ▼              ▼                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │   Data   │  │Backtester│  │Portfolio │  │  Paper   │            │
│  │  Feed   │  │          │  │ Tracker  │  │ Trading  │            │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │
│                                                                      │
│  ┌──────────────────────────────────────────────────────┐           │
│  │              Dashboard / Monitoring                   │           │
│  │         (Terminal UI + Optional Web UI)               │           │
│  └──────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## How It Works

### 1. Pre-Market Scanner (08:50 AM)
Before the market opens, the scanner filters the NSE universe down to a focused watchlist (max 15 stocks) using a chain of filters:
- **Liquidity** — volume > 5L, turnover > ₹10 Cr
- **Volatility** — ATR(14) > 1.5%, price between ₹100–₹5000
- **Technical** — EMA 9/21/50 proximity, RSI 30–70, VWAP positioning
- **Pre-market** — gap detection (>0.5%), volume spikes, sector strength

### 2. Real-Time Data Feed (09:15 AM onwards)
A WebSocket connection to Angel One streams live ticks for all watchlist symbols. The feed auto-resubscribes on reconnect — no manual intervention needed.

### 3. Strategy Engine
Multiple strategies run simultaneously on live tick data. Each strategy is pluggable and independently backtestable:

| Strategy | Logic |
|---|---|
| **ORB** (Opening Range Breakout) | Captures breakout above/below the first 15-minute candle range |
| **VWAP Reversion** | Fades moves that deviate >1.5% from VWAP back toward it |
| **Momentum Breakout** | Enters on high-volume price breakouts with trend confirmation |
| **EMA Crossover** | Trades the 9/21 EMA crossover with volume filter |
| **Gap Fill** | Fades overnight gaps that statistically revert intraday |

### 4. Risk Manager
Every signal passes through the risk manager before an order is placed:
- Max 60% capital deployed at any time
- 1.5% risk per trade (position sized by SL distance)
- Max 5 open positions simultaneously
- No new trades after 2:30 PM
- **3% daily loss kill switch** — hard stops all trading, no code override possible
- 30-minute cooldown after 3 consecutive losses

### 5. Order Execution
- **Paper mode** — simulates fills via LTP, journals all trades to SQLite
- **Live mode** — places real orders via Angel One SmartAPI with OCO logic (entry + SL placed atomically)
- Force square-off of all positions at 3:10 PM

### 6. Parquet Data Cache
Historical OHLCV data is cached locally as Parquet files. Cache-first loading means the broker API is only called for data not already on disk. Saves merge with existing cache and deduplicate automatically.

### 7. Monitoring
- **Terminal dashboard** — live positions, signals, P&L, scanner results (Rich/Textual)
- **Web UI** — FastAPI + HTMX: positions, trade history, strategy toggles, risk params
- **Telegram** — trade entry/exit alerts, daily summary, kill switch notifications

---

## Architecture

Uncle Bob Clean Architecture — strict dependency rule: outer layers depend on inner, never reverse.

```
core/entities/       ← Pure frozen dataclasses (Signal, Order, Trade, Position)
core/interfaces/     ← Protocols only — IBroker, IDataFeed, IDataCacher, IStrategy
core/use_cases/      ← Business logic — RiskManager, StrategyEngine, PortfolioTracker
adapters/            ← AngelBroker, DataFeed, DataCacher, Scanner, TelegramNotifier
infrastructure/      ← Config, scheduler, SQLite DB, dashboard
strategies/          ← Pluggable strategies, each implements BaseStrategy
backtester/          ← Standalone backtesting engine
```

---

## Tech Stack

| Layer | Tech |
|---|---|
| Language | Python 3.11+ |
| Broker API | Angel One SmartAPI |
| Real-time data | SmartWebSocketV2 |
| Async runtime | asyncio |
| Data | pandas, pyarrow (Parquet) |
| Config | pydantic-settings + YAML |
| Scheduling | APScheduler |
| Terminal UI | Rich / Textual |
| Web UI | FastAPI + HTMX |
| Database | SQLite |
| Notifications | Telegram Bot API |
| Testing | pytest + pytest-asyncio |

---

## Project Status

| Stage | What | Status |
|---|---|---|
| 1 — Foundation | Broker auth, data feed, config, entities, cacher | **COMPLETE** |
| 2 — Backtesting | Backtest engine, 5 strategies, performance metrics, HTML reports | Pending |
| 3 — Scanner + Risk | Pre-market scanner, position sizer, risk validator | Pending |
| 4 — Execution | Strategy engine, paper trader, live execution, square-off | Pending |
| 5 — Deploy | Telegram, web UI, health monitor, VPS deploy scripts | Pending |

---

## Setup

### Prerequisites
- Python 3.11+
- Angel One SmartAPI account with API key enabled
- Telegram bot token (optional, for notifications)

### Install

```bash
git clone https://github.com/arshadakl/quant-execution-engine.git
cd quant-execution-engine
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
ANGEL_API_KEY=your_api_key
ANGEL_CLIENT_ID=your_client_id
ANGEL_PASSWORD=your_password
ANGEL_TOTP_SECRET=your_totp_secret
TELEGRAM_BOT_TOKEN=your_bot_token      # optional
TELEGRAM_CHAT_ID=your_chat_id          # optional
```

Adjust trading parameters in `config/settings.yaml` — capital, risk limits, active strategies, scanner filters.

### Run

```bash
# Paper trading (safe — no real orders)
python scripts/run_bot.py

# Run backtest
python scripts/run_backtest.py
```

### Test

```bash
pytest
```

---

## Risk Disclaimer

This software is for educational and research purposes. Algorithmic trading involves significant financial risk. Always run in paper mode first, understand the strategies fully, and never risk capital you cannot afford to lose. The authors are not responsible for any financial losses.
