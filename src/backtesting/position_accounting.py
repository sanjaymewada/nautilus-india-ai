"""Position and P&L accounting helpers for backtest fill events.

Long-only accounting. Costs are excluded unless added by a later module.
This module does not submit orders or connect to a broker.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import time


@dataclass
class PositionSnapshot:
    symbol: str
    quantity: float = 0.0
    average_entry_price: float = 0.0
    realized_pnl: float = 0.0
    last_mark_price: float | None = None
    unrealized_pnl: float = 0.0


class PositionAccounting:
    def __init__(self, symbol: str):
        self.position = PositionSnapshot(symbol=symbol)
        self.fill_ledger: list[dict] = []

    def record_fill(
        self,
        side: str,
        quantity: float,
        price: float,
        timestamp_ns: int | None = None,
    ) -> None:
        side = side.upper()
        quantity = float(quantity)
        price = float(price)

        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        if quantity <= 0 or price <= 0:
            raise ValueError("quantity and price must be positive")

        p = self.position

        if side == "BUY":
            if p.quantity < 0:
                raise ValueError("Short positions are not supported")
            new_qty = p.quantity + quantity
            p.average_entry_price = (
                (p.quantity * p.average_entry_price + quantity * price) / new_qty
            )
            p.quantity = new_qty
        else:
            if quantity > p.quantity:
                raise ValueError("SELL quantity exceeds current long position")

            p.realized_pnl += quantity * (price - p.average_entry_price)
            p.quantity -= quantity

            if p.quantity == 0:
                p.average_entry_price = 0.0

        self.fill_ledger.append({
            "symbol": p.symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "timestamp_ns": timestamp_ns,
            "realized_pnl_after_fill": p.realized_pnl,
            "position_quantity_after_fill": p.quantity,
            "average_entry_price_after_fill": p.average_entry_price,
        })

        if p.last_mark_price is not None:
            self.mark_to_market(p.last_mark_price)

    def mark_to_market(self, mark_price: float) -> dict:
        mark_price = float(mark_price)
        if mark_price <= 0:
            raise ValueError("mark_price must be positive")

        p = self.position
        p.last_mark_price = mark_price
        p.unrealized_pnl = (
            p.quantity * (mark_price - p.average_entry_price)
            if p.quantity > 0
            else 0.0
        )

        return asdict(p)

    def summary(self) -> dict:
        p = self.position
        return {
            "symbol": p.symbol,
            "open_quantity": p.quantity,
            "average_entry_price": p.average_entry_price,
            "realized_pnl": p.realized_pnl,
            "last_mark_price": p.last_mark_price,
            "unrealized_pnl": p.unrealized_pnl,
            "total_pnl_before_costs": p.realized_pnl + p.unrealized_pnl,
            "fills_recorded": len(self.fill_ledger),
            "costs_included": False,
        }

    def export_json(self, output_dir: str | Path) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        stamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"position_accounting_{stamp}.json"

        payload = {
            "summary": self.summary(),
            "fills": self.fill_ledger,
            "warning": (
                "Accounting helper only; not yet integrated with "
                "NautilusTrader portfolio reports or brokerage costs."
            ),
        }
        output_path.write_text(json.dumps(payload, indent=2))
        return output_path
