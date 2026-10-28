"""Manage versioned prediction models for six live forecast horizons."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

HORIZONS_MINUTES = (1, 5, 15, 30, 60, 240)


class ModelManager:
    """Load and expose separately trained models for each forecast horizon."""

    def __init__(self, model_dir: str | Path = "models/live") -> None:
        self.model_dir = Path(model_dir)
        self.models: dict[int, Any] = {}
        self.metadata: dict[int, dict[str, Any]] = {}

    def load_model(self, horizon_minutes: int) -> dict[str, Any]:
        if horizon_minutes not in HORIZONS_MINUTES:
            raise ValueError(f"Supported horizons: {HORIZONS_MINUTES}")

        artifact = self.model_dir / f"model_{horizon_minutes}m.joblib"
        metadata_file = self.model_dir / f"model_{horizon_minutes}m.json"

        if not artifact.is_file() or not metadata_file.is_file():
            return {
                "status": "NO_MODEL",
                "horizon_minutes": horizon_minutes,
            }

        try:
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))

            if metadata.get("horizon_minutes") != horizon_minutes:
                raise ValueError("Model metadata horizon mismatch")

            model = joblib.load(artifact)

            if not callable(getattr(model, "predict_proba", None)):
                raise ValueError("Model must provide predict_proba()")

            self.models[horizon_minutes] = model
            self.metadata[horizon_minutes] = metadata

            return {
                "status": "LOADED",
                "horizon_minutes": horizon_minutes,
                "version": metadata.get("version", "unspecified"),
            }

        except Exception as exc:
            self.models.pop(horizon_minutes, None)
            self.metadata.pop(horizon_minutes, None)
            return {
                "status": "LOAD_ERROR",
                "horizon_minutes": horizon_minutes,
                "error": str(exc),
            }

    def load_all(self) -> list[dict[str, Any]]:
        return [self.load_model(h) for h in HORIZONS_MINUTES]

    def get_predictor(self, horizon_minutes: int) -> Any | None:
        return self.models.get(horizon_minutes)

    def status(self) -> dict[str, Any]:
        return {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "models": {
                f"{h}m": {
                    "loaded": h in self.models,
                    "version": self.metadata.get(h, {}).get("version"),
                }
                for h in HORIZONS_MINUTES
            },
        }
