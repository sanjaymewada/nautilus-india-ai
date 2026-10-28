"""Incremental causal features for six live prediction horizons."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

import numpy as np
import pandas as pd

from src.live.candle_aggregator import Candle


HORIZONS_MINUTES = (1, 5, 15, 30, 60, 240)


class LiveFeatureEngine:
    """Maintain completed 1-minute candles and derive horizon-specific features."""

    def __init__(self, max_candles: int = 1600) -> None:
        if max_candles < 300:
            raise ValueError("max_candles must be at least 300")

        self.max_candles = max_candles
        self._history: dict[str, deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=self.max_candles)
        )

    def update(self, candle: Candle) -> dict[str, Any] | None:
        """Add a completed candle and return features when sufficient history exists."""
        history = self._history[candle.symbol]

        if history and candle.start_time <= history[-1]["timestamp"]:
            return None

        history.append({
            "timestamp": candle.start_time,
            "open": float(candle.open),
            "high": float(candle.high),
            "low": float(candle.low),
            "close": float(candle.close),
            "volume": float(candle.volume),
        })

        # Require enough 1-minute candles to construct a 4-hour window.
        if len(history) < 240:
            return None

        frame = pd.DataFrame(list(history)).set_index("timestamp").sort_index()
        close_1m = frame["close"]
        volume_1m = frame["volume"]

        output: dict[str, Any] = {
            "symbol": candle.symbol,
            "timestamp": candle.start_time.isoformat(),
            "close": float(close_1m.iloc[-1]),
            "ready": True,
            "horizons": {},
        }

        # Aggregate completed 1-minute candles into higher timeframes.
        # The current bucket is excluded unless it has ended.
        for horizon in HORIZONS_MINUTES:
            if horizon == 1:
                tf = frame.copy()
            else:
                rule = f"{horizon}min"
                tf = frame.resample(
                    rule,
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

                # Only use buckets whose entire timeframe has elapsed.
                latest_time = pd.Timestamp(candle.start_time)
                if latest_time.tzinfo is None:
                    latest_time = latest_time.tz_localize("UTC")
                else:
                    latest_time = latest_time.tz_convert("UTC")

                tf.index = pd.to_datetime(tf.index, utc=True)
                tf = tf.loc[
                    tf.index + pd.Timedelta(minutes=horizon) <= latest_time
                ]

            needed = 35
            if len(tf) < needed:
                output["horizons"][str(horizon)] = {
                    "ready": False,
                    "reason": "INSUFFICIENT_TIMEFRAME_HISTORY",
                    "bars_available": len(tf),
                    "bars_required": needed,
                }
                continue

            close = tf["close"]
            volume = tf["volume"]
            returns = close.pct_change()
            sma_5 = close.rolling(5).mean()
            sma_10 = close.rolling(10).mean()
            sma_20 = close.rolling(20).mean()
            sma_30 = close.rolling(30).mean()
            vol_mean = volume.rolling(20).mean()
            volatility_10 = returns.rolling(10).std()

            current = float(close.iloc[-1])
            previous = float(close.iloc[-2])
            vol_avg = float(vol_mean.iloc[-1])

            feature_set = {
                "close": current,
                "return_1bar": current / previous - 1,
                "return_5bar": current / float(close.iloc[-6]) - 1,
                "return_15bar": current / float(close.iloc[-16]) - 1,
                "sma_5_gap": current / float(sma_5.iloc[-1]) - 1,
                "sma_10_gap": current / float(sma_10.iloc[-1]) - 1,
                "sma_20_gap": current / float(sma_20.iloc[-1]) - 1,
                "sma_30_gap": current / float(sma_30.iloc[-1]) - 1,
                "volatility_10bar": float(volatility_10.iloc[-1]),
                "candle_range_pct": float(
                    (tf["high"].iloc[-1] - tf["low"].iloc[-1]) / current
                ),
                "volume": float(volume.iloc[-1]),
                "volume_ratio_20": (
                    float(volume.iloc[-1] / vol_avg) if vol_avg > 0 else None
                ),
                "bars_available": len(tf),
                "ready": True,
            }

            for key, value in list(feature_set.items()):
                if isinstance(value, (float, np.floating)) and not np.isfinite(value):
                    feature_set[key] = None

            output["horizons"][str(horizon)] = feature_set

        return output
