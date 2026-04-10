"""Tests for Position Sizer."""
import pytest
from core.use_cases.position_sizer import PositionSizer


# ─── Instantiation ───

def test_instantiates_with_defaults():
    ps = PositionSizer()
    assert ps.risk_pct == 0.01
    assert ps.max_qty == 500


def test_instantiates_with_custom_params():
    ps = PositionSizer(risk_pct=0.02, max_qty=200)
    assert ps.risk_pct == 0.02
    assert ps.max_qty == 200


# ─── Basic calculation ───

def test_basic_quantity():
    ps = PositionSizer(risk_pct=0.01, max_qty=500)
    # capital=100_000, risk=1_000, sl_distance=10 → qty=100
    qty = ps.calculate(capital=100_000.0, entry=500.0, stop_loss=490.0)
    assert qty == 100


def test_qty_rounds_down_to_whole_shares():
    ps = PositionSizer(risk_pct=0.01, max_qty=500)
    # capital=100_000, risk=1_000, sl_distance=3 → qty=333.33 → 333
    qty = ps.calculate(capital=100_000.0, entry=500.0, stop_loss=497.0)
    assert qty == 333


# ─── Max qty cap ───

def test_caps_at_max_qty():
    ps = PositionSizer(risk_pct=0.05, max_qty=10)
    # would be capital*5% / tiny_sl = huge → capped at 10
    qty = ps.calculate(capital=100_000.0, entry=500.0, stop_loss=499.9)
    assert qty == 10


def test_does_not_cap_when_below_max():
    ps = PositionSizer(risk_pct=0.01, max_qty=500)
    qty = ps.calculate(capital=100_000.0, entry=500.0, stop_loss=490.0)
    assert qty == 100
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
    qty = ps.calculate(capital=1_000.0, entry=500.0, stop_loss=490.0)
    assert qty == 1  # risk=10, sl_dist=10 → 1 share


# ─── Return type ───

def test_returns_integer():
    ps = PositionSizer()
    qty = ps.calculate(capital=100_000.0, entry=500.0, stop_loss=490.0)
    assert isinstance(qty, int)
