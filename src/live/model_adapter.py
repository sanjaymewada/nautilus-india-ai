"""Adapt live multi-horizon features to each trained model's schema."""

from __future__ import annotations

from typing import Any


class HorizonModelAdapter:
    def __init__(self, manager: Any) -> None:
        self.manager = manager

    def predictors(self) -> dict[int, Any]:
        predictors = {}

        for horizon in (1, 5, 15, 30, 60, 240):
            predictor = self.manager.get_predictor(horizon)
            if predictor is not None:
                predictors[horizon] = predictor

        return predictors

    def features_for_horizon(
        self,
        all_features: dict[str, Any],
        horizon: int,
    ) -> dict[str, Any] | None:
        horizons = all_features.get("horizons", {})
        features = horizons.get(str(horizon), horizons.get(horizon))

        if not isinstance(features, dict) or not features.get("ready"):
            return None

        model = self.manager.get_predictor(horizon)
        if model is None:
            return None

        metadata = getattr(self.manager, "metadata", {})
        model_metadata = metadata.get(horizon, {})
        columns = model_metadata.get("feature_columns")

        if not columns:
            columns = getattr(model, "feature_names_in_", None)

        if columns is None:
            return None

        selected = {}
        for column in columns:
            value = features.get(column)
            if value is None:
                return None
            selected[column] = value

        return selected
