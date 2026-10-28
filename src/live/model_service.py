"""Build the live prediction engine from available trained models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.live.model_adapter import HorizonModelAdapter
from src.live.model_manager import HORIZONS_MINUTES, ModelManager
from src.live.prediction_engine import LivePredictionEngine


@dataclass
class LiveModelService:
    manager: ModelManager
    adapter: HorizonModelAdapter
    engine: LivePredictionEngine
    load_results: dict[int, dict[str, Any]]

    @classmethod
    def create(
        cls,
        model_dir: str | Path = "models/live",
        min_confidence: float = 0.60,
    ) -> "LiveModelService":
        manager = ModelManager(model_dir=model_dir)
        load_results = manager.load_all()

        adapter = HorizonModelAdapter(manager)
        engine = LivePredictionEngine(
            predictors=adapter.predictors(),
            min_confidence=min_confidence,
            adapter=adapter,
        )

        return cls(
            manager=manager,
            adapter=adapter,
            engine=engine,
            load_results=load_results,
        )

    def status(self) -> dict[str, Any]:
        loaded = self.adapter.predictors()

        return {
            "models_directory": str(self.manager.model_dir),
            "available_horizons": list(HORIZONS_MINUTES),
            "loaded_horizons": sorted(loaded.keys()),
            "missing_horizons": [
                horizon
                for horizon in HORIZONS_MINUTES
                if horizon not in loaded
            ],
            "load_results": self.load_results,
        }

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        """Generate predictions using the currently loaded models."""
        return self.engine.predict(features)
