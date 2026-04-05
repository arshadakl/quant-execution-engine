"""Tests for DataCacher — Parquet cache-first OHLCV storage."""
import pytest
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path


@pytest.fixture
def tmp_cacher(tmp_path):
    from adapters.data.data_cacher import DataCacher
    return DataCacher(cache_dir=tmp_path)


@pytest.fixture
def sample_df():
    idx = pd.date_range("2026-01-02 09:15", periods=5, freq="1min")
    return pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0, 103.0, 104.0],
            "high": [101.0, 102.0, 103.0, 104.0, 105.0],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0],
            "close": [100.5, 101.5, 102.5, 103.5, 104.5],
            "volume": [1000, 1100, 1200, 1300, 1400],
        },
        index=idx,
    )


# ─── Path and existence ───

def test_cache_path_matches_expected(tmp_cacher, tmp_path):
    path = tmp_cacher.cache_path("RELIANCE", "1m")
    assert path == tmp_path / "RELIANCE_1m.parquet"


def test_exists_false_when_no_file(tmp_cacher):
    assert tmp_cacher.exists("RELIANCE", "1m") is False


def test_exists_true_after_save(tmp_cacher, sample_df):
    tmp_cacher.save("RELIANCE", "1m", sample_df)
    assert tmp_cacher.exists("RELIANCE", "1m") is True


# ─── Symbol / interval validation ───

def test_cache_path_rejects_path_traversal(tmp_cacher):
    with pytest.raises(ValueError, match="Invalid symbol"):
        tmp_cacher.cache_path("../evil", "1m")


def test_cache_path_rejects_slash_in_symbol(tmp_cacher):
    with pytest.raises(ValueError, match="Invalid symbol"):
        tmp_cacher.cache_path("NIFTY/BANK", "1m")


def test_cache_path_rejects_invalid_interval(tmp_cacher):
    with pytest.raises(ValueError, match="Invalid interval"):
        tmp_cacher.cache_path("RELIANCE", "INVALID!")


def test_save_rejects_missing_ohlcv_columns(tmp_cacher):
    bad_df = pd.DataFrame({"close": [100.0]})
    with pytest.raises(ValueError, match="missing required columns"):
        tmp_cacher.save("RELIANCE", "1m", bad_df)


# ─── Save and load round-trip ───

def test_save_creates_parquet_file(tmp_cacher, sample_df):
    tmp_cacher.save("RELIANCE", "1m", sample_df)
    assert tmp_cacher.cache_path("RELIANCE", "1m").exists()


def test_load_returns_empty_df_when_no_cache(tmp_cacher):
    df = tmp_cacher.load("RELIANCE", "1m")
    assert isinstance(df, pd.DataFrame)
    assert df.empty


def test_load_returns_saved_data(tmp_cacher, sample_df):
    tmp_cacher.save("RELIANCE", "1m", sample_df)
    loaded = tmp_cacher.load("RELIANCE", "1m")
    assert len(loaded) == len(sample_df)
    assert list(loaded.columns) == ["open", "high", "low", "close", "volume"]


def test_index_is_datetime_after_load(tmp_cacher, sample_df):
    tmp_cacher.save("RELIANCE", "1m", sample_df)
    loaded = tmp_cacher.load("RELIANCE", "1m")
    assert pd.api.types.is_datetime64_any_dtype(loaded.index)


# ─── Date range filtering ───

def test_load_with_from_dt_filters_start(tmp_cacher, sample_df):
    tmp_cacher.save("RELIANCE", "1m", sample_df)
    from_dt = datetime(2026, 1, 2, 9, 17)
    loaded = tmp_cacher.load("RELIANCE", "1m", from_dt=from_dt)
    assert all(loaded.index >= from_dt)


def test_load_with_to_dt_filters_end(tmp_cacher, sample_df):
    tmp_cacher.save("RELIANCE", "1m", sample_df)
    to_dt = datetime(2026, 1, 2, 9, 17)
    loaded = tmp_cacher.load("RELIANCE", "1m", to_dt=to_dt)
    assert all(loaded.index <= to_dt)


def test_load_with_tz_aware_filter_normalizes_correctly(tmp_cacher, sample_df):
    tmp_cacher.save("RELIANCE", "1m", sample_df)
    from_dt = datetime(2026, 1, 2, 9, 17, tzinfo=timezone.utc)
    # Should not raise — tz is stripped before comparison
    loaded = tmp_cacher.load("RELIANCE", "1m", from_dt=from_dt)
    assert len(loaded) <= len(sample_df)


# ─── Merge and deduplication ───

def test_save_merges_with_existing_data(tmp_cacher, sample_df):
    tmp_cacher.save("RELIANCE", "1m", sample_df)

    # New data with no overlap — starts at 09:20 (after original ends at 09:19)
    new_idx = pd.date_range("2026-01-02 09:20", periods=3, freq="1min")
    new_df = pd.DataFrame(
        {"open": [105.0, 106.0, 107.0], "high": [106.0, 107.0, 108.0],
         "low": [104.0, 105.0, 106.0], "close": [105.5, 106.5, 107.5],
         "volume": [1500, 1600, 1700]},
        index=new_idx,
    )
    tmp_cacher.save("RELIANCE", "1m", new_df)
    loaded = tmp_cacher.load("RELIANCE", "1m")
    assert len(loaded) == 8  # 5 original + 3 new (no overlap)


def test_save_deduplicates_overlapping_rows(tmp_cacher, sample_df):
    tmp_cacher.save("RELIANCE", "1m", sample_df)
    tmp_cacher.save("RELIANCE", "1m", sample_df)
    loaded = tmp_cacher.load("RELIANCE", "1m")
    assert len(loaded) == len(sample_df)


def test_data_sorted_ascending_after_merge(tmp_cacher, sample_df):
    tmp_cacher.save("RELIANCE", "1m", sample_df)

    old_idx = pd.date_range("2026-01-02 09:10", periods=2, freq="1min")
    old_df = pd.DataFrame(
        {"open": [98.0, 99.0], "high": [99.0, 100.0],
         "low": [97.0, 98.0], "close": [98.5, 99.5], "volume": [800, 900]},
        index=old_idx,
    )
    tmp_cacher.save("RELIANCE", "1m", old_df)
    loaded = tmp_cacher.load("RELIANCE", "1m")
    assert loaded.index.is_monotonic_increasing


def test_save_strips_tz_aware_index(tmp_cacher, sample_df):
    aware_df = sample_df.copy()
    aware_df.index = aware_df.index.tz_localize("Asia/Kolkata")
    tmp_cacher.save("RELIANCE", "1m", aware_df)
    loaded = tmp_cacher.load("RELIANCE", "1m")
    assert loaded.index.tz is None


def test_save_overwrites_corrupt_cache_with_new_data(tmp_cacher, sample_df, tmp_path):
    path = tmp_path / "RELIANCE_1m.parquet"
    path.write_bytes(b"not a valid parquet file")  # corrupt the cache

    # Save should recover by overwriting instead of crashing
    tmp_cacher.save("RELIANCE", "1m", sample_df)
    loaded = tmp_cacher.load("RELIANCE", "1m")
    assert len(loaded) == len(sample_df)


# ─── Clear ───

def test_clear_removes_cache_file(tmp_cacher, sample_df):
    tmp_cacher.save("RELIANCE", "1m", sample_df)
    tmp_cacher.clear("RELIANCE", "1m")
    assert tmp_cacher.exists("RELIANCE", "1m") is False


def test_clear_nonexistent_does_not_raise(tmp_cacher):
    tmp_cacher.clear("RELIANCE", "1m")


# ─── Protocol conformance ───

def test_data_cacher_implements_i_data_cacher(tmp_cacher):
    from core.interfaces.i_data_cacher import IDataCacher
    assert isinstance(tmp_cacher, IDataCacher)
