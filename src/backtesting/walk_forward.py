"""Chronological walk-forward splits for historical strategy research.

This module creates train/test date ranges only. It does not train models,
generate signals, or execute trades.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import time

import pandas as pd


@dataclass
class WalkForwardConfig:
    train_size: int = 120
    test_size: int = 20
    step_size: int = 20
    min_train_size: int = 60


def create_walk_forward_splits(
    data: pd.DataFrame,
    config: WalkForwardConfig | None = None,
    timestamp_col: str = "timestamp",
) -> list[dict]:
    config = config or WalkForwardConfig()

    if config.train_size < config.min_train_size:
        raise ValueError("train_size must be >= min_train_size")
    if config.test_size <= 0 or config.step_size <= 0:
        raise ValueError("test_size and step_size must be positive")
    if timestamp_col not in data.columns:
        raise ValueError(f"Missing timestamp column: {timestamp_col}")

    df = data.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True, errors="coerce")
    df = df.dropna(subset=[timestamp_col]).sort_values(timestamp_col)
    df = df.drop_duplicates(subset=[timestamp_col]).reset_index(drop=True)

    splits = []
    split_number = 1
    train_end = config.train_size

    while train_end + config.test_size <= len(df):
        train = df.iloc[:train_end]
        test = df.iloc[train_end:train_end + config.test_size]

        splits.append({
            "split": split_number,
            "train_rows": len(train),
            "test_rows": len(test),
            "train_start": train[timestamp_col].iloc[0].isoformat(),
            "train_end": train[timestamp_col].iloc[-1].isoformat(),
            "test_start": test[timestamp_col].iloc[0].isoformat(),
            "test_end": test[timestamp_col].iloc[-1].isoformat(),
            "chronological_order_valid": (
                train[timestamp_col].max() < test[timestamp_col].min()
            ),
        })

        split_number += 1
        train_end += config.step_size

    return splits


def export_walk_forward_report(
    splits: list[dict],
    output_dir: str | Path,
    config: WalkForwardConfig | None = None,
) -> Path:
    config = config or WalkForwardConfig()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"walk_forward_{stamp}.json"

    payload = {
        "config": asdict(config),
        "split_count": len(splits),
        "splits": splits,
        "warning": (
            "Split generation only. Fit indicators and models using training "
            "data only; evaluate decisions on untouched test periods. "
            "Account for warm-up bars, overlapping labels, and transaction costs."
        ),
    }

    output_path.write_text(json.dumps(payload, indent=2, allow_nan=False))
    return output_path
