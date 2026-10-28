"""Broker-independent live market feed interface.

Broker integrations should implement this interface and normalize incoming
market data into MarketTick objects. No broker connection is made here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Callable, Iterable


@dataclass(frozen=True, slots=True)
class MarketTick:
    symbol: str
    timestamp: datetime
    last_price: float
    volume: float | None = None
    bid: float | None = None
    ask: float | None = None
    source: str = "unknown"

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")
        if self.last_price <= 0:
            raise ValueError("last_price must be positive")
        if self.volume is not None and self.volume < 0:
            raise ValueError("volume cannot be negative")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")

    def to_dict(self) -> dict:
        record = asdict(self)
        record["timestamp"] = self.timestamp.isoformat()
        return record


TickHandler = Callable[[MarketTick], None]


class LiveMarketFeed(ABC):
    """Interface that future broker or vendor adapters must implement."""

    @abstractmethod
    def connect(self) -> None:
        """Connect to the provider and begin receiving data."""
        raise NotImplementedError

    @abstractmethod
    def subscribe(self, symbols: Iterable[str]) -> None:
        """Subscribe to one or more symbols."""
        raise NotImplementedError

    @abstractmethod
    def set_tick_handler(self, handler: TickHandler) -> None:
        """Register the callback for normalized market ticks."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """Close the provider connection cleanly."""
        raise NotImplementedError
