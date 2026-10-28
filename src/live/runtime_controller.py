"""Coordinate live model inference and runtime status."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.live.model_service import LiveModelService


class LiveRuntimeController:
    def __init__(
        self,
        model_service: LiveModelService | None = None,
    ) -> None:
        self.model_service = model_service or LiveModelService.create()
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.running = False
        self.last_prediction: dict[str, Any] | None = None
        self.last_error: str | None = None

    def start(self) -> dict[str, Any]:
        """Mark the controller ready for feed integration."""
        self.running = True
        return self.status()

    def stop(self) -> dict[str, Any]:
        self.running = False
        return self.status()

    def on_features(
        self,
        features: dict[str, Any],
    ) -> dict[str, Any]:
        """Process features supplied by an external live pipeline."""
        if not self.running:
            return {
                "status": "RUNTIME_STOPPED",
                "message": "Call start() before sending features.",
            }

        try:
            prediction = self.model_service.predict(features)
            self.last_prediction = prediction
            self.last_error = None
            return prediction
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            return {
                "status": "PREDICTION_ERROR",
                "error": self.last_error,
            }

    def status(self) -> dict[str, Any]:
        model_status = self.model_service.status()

        return {
            "runtime_status": "READY_FOR_FEED" if self.running else "STOPPED",
            "started_at": self.started_at,
            "market_feed_connected": False,
            "last_prediction_available": self.last_prediction is not None,
            "last_error": self.last_error,
            "models": model_status,
        }
