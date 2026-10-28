"""Controller for running Yahoo Finance polling with the live pipeline."""

from __future__ import annotations

import threading
from typing import Any

from src.live.live_pipeline import LivePipeline
from src.live.yahoo_feed import YahooPollingFeed


class YahooLiveController:
    """Manage a background Yahoo polling loop and expose runtime status."""

    def __init__(
        self,
        symbols: list[str],
        period: str = "5d",
        interval: str = "1m",
        poll_seconds: int = 60,
        pipeline: LivePipeline | None = None,
    ) -> None:
        self.symbols = [s.strip().upper() for s in symbols if s.strip()]
        if not self.symbols:
            raise ValueError("At least one symbol is required.")

        self.pipeline = pipeline or LivePipeline()
        self.feed = YahooPollingFeed(
            symbols=self.symbols,
            pipeline=self.pipeline,
            period=period,
            interval=interval,
            poll_seconds=poll_seconds,
        )
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._running = False
        self._last_poll_result: dict[str, int] = {}
        self._poll_count = 0
        self._last_error: str | None = None

    def start(self) -> None:
        """Start polling in a daemon thread; safe to call only once at a time."""
        with self._lock:
            if self._running:
                return
            self._stop_event.clear()
            self._running = True
            self._last_error = None
            self._thread = threading.Thread(
                target=self._run,
                name="yahoo-live-controller",
                daemon=True,
            )
            self._thread.start()

    def _run(self) -> None:
        try:
            self.feed.connect()
            while not self._stop_event.is_set():
                result = self.feed.poll_once()
                with self._lock:
                    self._last_poll_result = result
                    self._poll_count += 1

                if self._stop_event.wait(self.feed.poll_seconds):
                    break
        except Exception as exc:
            with self._lock:
                self._last_error = str(exc)
        finally:
            self.feed.disconnect()
            with self._lock:
                self._running = False

    def stop(self, timeout: float = 5.0) -> None:
        """Request shutdown and wait briefly for the polling thread."""
        self._stop_event.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=max(0.0, timeout))
        if not thread or not thread.is_alive():
            self.feed.disconnect()
            with self._lock:
                self._running = False

    def status(self) -> dict[str, Any]:
        """Return controller, polling and pipeline status."""
        with self._lock:
            running = self._running
            poll_count = self._poll_count
            last_poll_result = dict(self._last_poll_result)
            last_error = self._last_error

        return {
            "running": running,
            "source": "YAHOO_FINANCE_POLLING",
            "symbols": list(self.symbols),
            "poll_interval_seconds": self.feed.poll_seconds,
            "poll_count": poll_count,
            "last_poll_result": last_poll_result,
            "feed_errors": dict(self.feed.last_errors),
            "controller_error": last_error,
            "pipeline": self.pipeline.snapshot(),
            "note": (
                "Yahoo polling is not a guaranteed real-time exchange feed. "
                "Historical rows may be processed on the first poll."
            ),
        }
