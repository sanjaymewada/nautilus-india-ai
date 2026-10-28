"""Execution timing audit helpers for the NautilusTrader backtest.

This module records signal and execution timestamps separately.
It does not submit orders or claim that next-bar execution occurred.
"""

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import time


@dataclass
class ExecutionTimingRecord:
    symbol: str
    signal: str
    signal_timestamp_ns: int
    signal_close: float
    planned_execution_timestamp_ns: int | None = None
    fill_timestamp_ns: int | None = None
    fill_price: float | None = None
    status: str = "SIGNAL_RECORDED"


class ExecutionTimingAudit:
    """Record signal-to-execution timing without placing orders."""

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.records: list[ExecutionTimingRecord] = []

    def record_signal(
        self,
        signal: str,
        signal_timestamp_ns: int,
        signal_close: float,
    ) -> int:
        if signal not in {"BUY", "SELL"}:
            raise ValueError("signal must be BUY or SELL")

        record = ExecutionTimingRecord(
            symbol=self.symbol,
            signal=signal,
            signal_timestamp_ns=int(signal_timestamp_ns),
            signal_close=float(signal_close),
        )
        self.records.append(record)
        return len(self.records) - 1

    def plan_next_bar(self, record_id: int, next_bar_timestamp_ns: int) -> None:
        record = self.records[record_id]
        next_ts = int(next_bar_timestamp_ns)

        if next_ts <= record.signal_timestamp_ns:
            raise ValueError(
                "Planned execution timestamp must be later than signal timestamp"
            )

        record.planned_execution_timestamp_ns = next_ts
        record.status = "NEXT_BAR_PLANNED"

    def record_fill(
        self,
        record_id: int,
        fill_timestamp_ns: int,
        fill_price: float,
    ) -> None:
        record = self.records[record_id]
        fill_ts = int(fill_timestamp_ns)

        if record.planned_execution_timestamp_ns is None:
            record.status = "FILL_WITHOUT_NEXT_BAR_PLAN"
        elif fill_ts < record.planned_execution_timestamp_ns:
            record.status = "FILL_BEFORE_PLANNED_BAR"
        else:
            record.status = "FILL_RECORDED"

        record.fill_timestamp_ns = fill_ts
        record.fill_price = float(fill_price)

    def export_json(self, output_dir: str | Path) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        stamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"execution_timing_{stamp}.json"

        payload = {
            "symbol": self.symbol,
            "record_count": len(self.records),
            "records": [asdict(record) for record in self.records],
            "warning": (
                "Audit records only; this module does not control the "
                "NautilusTrader matching engine or guarantee next-bar fills."
            ),
        }
        output_path.write_text(json.dumps(payload, indent=2))
        return output_path
