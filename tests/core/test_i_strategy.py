"""Tests for IStrategy protocol and BacktestParams contract."""
import pytest
import pandas as pd
from datetime import datetime
from abc import ABC


# ─── IStrategy protocol ───

def test_i_strategy_is_runtime_checkable():
    from core.interfaces.i_strategy import IStrategy
    from typing import runtime_checkable, Protocol
    assert issubclass(IStrategy, Protocol)


def test_concrete_strategy_satisfies_i_strategy():
    from core.interfaces.i_strategy import IStrategy
    from core.entities.signal import Signal
    from strategies.base_strategy import BaseStrategy

    class MyStrategy(BaseStrategy):
        @property
        def name(self) -> str:
            return "test"

        def generate_signals(self, df, symbol):
            return []

    s = MyStrategy(params={})
    assert isinstance(s, IStrategy)


def test_object_missing_generate_signals_fails_i_strategy_check():
    from core.interfaces.i_strategy import IStrategy

    class NotAStrategy:
        @property
        def name(self):
            return "x"
        @property
        def params(self):
            return {}

    assert not isinstance(NotAStrategy(), IStrategy)


# ─── BaseStrategy ABC ───

def test_base_strategy_is_abstract():
    from strategies.base_strategy import BaseStrategy
    assert issubclass(BaseStrategy, ABC)


def test_base_strategy_cannot_be_instantiated_directly():
    from strategies.base_strategy import BaseStrategy
    with pytest.raises(TypeError):
        BaseStrategy(params={})


def test_base_strategy_subclass_without_name_raises():
    from strategies.base_strategy import BaseStrategy
    from core.entities.signal import Signal

    class BadStrategy(BaseStrategy):
        def generate_signals(self, df, symbol):
            return []

    with pytest.raises(TypeError):
        BadStrategy(params={})


def test_base_strategy_subclass_without_generate_signals_raises():
    from strategies.base_strategy import BaseStrategy

    class BadStrategy(BaseStrategy):
        @property
        def name(self):
            return "bad"

    with pytest.raises(TypeError):
        BadStrategy(params={})


def test_base_strategy_stores_params():
    from strategies.base_strategy import BaseStrategy

    class GoodStrategy(BaseStrategy):
        @property
        def name(self):
            return "good"

        def generate_signals(self, df, symbol):
            return []

    s = GoodStrategy(params={"window": 14})
    assert s.params == {"window": 14}


def test_base_strategy_generate_signals_returns_list():
    from strategies.base_strategy import BaseStrategy
    import pandas as pd

    class GoodStrategy(BaseStrategy):
        @property
        def name(self):
            return "good"

        def generate_signals(self, df, symbol):
            return []

    s = GoodStrategy(params={})
    df = pd.DataFrame({"open": [100], "high": [101], "low": [99],
                       "close": [100.5], "volume": [1000]})
    result = s.generate_signals(df, "RELIANCE")
    assert isinstance(result, list)


# ─── BacktestParams ───

def test_backtest_params_creates_correctly():
    from strategies.base_strategy import BacktestParams
    bp = BacktestParams(
        symbol="RELIANCE",
        token="2885",
        interval="5m",
        from_dt=datetime(2026, 1, 1),
        to_dt=datetime(2026, 3, 31),
    )
    assert bp.symbol == "RELIANCE"
    assert bp.initial_capital == 100000.0


def test_backtest_params_is_frozen():
    from strategies.base_strategy import BacktestParams
    bp = BacktestParams(
        symbol="RELIANCE", token="2885", interval="5m",
        from_dt=datetime(2026, 1, 1), to_dt=datetime(2026, 3, 31),
    )
    with pytest.raises((AttributeError, TypeError)):
        bp.symbol = "INFY"


def test_backtest_params_rejects_from_dt_after_to_dt():
    from strategies.base_strategy import BacktestParams
    with pytest.raises(ValueError, match="from_dt"):
        BacktestParams(
            symbol="RELIANCE", token="2885", interval="5m",
            from_dt=datetime(2026, 3, 31), to_dt=datetime(2026, 1, 1),
        )


def test_backtest_params_rejects_invalid_interval():
    from strategies.base_strategy import BacktestParams
    with pytest.raises(ValueError, match="interval"):
        BacktestParams(
            symbol="RELIANCE", token="2885", interval="2m",
            from_dt=datetime(2026, 1, 1), to_dt=datetime(2026, 3, 31),
        )


def test_backtest_params_rejects_non_positive_capital():
    from strategies.base_strategy import BacktestParams
    with pytest.raises(ValueError, match="initial_capital"):
        BacktestParams(
            symbol="RELIANCE", token="2885", interval="5m",
            from_dt=datetime(2026, 1, 1), to_dt=datetime(2026, 3, 31),
            initial_capital=0,
        )
