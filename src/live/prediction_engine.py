"""Live prediction engine for six independent forecast horizons."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol

from src.live.model_manager import HORIZONS_MINUTES


class Predictor(Protocol):
    def predict_proba(self, features: dict[str, Any]) -> Any:
        """Return probabilities for the model's classes."""
        ...


class LivePredictionEngine:
    """Predict separately for 1m, 5m, 15m, 30m, 1h and 4h."""

    def __init__(
        self,
        predictors: dict[int, Predictor] | None = None,
        min_confidence: float = 0.60,
        adapter: Any | None = None,
    ) -> None:
        if not 0 <= min_confidence <= 1:
            raise ValueError("min_confidence must be between 0 and 1")

        self.predictors = predictors or {}
        self.min_confidence = min_confidence
        self.adapter = adapter

    def _features_for(
        self, features: dict[str, Any], horizon: int
    ) -> dict[str, Any] | None:
        if self.adapter is not None:
            return self.adapter.features_for_horizon(features, horizon)

        # Multi-timeframe feature format is required.
        horizon_features = features.get("horizons", {}).get(str(horizon))
        if not isinstance(horizon_features, dict):
            return None
        if not horizon_features.get("ready", False):
            return None

        return {
            "symbol": features.get("symbol", "UNKNOWN"),
            "timestamp": features.get("timestamp"),
            **horizon_features,
        }

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        predictions = []

        for horizon in HORIZONS_MINUTES:
            predictor = self.predictors.get(horizon)
            horizon_features = self._features_for(features, horizon)

            if horizon_features is None:
                predictions.append({
                    "horizon_minutes": horizon,
                    "status": "FEATURES_NOT_READY",
                    "direction": None,
                    "confidence": None,
                    "probabilities": None,
                })
                continue

            if predictor is None:
                predictions.append({
                    "horizon_minutes": horizon,
                    "status": "NO_MODEL",
                    "direction": None,
                    "confidence": None,
                    "probabilities": None,
                })
                continue

            try:
                raw = predictor.predict_proba(horizon_features)

                # Support sklearn estimators and simple custom predictors.
                if hasattr(raw, "tolist"):
                    raw = raw.tolist()

                if isinstance(raw, list):
                    if len(raw) == 1 and isinstance(raw[0], list):
                        raw = raw[0]
                    classes = list(getattr(predictor, "classes_", []))
                    if len(classes) != len(raw):
                        raise ValueError("Model classes_ do not match probabilities")
                    probabilities = {
                        str(label).upper(): float(value)
                        for label, value in zip(classes, raw)
                    }
                elif isinstance(raw, dict):
                    probabilities = {
                        str(label).upper(): float(value)
                        for label, value in raw.items()
                    }
                else:
                    raise ValueError("Unsupported predict_proba() output")

                if not probabilities or any(
                    value < 0 or value > 1
                    for value in probabilities.values()
                ):
                    raise ValueError("Invalid probability values")

                if abs(sum(probabilities.values()) - 1.0) > 0.02:
                    raise ValueError("Probabilities must sum to approximately 1")

                direction = max(probabilities, key=probabilities.get)
                if direction not in {"UP", "DOWN", "FLAT"}:
                    raise ValueError("Expected classes UP, DOWN and/or FLAT")

                confidence = probabilities[direction]
                if confidence < self.min_confidence:
                    direction = "NO_TRADE"

                predictions.append({
                    "horizon_minutes": horizon,
                    "status": "OK",
                    "direction": direction,
                    "confidence": round(confidence, 4),
                    "probabilities": probabilities,
                    "model_version": getattr(
                        predictor, "model_version", None
                    ),
                })

            except Exception as exc:
                predictions.append({
                    "horizon_minutes": horizon,
                    "status": "PREDICTION_ERROR",
                    "direction": None,
                    "confidence": None,
                    "probabilities": None,
                    "error": str(exc),
                })

        return {
            "symbol": str(features.get("symbol", "UNKNOWN")),
            "feature_timestamp": features.get("timestamp"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "engine": "live_multi_horizon",
            "predictions": predictions,
        }
