"""Tests for Position Sizer."""
import pytest
from core.use_cases.position_sizer import PositionSizer


# ─── Instantiation ───

def test_instantiates_with_defaults():
    ps = PositionSizer()
    assert ps.risk_pct == 0.01
    assert ps.max_qty == 500
    assert ps.max_position_size_pct == 0.15


def test_instantiates_with_custom_params():
    ps = PositionSizer(risk_pct=0.02, max_qty=200, max_position_size_pct=0.20)
    assert ps.risk_pct == 0.02
    assert ps.max_qty == 200
    assert ps.max_position_size_pct == 0.20


# ─── Basic calculation ───

def test_basic_quantity():
    ps = PositionSizer(risk_pct=0.01, max_qty=500)
    # capital=100_000, risk_qty=100, capital_cap: 15% of 100k / 500 = 30 → cap wins
    qty = ps.calculate(capital=100_000.0, entry=500.0, stop_loss=490.0)
    assert qty == 30


def test_qty_rounds_down_to_whole_shares():
    ps = PositionSizer(risk_pct=0.01, max_qty=500)
    # capital=100_000, risk_qty=333, capital_cap: 30 → cap wins
    qty = ps.calculate(capital=100_000.0, entry=500.0, stop_loss=497.0)
    assert qty == 30


# ─── Max qty cap ───

def test_caps_at_max_qty():
    ps = PositionSizer(risk_pct=0.05, max_qty=10)
    # would be capital*5% / tiny_sl = huge → capped at 10
    qty = ps.calculate(capital=100_000.0, entry=500.0, stop_loss=499.9)
    assert qty == 10


def test_does_not_cap_at_max_qty_when_below_it():
    # Explicitly use pct=1.0 so only max_qty acts as ceiling
    ps = PositionSizer(risk_pct=0.01, max_qty=500, max_position_size_pct=1.0)
    qty = ps.calculate(capital=100_000.0, entry=500.0, stop_loss=490.0)
    assert qty == 100  # risk_qty=100, cap_qty=200, max_qty=500 → 100
    assert qty <= 500


# ─── Zero / invalid SL distance ───

def test_returns_zero_when_sl_equals_entry():
    ps = PositionSizer()
    qty = ps.calculate(capital=100_000.0, entry=500.0, stop_loss=500.0)
    assert qty == 0


def test_returns_zero_when_sl_above_entry_long():
    # SL above entry for a long is invalid
    ps = PositionSizer()
    qty = ps.calculate(capital=100_000.0, entry=500.0, stop_loss=510.0)
    assert qty == 0


def test_returns_zero_on_zero_capital():
    ps = PositionSizer()
    qty = ps.calculate(capital=0.0, entry=500.0, stop_loss=490.0)
    assert qty == 0


# ─── Different capital sizes ───

def test_scales_with_capital():
    ps = PositionSizer(risk_pct=0.01, max_qty=10_000)
    qty_small = ps.calculate(capital=50_000.0, entry=500.0, stop_loss=490.0)
    qty_large = ps.calculate(capital=200_000.0, entry=500.0, stop_loss=490.0)
    assert qty_large == qty_small * 4


def test_small_capital_gives_small_qty():
    ps = PositionSizer(risk_pct=0.01, max_qty=500)
    # capital=1_000: 15% = ₹150, at ₹500/share → floor(150/500) = 0 shares
    qty = ps.calculate(capital=1_000.0, entry=500.0, stop_loss=490.0)
    assert qty == 0


# ─── Return type ───

def test_returns_integer():
    ps = PositionSizer()
    qty = ps.calculate(capital=100_000.0, entry=500.0, stop_loss=490.0)
    assert isinstance(qty, int)


# ─── Capital percentage cap ───

def test_capital_cap_limits_qty_when_risk_qty_is_too_large():
    # 15% of ₹100,000 = ₹15,000. At ₹500/share → cap = 30 shares.
    # Risk formula: ₹1,000 risk / ₹1 SL dist = 1,000 shares (way too large).
    # Capital cap should win → 30.
    ps = PositionSizer(risk_pct=0.01, max_qty=500, max_position_size_pct=0.15)
    qty = ps.calculate(capital=100_000.0, entry=500.0, stop_loss=499.0)
    assert qty == 30


def test_risk_qty_wins_when_smaller_than_capital_cap():
    # 15% cap → 30 shares. Risk formula: ₹100 / ₹10 = 10 shares.
    # Risk formula is smaller → 10.
    ps = PositionSizer(risk_pct=0.001, max_qty=500, max_position_size_pct=0.15)
    qty = ps.calculate(capital=100_000.0, entry=500.0, stop_loss=490.0)
    assert qty == 10
