"""Analyze recurring mistakes in reviewed historical trades."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


class MistakePatternAnalyzer:
    """Summarize repeated mistake labels and their associated trade outcomes."""

    def analyze(
        self,
        reviews: list[dict[str, Any]],
        trades: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        label_counts: Counter[str] = Counter()
        label_pnls: dict[str, list[float]] = defaultdict(list)
        reviewed_trade_ids: set[str] = set()

        for review in reviews:
            trade_id = review.get("trade_id")
            if trade_id:
                reviewed_trade_ids.add(str(trade_id))

        trade_lookup = {
            str(trade["trade_id"]): trade
            for trade in (trades or [])
            if trade.get("trade_id") is not None
        }

        for review in reviews:
            labels = review.get("mistake_labels") or []
            trade = trade_lookup.get(str(review.get("trade_id")))
            pnl_value = None

            if trade:
                pnl_value = trade.get("net_pnl", trade.get("gross_pnl"))

            for label in labels:
                label = str(label).strip()
                if not label:
                    continue

                label_counts[label] += 1

                if pnl_value is not None:
                    label_pnls[label].append(float(pnl_value))

        patterns = []
        for label, count in label_counts.most_common():
            pnls = label_pnls.get(label, [])
            patterns.append(
                {
                    "mistake_label": label,
                    "occurrences": count,
                    "trades_with_pnl": len(pnls),
                    "average_associated_pnl": (
                        round(sum(pnls) / len(pnls), 2) if pnls else None
                    ),
                    "total_associated_pnl": (
                        round(sum(pnls), 2) if pnls else None
                    ),
                }
            )

        return {
            "reviewed_trade_count": len(reviewed_trade_ids),
            "review_count": len(reviews),
            "unique_mistake_labels": len(label_counts),
            "patterns": patterns,
            "interpretation_note": (
                "Associated P&L is descriptive, not proof that a mistake label "
                "caused the outcome. Human review and more samples are needed."
            ),
        }

    def export_json(
        self,
        report: dict[str, Any],
        path: str | Path = "data/research/mistake_patterns.json",
    ) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        return output_path
