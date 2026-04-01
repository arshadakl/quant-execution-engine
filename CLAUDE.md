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
| 1 — Foundation | `stage-1/foundation` | IN PROGRESS | 1 | 7 |
| 2 — Backtesting | `stage-2/backtest` | PENDING | 0 | 10 |
| 3 — Scanner + Risk | `stage-3/scanner-risk` | PENDING | 0 | 8 |
| 4 — Execution | `stage-4/execution` | PENDING | 0 | 6 |
| 5 — Deploy | `stage-5/deploy` | PENDING | 0 | 6 |

**Total:** ~37 sessions across 5 stages.

---

## Stage 1 — Foundation Module Status

| # | Module | File | Status | Notes |
|---|---|---|---|---|
| 1 | Project scaffold | root setup | DONE | |
| 2 | Config loader | infrastructure/config/settings.py | PENDING | |
| 3 | Base entities | core/entities/ | PENDING | |
| 4 | Broker auth | adapters/broker/angel_broker.py | PENDING | |
| 5 | Broker data | adapters/broker/angel_broker.py | PENDING | |
| 6 | WebSocket feed | adapters/data/data_feed.py | PENDING | |
| 7 | Data cacher | adapters/data/data_cacher.py | PENDING | |

---

## Stage 2 — Backtesting Module Status

| # | Module | File | Status | Notes |
|---|---|---|---|---|
| 1 | Base strategy protocol | core/interfaces/i_strategy.py | PENDING | |
| 2 | Trade simulator | backtester/trade_simulator.py | PENDING | |
| 3 | Performance metrics | backtester/metrics.py | PENDING | |
| 4 | HTML report generator | backtester/report.py | PENDING | |
| 5 | ORB strategy | strategies/orb.py | PENDING | |
| 6 | VWAP Reversion | strategies/vwap_reversion.py | PENDING | |
| 7 | Momentum Breakout | strategies/momentum_breakout.py | PENDING | |
| 8 | EMA Crossover | strategies/ema_crossover.py | PENDING | |
| 9 | Gap Fill | strategies/gap_fill.py | PENDING | |
| 10 | Parameter optimizer | backtester/optimizer.py | PENDING | |

---

## Stage 3 — Scanner + Risk Module Status

| # | Module | File | Status | Notes |
|---|---|---|---|---|
| 1 | Liquidity filter | adapters/scanner/filters/liquidity.py | PENDING | |
| 2 | Volatility filter | adapters/scanner/filters/volatility.py | PENDING | |
| 3 | Technical filter | adapters/scanner/filters/technical.py | PENDING | |
| 4 | Pre-market signals | adapters/scanner/filters/premarket.py | PENDING | |
| 5 | Scanner ranker | adapters/scanner/scanner.py | PENDING | |
| 6 | Position sizer | core/use_cases/position_sizer.py | PENDING | |
| 7 | Risk validator | core/use_cases/risk_manager.py | PENDING | |
| 8 | Portfolio tracker | core/use_cases/portfolio_tracker.py | PENDING | |

---

## Stage 4 — Execution Module Status

| # | Module | File | Status | Notes |
|---|---|---|---|---|
| 1 | Strategy engine | core/use_cases/strategy_engine.py | PENDING | |
| 2 | Paper trader | adapters/paper_trader.py | PENDING | |
| 3 | Live execution | adapters/broker/execution_engine.py | PENDING | |
| 4 | Square-off manager | core/use_cases/square_off_manager.py | PENDING | |
| 5 | Scheduler | infrastructure/scheduler/jobs.py | PENDING | |
| 6 | Terminal dashboard | infrastructure/dashboard/terminal_ui.py | PENDING | |

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

<!-- Format: - [OPEN/RESOLVED date] Stage N: description -->

---

## Session Log

> Update at end of every session.

<!-- Format:
### YYYY-MM-DD
- Stage N, Session M: what was built
- Next: what the next session should pick up
-->

### 2026-04-01
- Stage 1, Session 1: Project scaffold — git init, directories, requirements, pre-commit
- Next: Config loader (infrastructure/config/settings.py)

---

## Key Risks to Watch

| Risk | Watch For |
|---|---|
| Angel One WebSocket drops silently | Implement heartbeat in Stage 1, Session 6 |
| Token refresh fails mid-session | Add auto-refresh 5 min before expiry in Stage 1, Session 4 |
| SL not placed after entry fill | Atomic OCO logic in Stage 4, Session 3 |
| Race condition on SL + target | OCO cancel-other logic in Stage 4, Session 3 |
| Strategy signal during square-off window | RiskManager time gate in Stage 3, Session 7 |
