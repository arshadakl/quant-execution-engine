# AlgoTrader India — Build Design Spec
**Date:** 2026-04-01
**Author:** Arshad
**Status:** Approved

---

## 1. Project Summary

A fully automated intraday trading bot for NSE/BSE using Angel One SmartAPI.
Built in Python 3.11+, async-first, clean architecture, agent-capable.
Deployed locally first, then VPS.

---

## 2. Architecture

Uncle Bob Clean Architecture — strict dependency rule (outer depends on inner, never reverse):

```
core/entities/          ← Pure data models. No dependencies.
core/interfaces/        ← Abstract protocols. No dependencies.
core/use_cases/         ← Business logic. Depends only on entities + interfaces.
adapters/               ← Implements interfaces. Depends on use_cases + entities.
infrastructure/         ← Frameworks, DB, config. Depends on adapters.
strategies/             ← Pluggable. Implements BaseStrategy protocol.
backtester/             ← Standalone. Depends on strategies + data layer.
```

### Directory Structure

```
algotrader-india/
├── core/
│   ├── entities/               # Signal, Trade, Order, Position — pure dataclasses
│   ├── interfaces/             # IBroker, IDataFeed, IStrategy, INotifier protocols
│   └── use_cases/              # RiskManager, StrategyEngine, PortfolioTracker
│
├── adapters/
│   ├── broker/                 # AngelBroker — implements IBroker
│   ├── data/                   # DataFeed, HistoricalFetcher, DataCacher
│   ├── scanner/                # StockScanner + filter chain
│   └── notifications/          # TelegramNotifier — implements INotifier
│
├── infrastructure/
│   ├── db/                     # SQLite repositories (trades, positions, daily summary)
│   ├── scheduler/              # APScheduler job definitions
│   ├── dashboard/              # Rich terminal UI + FastAPI web UI
│   └── config/                 # pydantic-settings loader, .env validation
│
├── strategies/                 # ORB, VWAP, Momentum, EMA, GapFill
├── backtester/                 # Engine, DataLoader, TradeSimulator, ReportGenerator
│
├── tests/                      # Mirrors src structure exactly
│   ├── core/
│   ├── adapters/
│   ├── strategies/
│   └── backtester/
│
├── scripts/                    # Entry points only — no business logic
│   ├── run_bot.py
│   ├── run_backtest.py
│   └── run_scanner.py
│
├── docs/
│   └── superpowers/specs/      # Stage design specs
│
├── config/
│   ├── settings.yaml           # Non-secret config
│   └── stock_universe.yaml     # Watchlist + sector filters
│
├── data/
│   ├── historical/             # Parquet cache
│   ├── logs/
│   └── reports/
│
├── CLAUDE.md                   # Project bible — read at every session start
├── .env.example                # Placeholder only — committed to git
├── .env                        # Real secrets — NEVER committed
└── requirements.txt
```

---

## 3. SOLID Principles Applied

| Principle | How |
|---|---|
| Single Responsibility | Every file has one reason to change. Max 150 lines per file. |
| Open/Closed | New strategy = new file implementing BaseStrategy. No existing code changes. |
| Liskov Substitution | AngelBroker, MockBroker are fully interchangeable via IBroker protocol. |
| Interface Segregation | IBroker split into IOrderBroker + IDataBroker — strategies only see what they need. |
| Dependency Inversion | RiskManager depends on IBroker interface, not AngelBroker directly. |

---

## 4. Coding Standards

- **Max file length:** 150 lines — split if exceeded
- **Max function length:** 20 lines — extract if exceeded
- **Type hints:** Mandatory on all public functions and class attributes
- **Docstrings:** Public interfaces and protocols only — not internals
- **Logging:** Standard `logging` with JSON formatter via `python-json-logger` — no `print()`
- **Exceptions:** Always catch specific exceptions — no bare `except:`
- **Config:** No hardcoded values — everything via `config/settings.yaml` or `.env`
- **Async:** `async/await` throughout broker, data feed, execution modules
- **Immutability:** Entities are frozen dataclasses — never mutated after creation

---

## 5. Security Rules

| Rule | Implementation |
|---|---|
| No secret in git | `.env` gitignored from Day 1. Pre-commit hook blocks commits with secret patterns. |
| No credential logging | Custom log formatter strips token, password, totp fields before writing. |
| Secrets via pydantic-settings | `BrokerConfig` loads from `.env` only — fails fast at startup if missing. |
| Web UI auth | FastAPI routes protected — no public endpoints, even locally. |
| Kill switch | RiskManager hard-cuts all trading at 3% daily loss — no override possible in code. |
| SQLite local only | Trade DB never synced to cloud without explicit user action. |

---

## 6. 5-Stage Breakdown

### Stage 1 — Foundation `stage-1/foundation`
**Goal:** Project skeleton + broker connection + data pipeline working end-to-end.

| # | Session | Module | File |
|---|---|---|---|
| 1 | Project scaffold | Dir structure, CLAUDE.md, pre-commit hooks, requirements.txt, .gitignore | root |
| 2 | Config loader | pydantic-settings loader, .env validation, fail-fast | infrastructure/config/settings.py |
| 3 | Base entities | Signal, Trade, Order, Position frozen dataclasses | core/entities/ |
| 4 | Broker auth | Angel One login, TOTP via pyotp, JWT token, auto-refresh | adapters/broker/angel_broker.py |
| 5 | Broker data | get_historical(), get_ltp(), get_funds(), get_positions(), get_orders() | adapters/broker/angel_broker.py |
| 6 | WebSocket feed | Tick subscription, reconnect logic, callback dispatch | adapters/data/data_feed.py |
| 7 | Data cacher | Parquet read/write, cache-first loading, date range queries | adapters/data/data_cacher.py |

---

### Stage 2 — Backtesting Engine `stage-2/backtest`
**Goal:** Run any strategy against historical data, produce full HTML report.

| # | Session | Module | File |
|---|---|---|---|
| 1 | Base strategy protocol | BaseStrategy ABC, signal interface, backtest params contract | core/interfaces/i_strategy.py + strategies/base_strategy.py |
| 2 | Trade simulator | Fill simulation, slippage, Indian market charges (STT, brokerage, GST) | backtester/trade_simulator.py |
| 3 | Performance metrics | Sharpe, Sortino, max drawdown, win rate, expectancy, Calmar, profit factor | backtester/metrics.py |
| 4 | HTML report generator | Plotly equity curve, drawdown chart, monthly heatmap, trade log | backtester/report.py |
| 5 | ORB strategy | Full implementation, unit tests, first backtest run | strategies/orb.py |
| 6 | VWAP Reversion | Full implementation + tests | strategies/vwap_reversion.py |
| 7 | Momentum Breakout | Full implementation + tests | strategies/momentum_breakout.py |
| 8 | EMA Crossover | Full implementation + tests | strategies/ema_crossover.py |
| 9 | Gap Fill | Full implementation + tests | strategies/gap_fill.py |
| 10 | Parameter optimizer | Grid search over param_grid, optimize for Sharpe ratio | backtester/optimizer.py |

---

### Stage 3 — Scanner + Risk `stage-3/scanner-risk`
**Goal:** Pre-market stock picker + risk validation working end-to-end.

| # | Session | Module | File |
|---|---|---|---|
| 1 | Liquidity filter | Volume > 5L, turnover > ₹10Cr screening | adapters/scanner/filters/liquidity.py |
| 2 | Volatility filter | ATR(14) > 1.5%, price range ₹100-₹5000 | adapters/scanner/filters/volatility.py |
| 3 | Technical filter | EMA 9/21/50 proximity, RSI 30-70, VWAP positioning | adapters/scanner/filters/technical.py |
| 4 | Pre-market signals | Gap detection (>0.5%), volume spike, sector strength | adapters/scanner/filters/premarket.py |
| 5 | Scanner ranker | Composite score calculator, final watchlist (max 15) | adapters/scanner/scanner.py |
| 6 | Position sizer | Risk formula: Risk Amount / SL Distance, max qty cap | core/use_cases/position_sizer.py |
| 7 | Risk validator | Signal validation, daily limits, kill switches, cooldown logic | core/use_cases/risk_manager.py |
| 8 | Portfolio tracker | Account balance, open positions, day P&L, drawdown tracking | core/use_cases/portfolio_tracker.py |

---

### Stage 4 — Execution `stage-4/execution`
**Goal:** Full paper trading session running during market hours.

| # | Session | Module | File |
|---|---|---|---|
| 1 | Strategy engine | Multi-strategy runner, signal aggregator, market regime selector | core/use_cases/strategy_engine.py |
| 2 | Paper trader | Simulated fills via LTP, SQLite journal, P&L tracking | adapters/paper_trader.py |
| 3 | Live execution | Order placement, fill monitor (polling), OCO logic (SL + target) | adapters/broker/execution_engine.py |
| 4 | Square-off manager | Time-based exit (3:10 PM), force close all, market orders | core/use_cases/square_off_manager.py |
| 5 | Scheduler | APScheduler: scanner job, strategy loop, square-off, daily report | infrastructure/scheduler/jobs.py |
| 6 | Terminal dashboard | Rich/Textual: live positions, signals, P&L, scanner results | infrastructure/dashboard/terminal_ui.py |

---

### Stage 5 — Deploy `stage-5/deploy`
**Goal:** Production-ready, monitored, VPS-deployable system.

| # | Session | Module | File |
|---|---|---|---|
| 1 | Telegram notifier | Trade entry/exit, daily summary, kill switch alert, error alert | adapters/notifications/telegram_notifier.py |
| 2 | Error recovery | API failure handler, WebSocket auto-reconnect, state restore on restart | adapters/broker/error_recovery.py |
| 3 | Web UI | FastAPI + HTMX: positions, trade history, strategy toggles, risk params | infrastructure/dashboard/web_ui.py |
| 4 | Health monitor | Heartbeat checker, log rotation, process auto-restart | infrastructure/health_monitor.py |
| 5 | VPS deploy scripts | Systemd service file, cron jobs, environment setup guide | scripts/deploy/ |
| 6 | Integration tests | Full end-to-end paper trade simulation with mock broker | tests/integration/ |

---

## 7. Claude Code Session Workflow

Every session follows this pattern without exception:

```
1. Read CLAUDE.md                 → current status, active stage, next module
2. Read stage spec                → docs/superpowers/specs/stage-N-*.md
3. Pick ONE module (smallest unit)

4. Write tests FIRST              → TDD — red before green
5. Implement the module           → clean arch, SOLID, typed, <150 lines
6. Run tests                      → must pass before continuing

7. Brutal self-review             → edge cases, async safety, error paths
8. Code review agent              → superpowers:code-reviewer skill

9. Commit to stage branch         → "feat(stage-N): module-name — what it does"
10. Update CLAUDE.md              → mark module done, log improvements found
```

**Hard rules:**
- One module per session — never split a module across sessions
- Never commit failing tests
- Never skip review step
- If file exceeds 150 lines → stop, split, redesign

---

## 8. Agent-Capable Architecture

Designed for multi-agent workflows:

- Every module communicates through typed interfaces — agents can work in parallel on different adapters without conflict
- `IBroker`, `IDataFeed`, `IStrategy`, `INotifier` protocols let agents swap implementations independently
- Frozen dataclasses as messages — no shared mutable state between modules
- Each stage is fully independent — a separate agent can own each stage branch
- CLAUDE.md is the handoff document — any agent reading it knows exact project state

---

## 9. Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Angel One WebSocket drops silently | Reconnect with exponential backoff, heartbeat ping every 30s |
| Token refresh fails mid-session | Auto-refresh 5 min before expiry, fallback re-login |
| Order filled but SL not placed (partial failure) | Atomic order placement with rollback — if SL fails, immediately cancel entry |
| Race condition: SL + target both trigger | OCO monitor cancels the other order immediately on first fill |
| Pre-market scanner runs before data available | Retry with backoff, fallback to previous day data |
| Strategy generates signal during square-off window | RiskManager blocks all new entries after 14:30 hard cutoff |

---

## 10. Out of Scope (v1)

- Options / F&O trading
- ML-based prediction models
- Multi-broker support
- News / sentiment analysis
- HFT strategies
- Arbitrage

*These can be added as v2 modules without changing core architecture.*
