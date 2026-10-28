"""Train research models compatible with the existing LiveModelService."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report
from sklearn.pipeline import Pipeline

from src.market_data import fetch_yahoo
from src.live.model_manager import HORIZONS_MINUTES

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "live"
REPORT_DIR = ROOT / "data" / "research"

# Must match the names emitted by LiveFeatureEngine.
FEATURES = [
    "return_1bar",
    "return_5bar",
    "return_15bar",
    "sma_5_gap",
    "sma_10_gap",
    "sma_20_gap",
    "sma_30_gap",
    "volatility_10bar",
    "candle_range_pct",
    "volume_ratio_20",
]

# UP/DOWN/FLAT are the labels expected by LivePredictionEngine.
FLAT_THRESHOLD = 0.0005
MIN_ROWS = 120
MIN_TEST_ROWS = 100
MIN_BALANCED_ACCURACY = 0.52

def make_features(frame: pd.DataFrame) -> pd.DataFrame:
    close = frame["close"].astype(float)
    volume = frame["volume"].astype(float)
    returns = close.pct_change()

    result = pd.DataFrame(index=frame.index)
    result["return_1bar"] = close / close.shift(1) - 1
    result["return_5bar"] = close / close.shift(5) - 1
    result["return_15bar"] = close / close.shift(15) - 1

    for n in (5, 10, 20, 30):
        result[f"sma_{n}_gap"] = close / close.rolling(n).mean() - 1

    result["volatility_10bar"] = returns.rolling(10).std()
    result["candle_range_pct"] = (
        (frame["high"] - frame["low"]) / close
    )

    vol_avg = volume.rolling(20).mean()
    result["volume_ratio_20"] = volume / vol_avg.replace(0, np.nan)

    return result.replace([np.inf, -np.inf], np.nan)


def prepare_symbol(symbol: str, raw: pd.DataFrame, horizon: int) -> pd.DataFrame:
    frame = raw.copy().sort_index()
    frame.index = pd.to_datetime(frame.index, utc=True)
    frame = frame[~frame.index.duplicated(keep="last")]

    if horizon > 1:
        frame = frame.resample(
            f"{horizon}min",
            label="left",
            closed="left",
            origin="start_day",
        ).agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }).dropna(subset=["close"])

    x = make_features(frame)

    # Predict the direction of the NEXT completed bar of this horizon.
    future_return = frame["close"].shift(-1) / frame["close"] - 1
    y = pd.Series("FLAT", index=frame.index, dtype="object")
    y.loc[future_return > FLAT_THRESHOLD] = "UP"
    y.loc[future_return < -FLAT_THRESHOLD] = "DOWN"
    y.loc[future_return.isna()] = np.nan

    data = x.copy()
    data["target"] = y
    data["symbol"] = symbol
    data["timestamp"] = data.index
    data = data.dropna(subset=["target"])
    data = data.replace([np.inf, -np.inf], np.nan)
    data = data.dropna(subset=["return_1bar", "return_5bar", "return_15bar"])
    return data


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    # Yahoo's 1-minute history is limited. Multiple symbols pool examples;
    # this does NOT make them independent market observations.
    symbols = [
        s.strip().upper()
        for s in __import__("os").environ.get(
            "TRAIN_SYMBOLS",
            "RELIANCE.NS,TCS.NS,INFY.NS,WIPRO.NS,HDFCBANK.NS,ICICIBANK.NS"
        ).split(",")
        if s.strip()
    ]

    raw_by_symbol = {}
    print("Fetching Yahoo historical 1-minute bars (not a live feed)...")
    for symbol in symbols:
        try:
            actual_symbol, frame = fetch_yahoo(symbol, "7d", "1m")
            raw_by_symbol[actual_symbol] = frame
            print(f"  {actual_symbol}: {len(frame)} bars")
        except Exception as exc:
            print(f"  SKIP {symbol}: {exc}")

    if not raw_by_symbol:
        raise SystemExit("No historical data downloaded. Check internet and Yahoo symbols.")

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "Yahoo Finance historical 1-minute OHLCV",
        "symbols": list(raw_by_symbol),
        "flat_threshold": FLAT_THRESHOLD,
        "models": {},
        "warnings": [
            "Historical replay/training is not a live market feed.",
            "Direction classification metrics do not prove profitability.",
            "No transaction-cost-aware profitability claim is made.",
            "Models are trained research artifacts, not evidence of a profitable strategy.",
        ],
    }

    for horizon in HORIZONS_MINUTES:
        pieces = []
        for symbol, raw in raw_by_symbol.items():
            try:
                part = prepare_symbol(symbol, raw, horizon)
                if not part.empty:
                    pieces.append(part)
            except Exception as exc:
                print(f"  {symbol} / {horizon}m preparation failed: {exc}")

        if not pieces:
            report["models"][str(horizon)] = {
                "status": "INSUFFICIENT_DATA",
                "reason": "No usable feature rows",
            }
            print(f"{horizon:>3}m: INSUFFICIENT_DATA")
            continue

        data = pd.concat(pieces).sort_values("timestamp")
        data = data.dropna(subset=["target"])
        counts = data["target"].value_counts().to_dict()

        if len(data) < MIN_ROWS:
            report["models"][str(horizon)] = {
                "status": "INSUFFICIENT_DATA",
                "rows": int(len(data)),
                "class_counts": counts,
                "reason": f"Need at least {MIN_ROWS} usable rows",
            }
            print(f"{horizon:>3}m: INSUFFICIENT_DATA ({len(data)} rows)")
            continue

        # One global chronological cutoff avoids randomly mixing timestamps.
        unique_times = np.sort(data["timestamp"].unique())
        cutoff_idx = int(len(unique_times) * 0.8)
        if cutoff_idx <= 0 or cutoff_idx >= len(unique_times):
            print(f"{horizon}m: invalid chronological split")
            continue
        cutoff = unique_times[cutoff_idx]

        train = data[data["timestamp"] < cutoff]
        test = data[data["timestamp"] >= cutoff]

        if (
            len(test) < MIN_TEST_ROWS
            or set(train["target"]) != {"UP", "DOWN", "FLAT"}
            or len(test["target"].unique()) < 2
        ):
            report["models"][str(horizon)] = {
                "status": "INSUFFICIENT_VALIDATION",
                "rows": int(len(data)),
                "train_rows": int(len(train)),
                "test_rows": int(len(test)),
                "class_counts": counts,
                "reason": "Validation needs adequate rows and all three training classes",
            }
            print(f"{horizon:>3}m: INSUFFICIENT_VALIDATION "
                  f"(train={len(train)}, test={len(test)}, classes={counts})")
            continue

        model = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("classifier", RandomForestClassifier(
                n_estimators=250,
                max_depth=7,
                min_samples_leaf=4,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )),
        ])

        model.fit(train[FEATURES], train["target"])
        predicted = model.predict(test[FEATURES])
        accuracy = float(accuracy_score(test["target"], predicted))
        balanced = float(balanced_accuracy_score(test["target"], predicted))

        metrics = {
            "accuracy": accuracy,
            "balanced_accuracy": balanced,
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
            "validation_start": str(pd.Timestamp(cutoff)),
            "class_counts_all": counts,
            "classification_report": classification_report(
                test["target"],
                predicted,
                labels=["DOWN", "FLAT", "UP"],
                output_dict=True,
                zero_division=0,
            ),
        }

        # Fail closed: don't make an unvalidated artifact loadable by the live service.
        if balanced < MIN_BALANCED_ACCURACY:
            report["models"][str(horizon)] = {
                "status": "VALIDATION_FAILED",
                "metrics": metrics,
                "reason": f"Balanced accuracy below {MIN_BALANCED_ACCURACY:.2f}",
            }
            print(f"{horizon:>3}m: VALIDATION_FAILED (balanced_accuracy={balanced:.3f})")
            continue

        artifact = MODEL_DIR / f"model_{horizon}m.joblib"
        metadata_file = MODEL_DIR / f"model_{horizon}m.json"
        version = f"rf-{horizon}m-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

        metadata = {
            "horizon_minutes": horizon,
            "version": version,
            "algorithm": "RandomForestClassifier",
            "feature_columns": FEATURES,
            "classes": [str(c) for c in model.classes_],
            "label_definition": (
                f"next {horizon}-minute bar return; "
                f"UP > {FLAT_THRESHOLD}, DOWN < -{FLAT_THRESHOLD}, else FLAT"
            ),
            "data_source": "Yahoo Finance historical 1-minute OHLCV",
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "validation": metrics,
            "status": "RESEARCH_VALIDATED_NOT_PROVEN_PROFITABLE",
        }

        # Save only after validation passed.
        joblib.dump(model, artifact)
        metadata_file.write_text(
            json.dumps(metadata, indent=2, allow_nan=False),
            encoding="utf-8",
        )

        report["models"][str(horizon)] = {
            "status": "SAVED_AFTER_VALIDATION",
            "artifact": str(artifact.relative_to(ROOT)),
            "metadata": str(metadata_file.relative_to(ROOT)),
            "metrics": metrics,
        }
        print(f"{horizon:>3}m: SAVED "
              f"(rows={len(data)}, balanced_accuracy={balanced:.3f})")

    report_path = REPORT_DIR / "live_horizon_training_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(f"\nReport: {report_path}")
    print("\nModel service reload check:")
    from src.live.model_service import LiveModelService
    service = LiveModelService.create(model_dir=MODEL_DIR)
    print(json.dumps(service.status(), indent=2, default=str))


if __name__ == "__main__":
    main()
