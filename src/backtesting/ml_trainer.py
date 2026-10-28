"""Offline ML classifier for next-candle direction research."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer


FEATURES = [
    "return_1",
    "return_5",
    "volatility_10",
    "sma_gap",
    "range_pct",
    "volume_change",
]


class MLTrainer:
    """Train a Random Forest using a chronological holdout split."""

    def __init__(
        self,
        test_fraction: float = 0.2,
        random_seed: int = 42,
    ) -> None:
        if not 0.1 <= test_fraction <= 0.4:
            raise ValueError("test_fraction must be between 0.1 and 0.4")

        self.test_fraction = test_fraction
        self.random_seed = random_seed
        self.model: Pipeline | None = None

    @staticmethod
    def prepare_data(data: pd.DataFrame) -> pd.DataFrame:
        frame = data.copy()

        # Normalize common OHLCV column names.
        rename = {}
        for column in frame.columns:
            key = str(column).strip().lower()
            if key in {"open", "high", "low", "close", "volume"}:
                rename[column] = key
        frame = frame.rename(columns=rename)

        if "close" not in frame.columns:
            raise ValueError("Input must contain a close column")

        frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
        for column in ("open", "high", "low", "volume"):
            if column in frame.columns:
                frame[column] = pd.to_numeric(frame[column], errors="coerce")

        close = frame["close"]
        frame["return_1"] = close.pct_change()
        frame["return_5"] = close.pct_change(5)
        frame["volatility_10"] = frame["return_1"].rolling(10).std()
        frame["sma_gap"] = (
            close.rolling(10).mean() / close.rolling(30).mean() - 1
        )

        if {"high", "low"}.issubset(frame.columns):
            frame["range_pct"] = (frame["high"] - frame["low"]) / close
        else:
            frame["range_pct"] = float("nan")

        if "volume" in frame.columns:
            frame["volume_change"] = frame["volume"].pct_change()
        else:
            frame["volume_change"] = float("nan")

        # Label uses the next candle's close, never a feature.
        frame["target"] = (close.shift(-1) > close).astype("int8")
        frame.loc[close.shift(-1).isna(), "target"] = pd.NA

        frame = frame.replace([float("inf"), float("-inf")], float("nan"))
        frame = frame.dropna(subset=["target"]).copy()
        frame["target"] = frame["target"].astype("int8")

        if len(frame) < 60:
            raise ValueError(
                "Need at least 60 labelled candles for a basic chronological split"
            )

        return frame

    def train(self, data: pd.DataFrame) -> dict[str, Any]:
        frame = self.prepare_data(data)
        split = int(len(frame) * (1 - self.test_fraction))

        train = frame.iloc[:split]
        test = frame.iloc[split:]

        if train["target"].nunique() < 2:
            raise ValueError("Training data contains only one target class")

        self.model = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "classifier",
                    RandomForestClassifier(
                        n_estimators=200,
                        max_depth=6,
                        min_samples_leaf=3,
                        class_weight="balanced",
                        random_state=self.random_seed,
                        n_jobs=-1,
                    ),
                ),
            ]
        )

        self.model.fit(train[FEATURES], train["target"])
        predictions = self.model.predict(test[FEATURES])

        metrics = {
            "accuracy": float(accuracy_score(test["target"], predictions)),
            "test_rows": int(len(test)),
            "train_rows": int(len(train)),
            "test_up_rate_pct": float(test["target"].mean() * 100),
            "classification_report": classification_report(
                test["target"],
                predictions,
                labels=[0, 1],
                target_names=["DOWN_OR_FLAT", "UP"],
                output_dict=True,
                zero_division=0,
            ),
        }

        classifier = self.model.named_steps["classifier"]
        metrics["feature_importance"] = {
            name: float(value)
            for name, value in zip(FEATURES, classifier.feature_importances_)
        }

        return {
            "algorithm": "random_forest_classifier",
            "target": "next_candle_close_higher",
            "features": FEATURES,
            "split_method": "chronological_holdout",
            "metrics": metrics,
            "limitations": [
                "Direction accuracy alone does not establish profitability.",
                "No transaction costs or trading execution are included.",
                "Missing volume or high/low data leaves those features imputed.",
                "A single holdout is preliminary; walk-forward evaluation is still needed.",
            ],
        }

    @staticmethod
    def export_json(
        report: dict[str, Any],
        path: str | Path = "data/research/ml_training_report.json",
    ) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        return output_path
