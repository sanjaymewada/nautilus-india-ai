"""Configurable transaction-cost estimator for Indian equity backtests.

All rates are caller-supplied. No tax or brokerage rate is assumed.
This is an estimate helper, not a broker contract-note calculator.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import time


@dataclass
class CostRates:
    brokerage_rate: float = 0.0
    exchange_rate: float = 0.0
    stt_rate: float = 0.0
    gst_rate: float = 0.0
    stamp_duty_rate: float = 0.0
    slippage_bps: float = 0.0


class TransactionCostModel:
    def __init__(self, rates: CostRates | None = None):
        self.rates = rates or CostRates()
        self.ledger: list[dict] = []

        for name, value in asdict(self.rates).items():
            if value < 0:
                raise ValueError(f"{name} cannot be negative")

    def estimate(
        self,
        side: str,
        quantity: float,
        price: float,
        timestamp_ns: int | None = None,
    ) -> dict:
        side = side.upper()
        quantity = float(quantity)
        price = float(price)

        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        if quantity <= 0 or price <= 0:
            raise ValueError("quantity and price must be positive")

        turnover = quantity * price
        brokerage = turnover * self.rates.brokerage_rate
        exchange = turnover * self.rates.exchange_rate
        stt = turnover * self.rates.stt_rate if side == "SELL" else 0.0
        stamp_duty = (
            turnover * self.rates.stamp_duty_rate if side == "BUY" else 0.0
        )
        gst = (brokerage + exchange) * self.rates.gst_rate
        slippage = turnover * self.rates.slippage_bps / 10000.0

        result = {
            "side": side,
            "quantity": quantity,
            "price": price,
            "turnover": turnover,
            "brokerage": brokerage,
            "exchange_charges": exchange,
            "stt_estimate": stt,
            "gst_estimate": gst,
            "stamp_duty_estimate": stamp_duty,
            "slippage_estimate": slippage,
            "estimated_total_cost": (
                brokerage + exchange + stt + gst + stamp_duty + slippage
            ),
            "timestamp_ns": timestamp_ns,
            "warning": (
                "Illustrative estimate only; validate rates and applicable "
                "rules against the broker contract note and current regulations."
            ),
        }
        self.ledger.append(result)
        return result

    def total_cost(self) -> float:
        return sum(item["estimated_total_cost"] for item in self.ledger)

    def export_json(self, output_dir: str | Path) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        stamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"cost_model_{stamp}.json"
        payload = {
            "rates": asdict(self.rates),
            "fills_estimated": len(self.ledger),
            "estimated_total_cost": self.total_cost(),
            "ledger": self.ledger,
            "warning": (
                "Rates default to zero until configured; zero costs do not "
                "represent real trading costs."
            ),
        }
        output_path.write_text(json.dumps(payload, indent=2))
        return output_path
