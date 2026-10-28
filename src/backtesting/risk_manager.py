"""Pre-trade risk checks for a manual-review day-trading system.

This module approves or rejects proposed trades; it does not submit orders.
All monetary values are in INR.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import time


@dataclass
class RiskConfig:
    max_risk_per_trade_inr: float = 1000.0
    max_daily_loss_inr: float = 3000.0
    max_open_positions: int = 3
    max_capital_per_trade_inr: float = 50000.0
    max_trades_per_day: int = 5


class RiskManager:
    def __init__(self, config: RiskConfig | None = None):
        self.config = config or RiskConfig()
        self.daily_realized_pnl = 0.0
        self.open_positions = 0
        self.trades_today = 0
        self.audit_log: list[dict] = []

        if self.config.max_risk_per_trade_inr <= 0:
            raise ValueError("max_risk_per_trade_inr must be positive")
        if self.config.max_daily_loss_inr <= 0:
            raise ValueError("max_daily_loss_inr must be positive")
        if self.config.max_open_positions < 1:
            raise ValueError("max_open_positions must be at least 1")
        if self.config.max_capital_per_trade_inr <= 0:
            raise ValueError("max_capital_per_trade_inr must be positive")
        if self.config.max_trades_per_day < 1:
            raise ValueError("max_trades_per_day must be at least 1")

    def evaluate(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        stop_price: float,
        available_capital_inr: float,
    ) -> dict:
        side = side.upper()
        quantity = float(quantity)
        entry_price = float(entry_price)
        stop_price = float(stop_price)
        available_capital_inr = float(available_capital_inr)

        reasons = []

        if side not in {"BUY", "SELL"}:
            reasons.append("Unsupported side; only BUY and SELL are allowed")
        if quantity <= 0 or entry_price <= 0 or stop_price <= 0:
            reasons.append("Quantity and prices must be positive")
        if available_capital_inr < 0:
            reasons.append("Available capital cannot be negative")

        if not reasons:
            if side == "BUY" and stop_price >= entry_price:
                reasons.append("BUY stop price must be below entry price")
            if side == "SELL" and stop_price <= entry_price:
                reasons.append("SELL stop price must be above entry price")

            estimated_risk = quantity * abs(entry_price - stop_price)
            required_capital = quantity * entry_price

            if estimated_risk > self.config.max_risk_per_trade_inr:
                reasons.append("Per-trade risk limit exceeded")
            if required_capital > self.config.max_capital_per_trade_inr:
                reasons.append("Per-trade capital limit exceeded")
            if required_capital > available_capital_inr:
                reasons.append("Insufficient available capital")
            if self.daily_realized_pnl <= -self.config.max_daily_loss_inr:
                reasons.append("Daily loss limit reached")
            if self.open_positions >= self.config.max_open_positions:
                reasons.append("Maximum open positions reached")
            if self.trades_today >= self.config.max_trades_per_day:
                reasons.append("Maximum trades per day reached")

        result = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "entry_price": entry_price,
            "stop_price": stop_price,
            "estimated_risk_inr": (
                quantity * abs(entry_price - stop_price)
                if quantity > 0 and entry_price > 0 and stop_price > 0
                else None
            ),
            "required_capital_inr": (
                quantity * entry_price
                if quantity > 0 and entry_price > 0
                else None
            ),
            "approved": not reasons,
            "rejection_reasons": reasons,
            "note": "Approval is a pre-trade check, not a guarantee of safety.",
        }

        self.audit_log.append(result)
        return result

    def update_daily_realized_pnl(self, realized_pnl_inr: float) -> None:
        self.daily_realized_pnl += float(realized_pnl_inr)

    def set_open_positions(self, count: int) -> None:
        if count < 0:
            raise ValueError("Open position count cannot be negative")
        self.open_positions = int(count)

    def record_trade_opened(self) -> None:
        self.trades_today += 1

    def reset_day(self) -> None:
        self.daily_realized_pnl = 0.0
        self.open_positions = 0
        self.trades_today = 0

    def export_json(self, output_dir: str | Path) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"risk_audit_{stamp}.json"

        output_path.write_text(json.dumps({
            "config": asdict(self.config),
            "daily_realized_pnl_inr": self.daily_realized_pnl,
            "open_positions": self.open_positions,
            "trades_today": self.trades_today,
            "decisions": self.audit_log,
            "warning": (
                "Prototype only. Daily resets, order fills, stop execution, "
                "and broker positions are not automatically synchronized."
            ),
        }, indent=2))
        return output_path
