"""Tests for Strategy Engine."""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from core.entities.signal import Signal


def _make_df(n: int = 60, close: float = 500.0) -> pd.DataFrame:
    idx = [datetime(2026, 1, 2, 9, 15) + timedelta(minutes=i * 5) for i in range(n)]
    return pd.DataFrame(
        [{"open": close - 1, "high": close + 2, "low": close - 2,
          "close": close, "volume": 600_000}
         for _ in range(n)],
        index=idx,
    )


def _make_signal(symbol: str = "RELIANCE", direction: str = "LONG") -> Signal:
    sl = 490.0 if direction == "LONG" else 510.0
    target = 520.0 if direction == "LONG" else 480.0
    return Signal(
        symbol=symbol,
        direction=direction,
        entry_price=500.0,
        stop_loss=sl,
        target_1=target,
        timestamp=datetime(2026, 1, 2, 10, 0),
        strategy="test",
    )


def _mock_strategy(signals: list) -> MagicMock:
    s = MagicMock()
    s.name = "mock_strategy"
    s.generate_signals.return_value = signals
    return s


# ─── Instantiation ───

def test_instantiates_with_empty_strategies():
    from core.use_cases.strategy_engine import StrategyEngine
    eng = StrategyEngine(strategies=[])
    assert eng.strategies == []


def test_instantiates_with_strategies():
    from core.use_cases.strategy_engine import StrategyEngine
    strat = _mock_strategy([])
    eng = StrategyEngine(strategies=[strat])
    assert len(eng.strategies) == 1


# ─── run returns no signals when no strategies ───

def test_run_returns_empty_with_no_strategies():
    from core.use_cases.strategy_engine import StrategyEngine
    eng = StrategyEngine(strategies=[])
    result = eng.run(symbol="RELIANCE", df=_make_df())
    assert result == []


# ─── Signal aggregation ───

def test_collects_signals_from_single_strategy():
    from core.use_cases.strategy_engine import StrategyEngine
    sig = _make_signal()
    strat = _mock_strategy([sig])
    eng = StrategyEngine(strategies=[strat])
    result = eng.run(symbol="RELIANCE", df=_make_df())
    assert result == [sig]


def test_collects_signals_from_multiple_strategies():
    from core.use_cases.strategy_engine import StrategyEngine
    sig1 = _make_signal("RELIANCE", "LONG")
    sig2 = _make_signal("RELIANCE", "SHORT")
    strat1 = _mock_strategy([sig1])
    strat2 = _mock_strategy([sig2])
    eng = StrategyEngine(strategies=[strat1, strat2])
    result = eng.run(symbol="RELIANCE", df=_make_df())
    assert len(result) == 2
    assert sig1 in result
    assert sig2 in result


def test_returns_empty_when_strategies_produce_no_signals():
    from core.use_cases.strategy_engine import StrategyEngine
    strat = _mock_strategy([])
    eng = StrategyEngine(strategies=[strat])
    result = eng.run(symbol="RELIANCE", df=_make_df())
    assert result == []


# ─── Strategy isolation — one strategy error does not kill others ───

def test_continues_on_strategy_exception():
    from core.use_cases.strategy_engine import StrategyEngine
    bad = MagicMock()
    bad.name = "bad_strategy"
    bad.generate_signals.side_effect = RuntimeError("boom")
    sig = _make_signal()
    good = _mock_strategy([sig])
    eng = StrategyEngine(strategies=[bad, good])
    result = eng.run(symbol="RELIANCE", df=_make_df())
    assert result == [sig]


# ─── Each strategy receives the same df and symbol ───

def test_each_strategy_called_with_correct_args():
    from core.use_cases.strategy_engine import StrategyEngine
    strat = _mock_strategy([])
    df = _make_df()
    eng = StrategyEngine(strategies=[strat])
    eng.run(symbol="RELIANCE", df=df)
    strat.generate_signals.assert_called_once_with(df, "RELIANCE")


# ─── Enabled/disabled strategies ───

def test_disabled_strategy_is_skipped():
    from core.use_cases.strategy_engine import StrategyEngine
    sig = _make_signal()
    strat = _mock_strategy([sig])
    eng = StrategyEngine(strategies=[strat], enabled={"mock_strategy": False})
    result = eng.run(symbol="RELIANCE", df=_make_df())
    assert result == []


def test_enabled_strategy_is_run():
    from core.use_cases.strategy_engine import StrategyEngine
    sig = _make_signal()
    strat = _mock_strategy([sig])
    eng = StrategyEngine(strategies=[strat], enabled={"mock_strategy": True})
    result = eng.run(symbol="RELIANCE", df=_make_df())
    assert result == [sig]


def test_all_strategies_run_by_default():
    from core.use_cases.strategy_engine import StrategyEngine
    sig = _make_signal()
    strat = _mock_strategy([sig])
    # no enabled dict → all run
    eng = StrategyEngine(strategies=[strat])
    result = eng.run(symbol="RELIANCE", df=_make_df())
    assert result == [sig]


# ─── Return type ───

def test_run_returns_list():
    from core.use_cases.strategy_engine import StrategyEngine
    eng = StrategyEngine(strategies=[])
    result = eng.run(symbol="RELIANCE", df=_make_df())
    assert isinstance(result, list)
