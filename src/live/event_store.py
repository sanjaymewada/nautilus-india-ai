"""Append-only local event store for live market learning."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class LiveEventStore:
    """Persist live events as JSON Lines, one event per record."""

    def __init__(self, data_dir: str | Path = "data/live") -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): LiveEventStore._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [LiveEventStore._json_safe(v) for v in value]
        if isinstance(value, Path):
            return str(value)
        if hasattr(value, "item"):
            try:
                return value.item()
            except (ValueError, TypeError):
                pass
        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except (ValueError, TypeError):
                pass
        return value

    def append(self, stream: str, event: dict[str, Any]) -> Path:
        """Append one event to a named stream."""
        if not stream or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for ch in stream):
            raise ValueError("stream must contain only lowercase letters, digits, _ or -")

        record = {
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "event": self._json_safe(event),
        }
        line = json.dumps(record, ensure_ascii=False, allow_nan=False)

        path = self.data_dir / f"{stream}.jsonl"
        with self._lock:
            with path.open("a", encoding="utf-8") as file:
                file.write(line + "\n")
                file.flush()

        return path

    def save_candle(self, candle: dict[str, Any]) -> Path:
        return self.append("candles", candle)

    def save_features(self, features: dict[str, Any]) -> Path:
        return self.append("features", features)

    def save_prediction(self, prediction: dict[str, Any]) -> Path:
        return self.append("predictions", prediction)

    def save_outcome(self, outcome: dict[str, Any]) -> Path:
        return self.append("outcomes", outcome)
