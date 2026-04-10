"""Tests for Scanner Ranker."""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import MagicMock


def _make_df(n: int = 60, close: float = 500.0, volume: int = 600_000) -> pd.DataFrame:
    idx = [datetime(2026, 1, 2, 9, 15) + timedelta(minutes=i * 5) for i in range(n)]
    return pd.DataFrame(
        [{"open": close - 1, "high": close + 2, "low": close - 2,
          "close": close, "volume": volume}
         for _ in range(n)],
        index=idx,
    )


def _always_pass() -> MagicMock:
    f = MagicMock()
    f.passes.return_value = True
    return f


def _always_fail() -> MagicMock:
    f = MagicMock()
    f.passes.return_value = False
    return f


# ─── Instantiation ───

def test_instantiates_with_defaults():
    from adapters.scanner.scanner import ScannerRanker
    r = ScannerRanker()
    assert r.max_stocks == 15


def test_instantiates_with_custom_max():
    from adapters.scanner.scanner import ScannerRanker
    r = ScannerRanker(max_stocks=5)
    assert r.max_stocks == 5


def test_accepts_filter_list():
    from adapters.scanner.scanner import ScannerRanker
    r = ScannerRanker(filters=[_always_pass()])
    assert len(r.filters) == 1


# ─── Empty inputs ───

def test_returns_empty_on_no_candidates():
    from adapters.scanner.scanner import ScannerRanker
    r = ScannerRanker()
    assert r.scan({}) == []


# ─── Filter application ───

def test_excludes_stocks_that_fail_any_filter():
    from adapters.scanner.scanner import ScannerRanker
    fail = _always_fail()
    r = ScannerRanker(filters=[fail])
    candidates = {"RELIANCE": _make_df(), "TCS": _make_df()}
    result = r.scan(candidates)
    assert result == []


def test_includes_stocks_passing_all_filters():
    from adapters.scanner.scanner import ScannerRanker
    r = ScannerRanker(filters=[_always_pass(), _always_pass()])
    candidates = {"RELIANCE": _make_df(), "TCS": _make_df()}
    result = r.scan(candidates)
    assert set(result) == {"RELIANCE", "TCS"}


def test_partial_pass_only_passing_stocks_included():
    from adapters.scanner.scanner import ScannerRanker

    class SelectiveFilter:
        def passes(self, df, symbol):
            return symbol == "RELIANCE"

    r = ScannerRanker(filters=[SelectiveFilter()])
    candidates = {"RELIANCE": _make_df(), "TCS": _make_df()}
    result = r.scan(candidates)
    assert result == ["RELIANCE"]


# ─── Max stocks cap ───

def test_caps_result_at_max_stocks():
    from adapters.scanner.scanner import ScannerRanker
    r = ScannerRanker(max_stocks=2, filters=[_always_pass()])
    candidates = {f"STOCK{i}": _make_df() for i in range(10)}
    result = r.scan(candidates)
    assert len(result) <= 2


def test_returns_all_when_fewer_than_max():
    from adapters.scanner.scanner import ScannerRanker
    r = ScannerRanker(max_stocks=15, filters=[_always_pass()])
    candidates = {"RELIANCE": _make_df(), "TCS": _make_df()}
    result = r.scan(candidates)
    assert len(result) == 2


# ─── Ranking by score ───

def test_higher_volume_ranked_first():
    from adapters.scanner.scanner import ScannerRanker
    r = ScannerRanker(max_stocks=15, filters=[_always_pass()])
    candidates = {
        "LOW_VOL": _make_df(close=500.0, volume=500_000),
        "HIGH_VOL": _make_df(close=500.0, volume=2_000_000),
    }
    result = r.scan(candidates)
    assert result[0] == "HIGH_VOL"


def test_higher_atr_pct_ranked_first_same_volume():
    from adapters.scanner.scanner import ScannerRanker
    r = ScannerRanker(max_stocks=15, filters=[_always_pass()])
    # Same volume, different ranges → different ATR%
    idx = [datetime(2026, 1, 2, 9, 15) + timedelta(minutes=i * 5) for i in range(30)]
    low_atr = pd.DataFrame(
        [{"open": 499, "high": 501, "low": 499, "close": 500.0, "volume": 600_000}
         for _ in range(30)], index=idx)
    high_atr = pd.DataFrame(
        [{"open": 495, "high": 510, "low": 495, "close": 500.0, "volume": 600_000}
         for _ in range(30)], index=idx)
    result = r.scan({"LOW_ATR": low_atr, "HIGH_ATR": high_atr})
    assert result[0] == "HIGH_ATR"


# ─── Return type ───

def test_returns_list_of_strings():
    from adapters.scanner.scanner import ScannerRanker
    r = ScannerRanker(filters=[_always_pass()])
    candidates = {"RELIANCE": _make_df()}
    result = r.scan(candidates)
    assert isinstance(result, list)
    assert all(isinstance(s, str) for s in result)
