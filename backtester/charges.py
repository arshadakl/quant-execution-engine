"""TradeCharges — Indian intraday equity transaction cost model.

Rates (NSE intraday equity, as of 2026):
  Brokerage       : min(₹20, 0.03%) per side
  STT             : 0.025% on sell turnover only
  Exchange charges: 0.00325% on total turnover (NSE)
  SEBI charges    : ₹10 per crore = 0.000010%
  GST             : 18% on (brokerage + exchange + SEBI)
  Stamp duty      : 0.015% on buy turnover only
"""
from dataclasses import dataclass

_BROKERAGE_PCT = 0.0003       # 0.03%
_BROKERAGE_CAP = 20.0         # ₹20 per order
_STT_PCT = 0.00025            # 0.025% sell side
_EXCHANGE_PCT = 0.0000325     # 0.00325%
_SEBI_PCT = 0.000001          # ₹10 per crore
_GST_PCT = 0.18
_STAMP_PCT = 0.00015          # 0.015% buy side


@dataclass(frozen=True)
class TradeCharges:
    """Breakdown of transaction costs for one round-trip trade."""

    brokerage: float
    stt: float
    exchange_charges: float
    gst: float
    sebi_charges: float
    stamp_duty: float

    @property
    def total(self) -> float:
        return (self.brokerage + self.stt + self.exchange_charges
                + self.gst + self.sebi_charges + self.stamp_duty)


def calculate_charges(
    entry_price: float,
    exit_price: float,
    qty: int,
) -> TradeCharges:
    """Compute full intraday charge breakdown for one round-trip trade."""
    buy_turnover = entry_price * qty
    sell_turnover = exit_price * qty
    total_turnover = buy_turnover + sell_turnover

    brokerage_buy = min(_BROKERAGE_CAP, buy_turnover * _BROKERAGE_PCT)
    brokerage_sell = min(_BROKERAGE_CAP, sell_turnover * _BROKERAGE_PCT)
    brokerage = brokerage_buy + brokerage_sell

    stt = sell_turnover * _STT_PCT
    exchange_charges = total_turnover * _EXCHANGE_PCT
    sebi_charges = total_turnover * _SEBI_PCT
    gst = (brokerage + exchange_charges + sebi_charges) * _GST_PCT
    stamp_duty = buy_turnover * _STAMP_PCT

    return TradeCharges(
        brokerage=round(brokerage, 4),
        stt=round(stt, 4),
        exchange_charges=round(exchange_charges, 4),
        gst=round(gst, 4),
        sebi_charges=round(sebi_charges, 4),
        stamp_duty=round(stamp_duty, 4),
    )
