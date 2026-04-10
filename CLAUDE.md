# AlgoTrader India — Project Bible

> **READ THIS AT THE START OF EVERY SESSION.**
> This is the single source of truth for project status, standards, and workflow.

---

## Project Overview

Fully automated intraday trading bot for NSE/BSE using Angel One SmartAPI.
- **Language:** Python 3.11+
- **Broker:** Angel One SmartAPI
- **Architecture:** Uncle Bob Clean Architecture
- **Mode:** Async-first, agent-capable, paper trading → live trading
- **Spec:** `docs/superpowers/specs/2026-04-01-algotrader-india-design.md`

---

## Session Workflow (Non-Negotiable)

Every Claude Code session follows this exact order:

```
1. Read CLAUDE.md                        ← you are here
2. Read active stage spec                ← docs/superpowers/specs/
3. Pick ONE module from the stage table below

4. Write tests FIRST (TDD)
5. Implement the module
6. Run tests — must pass before continuing

7. Brutal self-review — edge cases, async safety, error paths
8. Invoke superpowers:code-reviewer skill

9. Commit to stage branch
   Format: feat(stage-N): module-name — what it does
10. Update CLAUDE.md — mark module done, log any improvements found
```

---

## Architecture Layers

```
core/entities/       ← Pure frozen dataclasses. Zero dependencies.
core/interfaces/     ← Protocols / ABCs only. Zero dependencies.
core/use_cases/      ← Business logic. Depends on entities + interfaces only.
adapters/            ← Implements interfaces. Angel One, Telegram, Scanner.
infrastructure/      ← DB, scheduler, dashboard, config.
strategies/          ← Pluggable. Each implements BaseStrategy.
backtester/          ← Standalone system. Depends on strategies + data layer.
tests/               ← Mirrors src structure exactly.
scripts/             ← Entry points only. No business logic.
```

**Dependency rule:** Outer layers depend on inner. Inner layers NEVER import outer.

---

## Coding Standards

| Rule | Detail |
|---|---|
| File length | Max 150 lines — split if exceeded |
| Function length | Max 20 lines — extract if exceeded |
| Type hints | Mandatory on all public functions and class attributes |
| Docstrings | Public interfaces and ABCs only — not internals |
| Logging | Standard `logging` + `python-json-logger` formatter — never `print()` |
| Exceptions | Always catch specific exceptions — never bare `except:` |
| Config | No hardcoded values — use `config/settings.yaml` or `.env` |
| Async | `async/await` on all broker, data feed, execution code |
| Entities | Frozen dataclasses — immutable after creation |
| Imports | Absolute imports only — no relative `..` imports |

---

## Security Rules

| Rule | Detail |
|---|---|
| Secrets | `.env` is gitignored. Never commit real credentials. |
| Credential logging | Log formatter strips `token`, `password`, `totp` fields — always. |
| Config loading | `pydantic-settings` from `.env` only — fails fast at startup if missing. |
| Kill switch | 3% daily loss hard-cuts all trading — no override in code. |
| Web UI | All FastAPI routes require auth — no public endpoints. |
| Pre-commit hook | Installed in Stage 1 — blocks any commit containing secret patterns. |

---

## Git Conventions

| Rule | Detail |
|---|---|
| Branches | One branch per stage: `stage-N/feature-name` |
| Commits | `feat(stage-N): module-name — what it does` |
| Main | Never commit directly to main |
| Tests | Never commit failing tests |
| Merging | Merge stage branch to main only after stage is fully complete |

---

## Stage Status

| Stage | Branch | Status | Sessions Done | Total Sessions |
|---|---|---|---|---|
| 1 — Foundation | `stage-1/foundation` | COMPLETE | 7 | 7 |
| 2 — Backtesting | `stage-2/backtest` | COMPLETE | 10 | 10 |
| 3 — Scanner + Risk | `stage-3/scanner-risk` | COMPLETE | 8 | 8 |
| 4 — Execution | `stage-4/execution` | COMPLETE | 6 | 6 |
| 5 — Deploy | `stage-5/deploy` | PENDING | 0 | 6 |

**Total:** ~37 sessions across 5 stages.

---

## Stage 1 — Foundation Module Status

| # | Module | File | Status | Notes |
|---|---|---|---|---|
| 1 | Project scaffold | root setup | DONE | |
| 2 | Config loader | infrastructure/config/settings.py | DONE | |
| 3 | Base entities | core/entities/ | DONE | Signal, Order, Trade, Position + IBroker, IDataFeed interfaces |
| 4 | Broker auth | adapters/broker/angel_broker.py | DONE | TOTP login, JWT storage, auto-refresh, relogin fallback |
| 5 | Broker data | adapters/broker/angel_broker_data.py | DONE | Split into mixin (AngelBrokerDataMixin) to keep files under 150 lines |
| 6 | WebSocket feed | adapters/data/data_feed.py | DONE | SmartWebSocketV2 wrapper; auto-resubscribe on reconnect via _on_open; asyncio.to_thread for blocking SDK calls |
| 7 | Data cacher | adapters/data/data_cacher.py | DONE | Parquet merge/dedup, atomic writes, path-traversal guard, corrupt-cache recovery, IDataCacher protocol |

---

## Stage 2 — Backtesting Module Status

| # | Module | File | Status | Notes |
|---|---|---|---|---|
| 1 | Base strategy protocol | core/interfaces/i_strategy.py | DONE | IStrategy protocol, BaseStrategy ABC, BacktestParams frozen dataclass |
| 2 | Trade simulator | backtester/trade_simulator.py | DONE | Fill sim (SL/target/EOD exit), Indian charges (STT, GST, stamp, SEBI), SimulatedTrade |
| 3 | Performance metrics | backtester/metrics.py | DONE | Sharpe, Sortino, max drawdown, win rate, expectancy, Calmar, profit factor, MetricsResult |
| 4 | HTML report generator | backtester/report.py | DONE | Plotly equity curve + drawdown + monthly P&L, metrics grid, trade log table |
| 5 | ORB strategy | strategies/orb.py | DONE | Opening range breakout, buffer, configurable multiplier, one signal per session |
| 6 | VWAP Reversion | strategies/vwap_reversion.py | DONE | Session VWAP, deviation threshold, fade signal, one per session |
| 7 | Momentum Breakout | strategies/momentum_breakout.py | DONE | N-bar high/low breakout with volume confirmation, configurable lookback |
| 8 | EMA Crossover | strategies/ema_crossover.py | DONE | 9/21 EMA, strict crossover detection, SL=slow EMA, configurable multiplier |
| 9 | Gap Fill | strategies/gap_fill.py | DONE | Day-boundary gap detection, fade to prev_close, configurable threshold + SL multiplier |
| 10 | Parameter optimizer | backtester/optimizer.py | DONE | Grid search, run_backtest pipeline, OptimizationResult, configurable optimize_for |

---

## Stage 3 — Scanner + Risk Module Status

| # | Module | File | Status | Notes |
|---|---|---|---|---|
| 1 | Liquidity filter | adapters/scanner/filters/liquidity.py | DONE | avg_vol >= 5L, avg_turnover >= 10Cr |
| 2 | Volatility filter | adapters/scanner/filters/volatility.py | DONE | ATR(14) > 1.5%, price ₹100–5000 |
| 3 | Technical filter | adapters/scanner/filters/technical.py | DONE | RSI 30-70, EMA9/21/50 proximity 3%, VWAP proximity 3% |
| 4 | Pre-market signals | adapters/scanner/filters/premarket.py | DONE | gap > 0.5%, volume spike >= 1.5x |
| 5 | Scanner ranker | adapters/scanner/scanner.py | DONE | filter pipeline, vol*ATR% composite score, max-15 |
| 6 | Position sizer | core/use_cases/position_sizer.py | DONE | risk_pct/sl_distance, max_qty cap, floor division |
| 7 | Risk validator | core/use_cases/risk_manager.py | DONE | kill switch, daily loss, time gate, position cap, cooldown |
| 8 | Portfolio tracker | core/use_cases/portfolio_tracker.py | DONE | cash, positions, day P&L, equity mark-to-market, drawdown |

---

## Stage 4 — Execution Module Status

| # | Module | File | Status | Notes |
|---|---|---|---|---|
| 1 | Strategy engine | core/use_cases/strategy_engine.py | DONE | multi-strategy runner, per-strategy enable/disable, error isolation |
| 2 | Paper trader | adapters/paper_trader.py | DONE | SQLite journal, fill/close, day P&L, open trades — tmp_path fix for Windows |
| 3 | Live execution | adapters/broker/execution_engine.py | DONE | async place_entry, place_sl_order, cancel, fill monitor |
| 4 | Square-off manager | core/use_cases/square_off_manager.py | DONE | 15:10 cutoff, force close all via LTP, entry_price fallback |
| 5 | Scheduler | infrastructure/scheduler/jobs.py | DONE | APScheduler cron/interval, scanner/strategy/square-off/report jobs |
| 6 | Terminal dashboard | infrastructure/dashboard/terminal_ui.py | DONE | Rich tables: positions, signals, summary — returns string for testing |

---

## Stage 5 — Deploy Module Status

| # | Module | File | Status | Notes |
|---|---|---|---|---|
| 1 | Telegram notifier | adapters/notifications/telegram_notifier.py | PENDING | |
| 2 | Error recovery | adapters/broker/error_recovery.py | PENDING | |
| 3 | Web UI | infrastructure/dashboard/web_ui.py | PENDING | |
| 4 | Health monitor | infrastructure/health_monitor.py | PENDING | |
| 5 | VPS deploy scripts | scripts/deploy/ | PENDING | |
| 6 | Integration tests | tests/integration/ | PENDING | |

---

## Improvements Backlog

> Add discoveries during sessions. Never delete — mark as RESOLVED with date.

- `detect-secrets` is not installed in the current Python environment. Run `pip install detect-secrets` then regenerate `.secrets.baseline` with `python -m detect_secrets scan > .secrets.baseline` so the pre-commit hook has an accurate baseline.

<!-- Format: - [OPEN/RESOLVED date] Stage N: description -->

---

## Session Log

> Update at end of every session.

<!-- Format:
### YYYY-MM-DD
- Stage N, Session M: what was built
- Next: what the next session should pick up
-->

### 2026-04-10 (continued)
- Stage 4, Sessions 1-6: Execution — all 6 modules complete. 69 new tests, 412 total pass. Stage 4 COMPLETE.
  - Strategy engine: multi-strategy runner, error isolation per strategy
  - Paper trader: SQLite journal, fill/close/day P&L (Windows tmp_path fix for SQLite file lock)
  - Execution engine: async order placement, SL order, cancel, fill monitor
  - Square-off manager: 15:10 cutoff, LTP/entry fallback force close
  - Scheduler: APScheduler cron+interval for all 4 job types
  - Terminal dashboard: Rich tables (positions/signals/summary), string output for testability
- Next: Merge stage-4/execution → main, then begin Stage 5 (Deploy)

### 2026-04-10
- Stage 3, Sessions 1-8: Scanner + Risk — all 8 modules complete in one session. 115 new tests, 343 total pass. Stage 3 COMPLETE.
  - Liquidity filter: avg_vol/turnover thresholds (numpy bool → bool fix)
  - Volatility filter: Wilder ATR via EWM, price range gate
  - Technical filter: Wilder RSI (0/0→50 edge case), EMA9/21/50, VWAP proximity
  - Pre-market filter: signed gap%, volume spike multiplier
  - Scanner ranker: filter pipeline + vol*ATR% composite score, max-15 cap
  - Position sizer: floor(risk_amount / sl_distance), max_qty cap
  - Risk manager: kill switch, daily loss limit, time gate, position cap, cooldown
  - Portfolio tracker: cash, open positions, day P&L, equity, drawdown
- Next: Merge stage-3/scanner-risk → main, then begin Stage 4 (Execution)

### 2026-04-07
- Stage 2, Session 10: Parameter optimizer — grid search, run_backtest pipeline, inf-safe sort — 11 new tests, 228 total pass. Stage 2 COMPLETE.
- Stage 2, Session 9: Gap Fill — day-boundary gap detection, fade to prev_close — 17 new tests, 217 total pass.
- Stage 2, Session 8: EMA Crossover — 9/21 strict crossover, strict comparison fix for EMA init equality — 19 new tests, 200 total pass.
- Stage 2, Session 7: Momentum Breakout — N-bar high/low, volume filter, 16 new tests, 181 total pass.
- Stage 2, Session 6: VWAP Reversion — session VWAP, deviation fade, 15 new tests, 165 total pass.
- Stage 2, Session 5: ORB strategy — opening range breakout, buffer, multiplier, one signal/session — 15 new tests, 150 total pass.
- Stage 2, Session 4: HTML report — Plotly equity/drawdown/monthly charts, metrics grid, trade log — 11 new tests, 135 total pass.
- Stage 2, Session 3: Performance metrics — Sharpe, Sortino, drawdown, win rate, expectancy, Calmar, profit factor — 23 new tests, 124 total pass.
- Stage 2, Session 2: Trade simulator — fill sim, Indian charges (STT/GST/stamp/SEBI), SimulatedTrade — 15 new tests, 101 total pass.
- Stage 2, Session 1: Base strategy protocol — IStrategy protocol, BaseStrategy ABC, BacktestParams — 14 new tests, 86 total pass.
- Next: Stage 2, Module 2 — Trade simulator (backtester/trade_simulator.py)

### 2026-04-05
- Stage 1, Session 7: Data cacher — Parquet merge/dedup, atomic writes, path-traversal guard, corrupt-cache recovery, tz normalization, IDataCacher protocol — 22 new tests, 72 total pass. Stage 1 COMPLETE — ready to merge to main.
- Next: Merge stage-2/backtest → main, then begin Stage 3 (scanner + risk)

### 2026-04-02
- Stage 1, Session 6: WebSocket feed — tick subscription, auto-resubscribe on reconnect — 9 new tests, 50 total pass. Fixed SmartApi import path (SmartApi.smartWebSocketV2 not SmartWebSocketV2).
- Stage 1, Session 5: Broker data methods — get_historical, get_ltp, get_funds, get_positions, get_orders — 7 new tests, 41 total pass. Data methods split into AngelBrokerDataMixin (angel_broker_data.py) to stay under 150 lines.
- Stage 1, Session 4: Broker auth — TOTP login, JWT storage, auto-refresh with relogin fallback — 7 tests, all pass (31 total)
- Stage 1, Session 3: Base entities + interfaces — Signal, Trade, Order, Position, IBroker, IDataFeed — 11 tests, all pass

### 2026-04-01
- Stage 1, Session 1: Project scaffold — git init, directories, requirements, pre-commit
- Stage 1, Session 2: Config loader — BrokerConfig, TradingConfig, RiskConfig, get_settings singleton

---

## Key Risks to Watch

| Risk | Watch For |
|---|---|
| Angel One WebSocket drops silently | Implement heartbeat in Stage 1, Session 6 |
| Token refresh fails mid-session | Add auto-refresh 5 min before expiry in Stage 1, Session 4 |
| SL not placed after entry fill | Atomic OCO logic in Stage 4, Session 3 |
| Race condition on SL + target | OCO cancel-other logic in Stage 4, Session 3 |
| Strategy signal during square-off window | RiskManager time gate in Stage 3, Session 7 |
