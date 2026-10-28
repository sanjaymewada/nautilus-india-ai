"""Train separate time-ordered classifiers for live forecast horizons."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score

HORIZONS_MINUTES = (1, 5, 15, 30, 60, 240)

FEATURE_COLUMNS = [
    "return_1bar",
    "return_5bar",
    "return_15bar",
    "sma_5_gap",
    "sma_10_gap",
    "sma_20_gap",
    "sma_30_gap",
    "volatility_10bar",
    "volume_ratio_20",
    "candle_range_pct",
]


class LiveModelTrainer:
    """Train and save horizon-specific models using chronological splits."""

    def __init__(
        self,
        model_dir: str | Path = "models/live",
        train_fraction: float = 0.80,
        random_state: int = 42,
    ) -> None:
        if not 0.5 <= train_fraction < 1.0:
            raise ValueError("train_fraction must be >= 0.5 and < 1.0")

        self.model_dir = Path(model_dir)
        self.train_fraction = train_fraction
        self.random_state = random_state

    def train_one(
        self,
        dataset_path: str | Path,
        horizon_minutes: int,
    ) -> dict[str, Any]:
        if horizon_minutes not in HORIZONS_MINUTES:
            raise ValueError(f"Unsupported horizon: {horizon_minutes}")

        frame = pd.read_csv(dataset_path)
        missing = set(FEATURE_COLUMNS + ["timestamp", "target"]) - set(frame.columns)
        if missing:
            raise ValueError(f"Dataset is missing columns: {sorted(missing)}")

        frame["timestamp"] = pd.to_datetime(
            frame["timestamp"], utc=True, errors="coerce"
        )
        frame = frame.dropna(
            subset=["timestamp", "target"] + FEATURE_COLUMNS
        ).sort_values("timestamp").reset_index(drop=True)

        if len(frame) < 100:
            raise ValueError(
                f"Need at least 100 clean rows; found {len(frame)}"
            )

        if "horizon_minutes" in frame.columns:
            horizons = set(frame["horizon_minutes"].dropna().astype(int))
            if horizons != {horizon_minutes}:
                raise ValueError(
                    f"Dataset horizon {horizons} does not match "
                    f"requested {horizon_minutes}"
                )

        split = int(len(frame) * self.train_fraction)
        train = frame.iloc[:split]
        validation = frame.iloc[split:]

        if train["target"].nunique() < 2:
            raise ValueError("Training data contains fewer than two target classes")
        if validation["target"].nunique() < 2:
            raise ValueError("Validation data must contain at least two classes")

        model = RandomForestClassifier(
            n_estimators=160,
            max_depth=10,
            min_samples_leaf=5,
            class_weight="balanced_subsample",
            random_state=self.random_state,
            n_jobs=2,
        )

        model.fit(train[FEATURE_COLUMNS], train["target"])
        predicted = model.predict(validation[FEATURE_COLUMNS])

        metrics = {
            "accuracy": float(accuracy_score(validation["target"], predicted)),
            "balanced_accuracy": float(
                balanced_accuracy_score(validation["target"], predicted)
            ),
            "train_rows": int(len(train)),
            "validation_rows": int(len(validation)),
        }

        self.model_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = self.model_dir / f"model_{horizon_minutes}m.joblib"
        metadata_path = self.model_dir / f"model_{horizon_minutes}m.json"

        model.model_version = (
            f"{horizon_minutes}m-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        )
        joblib.dump(model, artifact_path)

        metadata = {
            "horizon_minutes": horizon_minutes,
            "version": model.model_version,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "feature_columns": FEATURE_COLUMNS,
            "classes": [str(c) for c in model.classes_],
            "metrics": metrics,
            "dataset_path": str(dataset_path),
            "validation_method": "chronological_holdout",
            "status": "TRAINED_NOT_PROMOTED",
        }
        metadata_path.write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

        return {
            "status": "TRAINED_NOT_PROMOTED",
            "horizon_minutes": horizon_minutes,
            "artifact": str(artifact_path),
            "metadata": str(metadata_path),
            "metrics": metrics,
        }

    def train_all(
        self,
        dataset_dir: str | Path = "data/training",
    ) -> list[dict[str, Any]]:
        results = []
        source = Path(dataset_dir)

        for horizon in HORIZONS_MINUTES:
            dataset = source / f"training_{horizon}m.csv"
            if not dataset.is_file():
                results.append({
                    "status": "DATASET_MISSING",
                    "horizon_minutes": horizon,
                    "expected_path": str(dataset),
                })
                continue

            try:
                results.append(self.train_one(dataset, horizon))
            except Exception as exc:
                results.append({
                    "status": "TRAINING_ERROR",
                    "horizon_minutes": horizon,
                    "error": str(exc),
                })

        return results
