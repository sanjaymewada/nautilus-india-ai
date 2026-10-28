"""Structured trade-outcome dataset for future AI/RL experiments.

This module stores historical examples. It does not train a model,
generate live signals, or place orders.
"""

from pathlib import Path
import json
import time


REQUIRED_FIELDS = {
    "symbol",
    "strategy",
    "entry_timestamp",
    "exit_timestamp",
    "side",
    "entry_price",
    "exit_price",
    "quantity",
    "gross_pnl",
}


class LearningDataset:
    def __init__(self):
        self.records: list[dict] = []

    def add_trade(self, trade: dict) -> int:
        missing = sorted(REQUIRED_FIELDS - set(trade))
        if missing:
            raise ValueError(f"Missing required trade fields: {missing}")

        record = dict(trade)

        if record["side"] not in {"LONG", "SHORT"}:
            raise ValueError("side must be LONG or SHORT")

        for field in ("entry_price", "exit_price", "quantity", "gross_pnl"):
            record[field] = float(record[field])

        if record["entry_price"] <= 0 or record["exit_price"] <= 0:
            raise ValueError("Entry and exit prices must be positive")
        if record["quantity"] <= 0:
            raise ValueError("Quantity must be positive")

        record.setdefault("net_pnl", None)
        record.setdefault("market_regime", "UNKNOWN")
        record.setdefault("setup_label", "UNLABELLED")
        record.setdefault("mistake_labels", [])
        record.setdefault("lessons", [])
        record.setdefault("data_quality", "UNREVIEWED")
        record.setdefault("reviewed_by_human", False)

        if not isinstance(record["mistake_labels"], list):
            raise ValueError("mistake_labels must be a list")
        if not isinstance(record["lessons"], list):
            raise ValueError("lessons must be a list")

        record["outcome"] = (
            "WIN" if record["gross_pnl"] > 0
            else "LOSS" if record["gross_pnl"] < 0
            else "BREAKEVEN"
        )

        self.records.append(record)
        return len(self.records) - 1

    def label_trade(
        self,
        record_id: int,
        mistake_labels: list[str] | None = None,
        lessons: list[str] | None = None,
        market_regime: str | None = None,
        setup_label: str | None = None,
        reviewed_by_human: bool = False,
    ) -> None:
        record = self.records[record_id]

        if mistake_labels is not None:
            record["mistake_labels"] = list(mistake_labels)
        if lessons is not None:
            record["lessons"] = list(lessons)
        if market_regime is not None:
            record["market_regime"] = market_regime
        if setup_label is not None:
            record["setup_label"] = setup_label

        record["reviewed_by_human"] = bool(reviewed_by_human)
        record["data_quality"] = (
            "HUMAN_REVIEWED" if reviewed_by_human else "UNREVIEWED"
        )

    def summary(self) -> dict:
        wins = sum(r["outcome"] == "WIN" for r in self.records)
        losses = sum(r["outcome"] == "LOSS" for r in self.records)
        breakeven = sum(r["outcome"] == "BREAKEVEN" for r in self.records)

        return {
            "trade_records": len(self.records),
            "wins": wins,
            "losses": losses,
            "breakeven": breakeven,
            "human_reviewed": sum(
                bool(r["reviewed_by_human"]) for r in self.records
            ),
            "note": (
                "Labels are observations, not proof of causation. "
                "Use chronological train/test splits to avoid data leakage."
            ),
        }

    def export_json(self, output_dir: str | Path) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        stamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"learning_dataset_{stamp}.json"

        payload = {
            "summary": self.summary(),
            "records": self.records,
        }
        output_path.write_text(json.dumps(payload, indent=2, allow_nan=False))
        return output_path
