"""Yahoo Finance polling adapter for the live prediction pipeline.

Yahoo data is polled periodically and is not guaranteed to be real-time.
This adapter emits only newly observed candle timestamps.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Callable

import pandas as pd

from src.market_data import fetch_yahoo
from src.live.market_feed import MarketTick


class YahooPollingFeed:
    """Poll Yahoo Finance candles and forward new observations as MarketTick."""

    def __init__(
        self,
        symbols: list[str],
        pipeline,
        period: str = "5d",
        interval: str = "1m",
        poll_seconds: int = 60,
    ) -> None:
        if not symbols:
            raise ValueError("Provide at least one Yahoo Finance symbol.")
        if poll_seconds < 15:
            raise ValueError("poll_seconds must be at least 15 seconds.")

        self.symbols = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
        self.pipeline = pipeline
        self.period = period
        self.interval = interval
        self.poll_seconds = poll_seconds
        self.connected = False
        self.last_seen: dict[str, pd.Timestamp] = {}
        self.last_errors: dict[str, str] = {}

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def poll_once(self) -> dict[str, int]:
        """Fetch each symbol once and process newly observed candle rows."""
        if not self.connected:
            raise RuntimeError("Call connect() before poll_once().")

        processed: dict[str, int] = {}

        for requested_symbol in self.symbols:
            try:
                ticker, frame = fetch_yahoo(
                    requested_symbol, self.period, self.interval
                )
                frame = frame.sort_index()
                last_seen = self.last_seen.get(ticker)
                if last_seen is not None:
                    frame = frame[frame.index > last_seen]

                count = 0
                for candle_time, row in frame.iterrows():
                    timestamp = pd.Timestamp(candle_time)
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.tz_localize("UTC")
                    else:
                        timestamp = timestamp.tz_convert("UTC")

                    tick = MarketTick(
                        symbol=ticker,
                        timestamp=timestamp.to_pydatetime(),
                        last_price=float(row["close"]),
                        volume=float(row["volume"]),
                        bid=None,
                        ask=None,
                        source="YAHOO_FINANCE_POLLING",
                    )
                    self.pipeline.on_tick(tick)
                    self.last_seen[ticker] = pd.Timestamp(candle_time)
                    count += 1

                processed[ticker] = count
                self.last_errors.pop(ticker, None)

            except Exception as exc:
                self.last_errors[requested_symbol] = str(exc)
                processed[requested_symbol] = 0

        return processed

    def run_forever(self) -> None:
        """Poll continuously until disconnect() is called."""
        self.connect()
        while self.connected:
            started = time.monotonic()
            self.poll_once()
            elapsed = time.monotonic() - started
            time.sleep(max(0.0, self.poll_seconds - elapsed))
