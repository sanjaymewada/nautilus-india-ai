"""Strategy comparison scorecard based on historical trade outcomes."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any


class StrategyScorecard:
    """Aggregate trade records by strategy for research comparisons."""

    def __init__(self) -> None:
        self.trades: list[dict[str, Any]] = []

    def add_trade(self, trade: dict[str, Any]) -> None:
        required = ("strategy", "gross_pnl")
        missing = [key for key in required if key not in trade]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        record = dict(trade)
        pnl = record.get("net_pnl", record["gross_pnl"])
        record["_scorecard_pnl"] = float(pnl)
        self.trades.append(record)

    def build(self) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for trade in self.trades:
            grouped[str(trade["strategy"])].append(trade)

        results: list[dict[str, Any]] = []

        for strategy, trades in grouped.items():
            pnls = [trade["_scorecard_pnl"] for trade in trades]
            wins = [pnl for pnl in pnls if pnl > 0]
            losses = [pnl for pnl in pnls if pnl < 0]
            gross_profit = sum(wins)
            gross_loss = abs(sum(losses))
            equity = 0.0
            peak = 0.0
            max_drawdown = 0.0

            for pnl in pnls:
                equity += pnl
                peak = max(peak, equity)
                max_drawdown = max(max_drawdown, peak - equity)

            results.append(
                {
                    "strategy": strategy,
                    "trade_count": len(pnls),
                    "wins": len(wins),
                    "losses": len(losses),
                    "breakeven": sum(pnl == 0 for pnl in pnls),
                    "win_rate_pct": round(len(wins) / len(pnls) * 100, 2),
                    "net_pnl": round(sum(pnls), 2),
                    "average_pnl": round(sum(pnls) / len(pnls), 2),
                    "profit_factor": (
                        round(gross_profit / gross_loss, 4)
                        if gross_loss > 0
                        else None
                    ),
                    "max_drawdown_from_trade_sequence": round(max_drawdown, 2),
                }
            )

        return sorted(results, key=lambda item: item["net_pnl"], reverse=True)

    def export_json(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(self.build(), indent=2, allow_nan=False),
            encoding="utf-8",
        )
        return output_path
