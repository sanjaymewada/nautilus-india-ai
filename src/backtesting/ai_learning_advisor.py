"""Rule-based research advisor for historical trading results.

This module generates review suggestions. It does not predict future returns,
train an ML/RL model, or authorize live trades.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class LearningAdvisor:
    """Generate research suggestions from metrics and mistake patterns."""

    def generate(
        self,
        metrics: dict[str, Any],
        mistake_report: dict[str, Any] | None = None,
        scorecard: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        suggestions: list[dict[str, str]] = []

        trade_count = int(metrics.get("trade_count", 0) or 0)
        win_rate = metrics.get("win_rate_pct", metrics.get("win_rate"))
        profit_factor = metrics.get("profit_factor")
        expectancy = metrics.get("expectancy")

        if trade_count < 30:
            suggestions.append({
                "priority": "HIGH",
                "area": "sample_size",
                "suggestion": (
                    f"Only {trade_count} trades are represented. Gather a larger "
                    "out-of-sample sample before drawing conclusions."
                ),
            })

        if win_rate is not None:
            try:
                if float(win_rate) < 40:
                    suggestions.append({
                        "priority": "MEDIUM",
                        "area": "win_rate",
                        "suggestion": (
                            "Review entry filters, losing setups, and whether "
                            "the strategy performs differently by market regime."
                        ),
                    })
            except (TypeError, ValueError):
                pass

        if profit_factor is not None:
            try:
                if float(profit_factor) < 1:
                    suggestions.append({
                        "priority": "HIGH",
                        "area": "profitability",
                        "suggestion": (
                            "Historical gross profits do not cover historical "
                            "losses under the supplied metric. Inspect trade "
                            "quality, costs, and execution assumptions."
                        ),
                    })
            except (TypeError, ValueError):
                pass

        if expectancy is not None:
            try:
                if float(expectancy) <= 0:
                    suggestions.append({
                        "priority": "HIGH",
                        "area": "expectancy",
                        "suggestion": (
                            "Reported expectancy is non-positive. Review the "
                            "trade sample and validate the metric definition."
                        ),
                    })
            except (TypeError, ValueError):
                pass

        patterns = (mistake_report or {}).get("patterns", [])
        for pattern in patterns[:5]:
            label = pattern.get("mistake_label", "unspecified")
            count = int(pattern.get("occurrences", 0) or 0)
            if count >= 2:
                suggestions.append({
                    "priority": "MEDIUM",
                    "area": "repeated_mistake",
                    "suggestion": (
                        f"'{label}' appears {count} times in reviewed trades. "
                        "Inspect those trades and define a testable prevention rule."
                    ),
                })

        if scorecard:
            ranked = sorted(
                scorecard,
                key=lambda item: float(item.get("net_pnl", 0) or 0),
                reverse=True,
            )
            suggestions.append({
                "priority": "LOW",
                "area": "strategy_comparison",
                "suggestion": (
                    f"Highest reported net P&L in the supplied scorecard: "
                    f"{ranked[0].get('strategy', 'unknown')}. Compare sample size, "
                    "cost assumptions, and out-of-sample results before ranking "
                    "strategies as suitable."
                ),
            })

        if not suggestions:
            suggestions.append({
                "priority": "LOW",
                "area": "data_quality",
                "suggestion": (
                    "Insufficient metric or review information for targeted "
                    "suggestions. Add reviewed trades and complete metrics."
                ),
            })

        return {
            "advisor_type": "rule_based",
            "suggestions": suggestions,
            "limitations": [
                "Suggestions depend on the supplied data and metric field names.",
                "Historical patterns do not guarantee future performance.",
                "This advisor does not place orders or modify strategy parameters.",
            ],
        }

    @staticmethod
    def export_json(
        report: dict[str, Any],
        path: str | Path = "data/research/learning_advice.json",
    ) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        return output_path
