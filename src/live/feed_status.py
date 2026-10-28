"""Market feed health and freshness tracking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class FeedStatus:
    source: str = "UNCONFIGURED"
    connected: bool = False
    subscribed_symbols: int = 0
    last_tick_at: str | None = None
    last_error: str | None = None
    ticks_received: int = 0

    def mark_connected(self, source: str) -> None:
        self.source = source
        self.connected = True
        self.last_error = None

    def mark_disconnected(self) -> None:
        self.connected = False

    def mark_tick(self, timestamp: datetime | None = None) -> None:
        timestamp = timestamp or datetime.now(timezone.utc)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        self.last_tick_at = timestamp.isoformat()
        self.ticks_received += 1

    def mark_error(self, error: Exception | str) -> None:
        self.last_error = str(error)

    def snapshot(self) -> dict[str, Any]:
        age_seconds = None

        if self.last_tick_at:
            try:
                last_tick = datetime.fromisoformat(self.last_tick_at)
                age_seconds = max(
                    0.0,
                    (datetime.now(timezone.utc) - last_tick).total_seconds(),
                )
            except ValueError:
                age_seconds = None

        if not self.connected:
            health = "DISCONNECTED"
        elif age_seconds is None:
            health = "CONNECTED_NO_TICKS"
        elif age_seconds > 120:
            health = "STALE"
        else:
            health = "HEALTHY"

        return {
            "source": self.source,
            "connected": self.connected,
            "health": health,
            "subscribed_symbols": self.subscribed_symbols,
            "last_tick_at": self.last_tick_at,
            "tick_age_seconds": age_seconds,
            "ticks_received": self.ticks_received,
            "last_error": self.last_error,
        }
