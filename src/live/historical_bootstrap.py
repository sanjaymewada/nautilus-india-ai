"""Prepare historical OHLCV candles for multi-horizon model training."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

HORIZONS_MINUTES = (1, 5, 15, 30, 60, 240)


class HistoricalBootstrap:
    """Load candle data and create future-return labels without look-ahead features."""

    REQUIRED_COLUMNS = {"timestamp", "open", "high", "low", "close", "volume"}

    def __init__(self, flat_threshold_pct: float = 0.0005) -> None:
        if flat_threshold_pct < 0:
            raise ValueError("flat_threshold_pct must be non-negative")
        self.flat_threshold_pct = flat_threshold_pct

    def load_csv(self, path: str | Path) -> pd.DataFrame:
        """Load a CSV containing timestamp and OHLCV columns."""
        frame = pd.read_csv(path)
        missing = self.REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        frame["timestamp"] = pd.to_datetime(
            frame["timestamp"], utc=True, errors="coerce"
        )
        for column in ("open", "high", "low", "close", "volume"):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

        frame = frame.dropna(subset=list(self.REQUIRED_COLUMNS))
        frame = frame.sort_values("timestamp")
        frame = frame.drop_duplicates(subset=["timestamp"], keep="last")
        frame = frame[
            (frame["open"] > 0)
            & (frame["high"] > 0)
            & (frame["low"] > 0)
            & (frame["close"] > 0)
            & (frame["volume"] >= 0)
        ].reset_index(drop=True)

        return frame

    def build_dataset(
        self,
        candles: pd.DataFrame,
        symbol: str,
    ) -> dict[int, pd.DataFrame]:
        """Build one labelled dataset per horizon from 1-minute candles."""
        missing = self.REQUIRED_COLUMNS - set(candles.columns)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        frame = candles.copy()
        frame["timestamp"] = pd.to_datetime(
            frame["timestamp"], utc=True, errors="coerce"
        )
        frame = (
            frame.dropna(subset=["timestamp", "close"])
            .sort_values("timestamp")
            .drop_duplicates(subset=["timestamp"], keep="last")
            .reset_index(drop=True)
        )

        # Use only past/current information as model input.
        close = pd.to_numeric(frame["close"], errors="coerce")
        volume = pd.to_numeric(frame["volume"], errors="coerce")
        returns = close.pct_change()

        features = pd.DataFrame({
            "timestamp": frame["timestamp"],
            "symbol": symbol,
            "close": close,
            "return_1bar": returns,
            "return_5bar": close.pct_change(5),
            "return_15bar": close.pct_change(15),
            "sma_5_gap": close / close.rolling(5).mean() - 1,
            "sma_10_gap": close / close.rolling(10).mean() - 1,
            "sma_20_gap": close / close.rolling(20).mean() - 1,
            "sma_30_gap": close / close.rolling(30).mean() - 1,
            "volatility_10bar": returns.rolling(10).std(),
            "volume_ratio_20": volume / volume.rolling(20).mean().replace(0, pd.NA),
            "candle_range_pct": (
                pd.to_numeric(frame["high"], errors="coerce")
                - pd.to_numeric(frame["low"], errors="coerce")
            ) / close,
        })

        datasets: dict[int, pd.DataFrame] = {}

        for horizon in HORIZONS_MINUTES:
            future_close = close.shift(-horizon)
            future_return = future_close / close - 1

            labels = pd.Series("FLAT", index=frame.index, dtype="object")
            labels.loc[future_return > self.flat_threshold_pct] = "UP"
            labels.loc[future_return < -self.flat_threshold_pct] = "DOWN"

            dataset = features.copy()
            dataset["future_return"] = future_return
            dataset["target"] = labels
            dataset["horizon_minutes"] = horizon

            # Drop rows without enough past feature history or future labels.
            dataset = dataset.dropna(
                subset=[
                    "return_1bar",
                    "return_5bar",
                    "return_15bar",
                    "sma_30_gap",
                    "volatility_10bar",
                    "future_return",
                ]
            ).reset_index(drop=True)

            datasets[horizon] = dataset

        return datasets

    def save_datasets(
        self,
        datasets: dict[int, pd.DataFrame],
        output_dir: str | Path = "data/training",
    ) -> list[Path]:
        """Save horizon-specific datasets as CSV files."""
        destination = Path(output_dir)
        destination.mkdir(parents=True, exist_ok=True)

        saved: list[Path] = []
        for horizon, dataset in datasets.items():
            path = destination / f"training_{horizon}m.csv"
            dataset.to_csv(path, index=False)
            saved.append(path)

        return saved
