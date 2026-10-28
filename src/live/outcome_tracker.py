"""Track live prediction horizons and label them from later market prices."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

HORIZONS_MINUTES = (1, 5, 15, 30, 60, 240)


class OutcomeTracker:
    """Match prediction snapshots with later prices; never invent missing prices."""

    def __init__(self, flat_threshold_pct: float = 0.0005) -> None:
        if flat_threshold_pct < 0:
            raise ValueError("flat_threshold_pct must be non-negative")

        self.flat_threshold_pct = flat_threshold_pct
        self._pending: list[dict[str, Any]] = []

    def register_prediction(
        self,
        prediction: dict[str, Any],
        reference_price: float,
        timestamp: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Register horizon predictions with their reference price and time."""
        if reference_price <= 0:
            raise ValueError("reference_price must be positive")

        timestamp = timestamp or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")

        registered = []
        for item in prediction.get("predictions", []):
            horizon = int(item.get("horizon_minutes", 0))
            if horizon not in HORIZONS_MINUTES:
                continue

            record = {
                "symbol": prediction.get("symbol"),
                "horizon_minutes": horizon,
                "prediction_generated_at": timestamp.isoformat(),
                "target_time": (timestamp + timedelta(minutes=horizon)).isoformat(),
                "reference_price": float(reference_price),
                "predicted_direction": item.get("direction"),
                "prediction_status": item.get("status"),
                "confidence": item.get("confidence"),
                "resolved": False,
            }
            self._pending.append(record)
            registered.append(record.copy())

        return registered

    def update_price(
        self,
        symbol: str,
        price: float,
        timestamp: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Resolve due predictions using the first supplied price at/after target."""
        if price <= 0:
            raise ValueError("price must be positive")

        timestamp = timestamp or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")

        outcomes = []
        remaining = []

        for record in self._pending:
            if record["symbol"] != symbol:
                remaining.append(record)
                continue

            target_time = datetime.fromisoformat(record["target_time"])
            if timestamp < target_time:
                remaining.append(record)
                continue

            reference = record["reference_price"]
            actual_return = price / reference - 1.0

            if actual_return > self.flat_threshold_pct:
                actual_direction = "UP"
            elif actual_return < -self.flat_threshold_pct:
                actual_direction = "DOWN"
            else:
                actual_direction = "FLAT"

            predicted = record["predicted_direction"]
            evaluable = (
                record["prediction_status"] == "OK"
                and predicted in {"UP", "DOWN", "FLAT", "NO_TRADE"}
            )

            outcome = {
                **record,
                "resolved": True,
                "resolved_at": timestamp.isoformat(),
                "actual_price": float(price),
                "actual_return_pct": round(actual_return * 100, 6),
                "actual_direction": actual_direction,
                "direction_correct": (
                    predicted == actual_direction if evaluable else None
                ),
            }
            outcomes.append(outcome)

        self._pending = remaining
        return outcomes

    def pending_count(self) -> int:
        return len(self._pending)
