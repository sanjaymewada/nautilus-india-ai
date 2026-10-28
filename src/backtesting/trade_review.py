"""Trade review journal for recording mistakes and lessons."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TradeReviewJournal:
    """Store human-reviewed trade outcomes for future analysis."""

    def __init__(self, output_path: str | Path = "data/research/trade_reviews.json"):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.reviews: list[dict[str, Any]] = []

        if self.output_path.exists():
            try:
                saved = json.loads(self.output_path.read_text(encoding="utf-8"))
                if isinstance(saved, list):
                    self.reviews = saved
            except (json.JSONDecodeError, OSError):
                # Keep the existing file untouched if it cannot be read.
                self.reviews = []

    def add_review(
        self,
        trade_id: str,
        symbol: str,
        strategy: str,
        outcome: str,
        mistake_labels: list[str] | None = None,
        lesson: str = "",
        review_notes: str = "",
        reviewer: str = "human",
    ) -> dict[str, Any]:
        """Append a review record and persist the journal."""
        if not trade_id.strip():
            raise ValueError("trade_id cannot be empty")
        if not symbol.strip():
            raise ValueError("symbol cannot be empty")

        record = {
            "trade_id": trade_id,
            "symbol": symbol,
            "strategy": strategy,
            "outcome": outcome,
            "mistake_labels": mistake_labels or [],
            "lesson": lesson,
            "review_notes": review_notes,
            "reviewer": reviewer,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }

        self.reviews.append(record)
        self._save()
        return record

    def _save(self) -> None:
        self.output_path.write_text(
            json.dumps(self.reviews, indent=2, allow_nan=False),
            encoding="utf-8",
        )

    def summary(self) -> dict[str, Any]:
        """Return simple counts for review progress."""
        mistake_counts: dict[str, int] = {}
        for review in self.reviews:
            for label in review.get("mistake_labels", []):
                mistake_counts[label] = mistake_counts.get(label, 0) + 1

        return {
            "total_reviews": len(self.reviews),
            "with_lessons": sum(bool(item.get("lesson")) for item in self.reviews),
            "mistake_counts": mistake_counts,
        }
