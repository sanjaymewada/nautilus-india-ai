"""Aggregate normalized live market ticks into one-minute OHLCV candles."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from collections import defaultdict

from src.live.market_feed import MarketTick


@dataclass(frozen=True, slots=True)
class Candle:
    symbol: str
    start_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    tick_count: int
    source: str

    def to_dict(self) -> dict:
        record = asdict(self)
        record["start_time"] = self.start_time.isoformat()
        return record


class CandleAggregator:
    """Build candles from ticks and emit completed candles through a callback."""

    def __init__(self, interval_seconds: int = 60) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")

        self.interval_seconds = interval_seconds
        self._active: dict[str, dict] = {}
        self._last_timestamp: dict[str, datetime] = defaultdict(
            lambda: datetime.min.replace(tzinfo=timezone.utc)
        )

    def _bucket_start(self, timestamp: datetime) -> datetime:
        epoch = int(timestamp.timestamp())
        bucket = epoch - epoch % self.interval_seconds
        return datetime.fromtimestamp(bucket, tz=timezone.utc)

    def update(self, tick: MarketTick) -> Candle | None:
        """Add a tick; return a completed candle when a new interval starts.

        Ticks older than the most recently processed tick for a symbol are
        ignored to avoid corrupting candle order.
        """
        previous_timestamp = self._last_timestamp[tick.symbol]
        if tick.timestamp < previous_timestamp:
            return None

        self._last_timestamp[tick.symbol] = tick.timestamp
        bucket = self._bucket_start(tick.timestamp)
        active = self._active.get(tick.symbol)

        if active is None:
            self._active[tick.symbol] = self._new_candle(tick, bucket)
            return None

        if bucket < active["start_time"]:
            return None

        if bucket == active["start_time"]:
            self._add_tick(active, tick)
            return None

        completed = Candle(**active)
        self._active[tick.symbol] = self._new_candle(tick, bucket)
        return completed

    @staticmethod
    def _new_candle(tick: MarketTick, bucket: datetime) -> dict:
        return {
            "symbol": tick.symbol,
            "start_time": bucket,
            "open": tick.last_price,
            "high": tick.last_price,
            "low": tick.last_price,
            "close": tick.last_price,
            "volume": float(tick.volume or 0.0),
            "tick_count": 1,
            "source": tick.source,
        }

    @staticmethod
    def _add_tick(candle: dict, tick: MarketTick) -> None:
        candle["high"] = max(candle["high"], tick.last_price)
        candle["low"] = min(candle["low"], tick.last_price)
        candle["close"] = tick.last_price
        candle["volume"] += float(tick.volume or 0.0)
        candle["tick_count"] += 1
        candle["source"] = tick.source

    def flush(self, symbol: str | None = None) -> list[Candle]:
        """Return active candles explicitly on shutdown or session end."""
        symbols = [symbol] if symbol else list(self._active)
        completed = []

        for item in symbols:
            active = self._active.pop(item, None)
            if active is not None:
                completed.append(Candle(**active))

        return completed
