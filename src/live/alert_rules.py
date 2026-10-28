"""Configurable rules for filtering live prediction alerts."""

from __future__ import annotations

from typing import Any


class AlertRules:
    """Filter predictions before sending notifications."""

    def __init__(
        self,
        min_confidence: float = 0.70,
        allowed_directions: set[str] | None = None,
        allowed_horizons: set[int] | None = None,
        require_all_models_ready: bool = False,
    ) -> None:
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be between 0 and 1")

        self.min_confidence = min_confidence
        self.allowed_directions = allowed_directions or {"UP", "DOWN"}
        self.allowed_horizons = allowed_horizons or {1, 5, 15, 30, 60, 240}
        self.require_all_models_ready = require_all_models_ready

    def evaluate(self, prediction: dict[str, Any]) -> dict[str, Any]:
        """Return whether to alert and which horizon predictions qualified."""
        items = prediction.get("predictions", [])
        qualified = []

        for item in items:
            horizon = item.get("horizon_minutes")
            direction = item.get("direction")
            confidence = item.get("confidence")

            if horizon not in self.allowed_horizons:
                continue
            if item.get("status") != "OK":
                continue
            if direction not in self.allowed_directions:
                continue
            if not isinstance(confidence, (int, float)):
                continue
            if confidence < self.min_confidence:
                continue

            qualified.append(item)

        all_ready = all(
            item.get("status") == "OK"
            for item in items
            if item.get("horizon_minutes") in self.allowed_horizons
        )

        should_alert = bool(qualified)
        if self.require_all_models_ready and not all_ready:
            should_alert = False

        return {
            "symbol": prediction.get("symbol", "UNKNOWN"),
            "should_alert": should_alert,
            "reason": (
                "MATCHED_RULES" if should_alert
                else "MODELS_NOT_ALL_READY"
                if self.require_all_models_ready and not all_ready
                else "NO_PREDICTION_MATCHED"
            ),
            "qualified_predictions": qualified if should_alert else [],
            "min_confidence": self.min_confidence,
        }
