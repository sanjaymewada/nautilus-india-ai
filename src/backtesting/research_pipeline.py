"""Central research pipeline for backtesting support modules.

This module coordinates metrics, market-regime labels, walk-forward splits,
strategy registry records, and learning-dataset exports. It does not place
orders or modify the existing NautilusTrader backtest engine.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.backtesting.learning_dataset import LearningDataset
from src.backtesting.market_regime import classify_market_regime
from src.backtesting.performance_metrics import calculate_metrics
from src.backtesting.strategy_registry import StrategyRegistry
from src.backtesting.walk_forward import (
    WalkForwardConfig,
    create_walk_forward_splits,
)


class ResearchPipeline:
    """Coordinate research artifacts from historical candles and trade records."""

    def __init__(
        self,
        output_dir: str | Path = "data/research",
        strategy_name: str = "sma_10_30",
        strategy_version: str = "1.0",
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.strategy_name = strategy_name
        self.strategy_version = strategy_version
        self.dataset = LearningDataset()
        self.registry = StrategyRegistry()

    @staticmethod
    def _write_json(path: Path, payload: Any) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, default=str, allow_nan=False),
            encoding="utf-8",
        )
        return path

    def run(
        self,
        candles: pd.DataFrame,
        trades: list[dict[str, Any]] | None = None,
        timestamp_col: str = "timestamp",
        starting_equity: float = 1_000_000,
        walk_forward_config: WalkForwardConfig | None = None,
    ) -> dict[str, Any]:
        """Generate research outputs without running or placing trades."""
        if candles.empty:
            raise ValueError("candles DataFrame is empty")

        trades = trades or []
        frame = candles.copy()

        if timestamp_col not in frame.columns:
            if isinstance(frame.index, pd.DatetimeIndex):
                frame = frame.reset_index()
                frame = frame.rename(columns={frame.columns[0]: timestamp_col})
            else:
                raise ValueError(
                    f"Missing '{timestamp_col}' column and no DatetimeIndex found"
                )

        frame[timestamp_col] = pd.to_datetime(frame[timestamp_col], errors="coerce")
        frame = frame.dropna(subset=[timestamp_col]).sort_values(timestamp_col)

        if frame.empty:
            raise ValueError("No valid candle timestamps found")

        # Basic candle-based regime classification.
        regime_report = classify_market_regime(frame)
        regime_path = self._write_json(
            self.output_dir / "market_regime.json",
            regime_report,
        )

        # Metrics use net_pnl when present; otherwise gross_pnl.
        pnls: list[float] = []
        for trade in trades:
            value = trade.get("net_pnl", trade.get("gross_pnl"))
            if value is not None:
                pnls.append(float(value))

        metrics = calculate_metrics(
            trade_pnls=pnls,
            starting_equity=starting_equity,
        )
        metrics_path = self._write_json(
            self.output_dir / "performance_metrics.json",
            metrics,
        )

        # Save supplied completed-trade records for later model training/review.
        for trade in trades:
            record = dict(trade)
            record.setdefault("strategy", self.strategy_name)
            self.dataset.add_trade(record)

        dataset_path = self.dataset.export_json(
            self.output_dir / "learning_dataset.json"
        )

        # Register this research run. This is metadata, not a strategy approval.
        self.registry.register_strategy(
            name=self.strategy_name,
            version=self.strategy_version,
            parameters={},
            description="Historical research pipeline run",
        )
        registry_path = self.registry.export_json(
            self.output_dir / "strategy_registry.json"
        )

        # Create time-ordered train/test windows for later out-of-sample testing.
        config = walk_forward_config or WalkForwardConfig()
        splits = create_walk_forward_splits(
            frame,
            timestamp_col=timestamp_col,
            config=config,
        )
        split_summary = [
            {
                "split": index + 1,
                "train_rows": len(train),
                "test_rows": len(test),
                "train_start": str(train[timestamp_col].min()),
                "train_end": str(train[timestamp_col].max()),
                "test_start": str(test[timestamp_col].min()),
                "test_end": str(test[timestamp_col].max()),
            }
            for index, (train, test) in enumerate(splits)
        ]
        splits_path = self._write_json(
            self.output_dir / "walk_forward_splits.json",
            split_summary,
        )

        summary = {
            "strategy": self.strategy_name,
            "strategy_version": self.strategy_version,
            "candle_rows": len(frame),
            "trade_records": len(trades),
            "metrics_trade_count": len(pnls),
            "walk_forward_split_count": len(split_summary),
            "outputs": {
                "market_regime": str(regime_path),
                "performance_metrics": str(metrics_path),
                "learning_dataset": str(dataset_path),
                "strategy_registry": str(registry_path),
                "walk_forward_splits": str(splits_path),
            },
            "notes": [
                "Research artifacts only; no live orders are placed.",
                "Walk-forward windows are created but strategies are not yet re-run inside each window.",
                "Metrics depend on the supplied trade records and are not independently reconciled with NautilusTrader engine output.",
            ],
        }

        summary_path = self._write_json(
            self.output_dir / "research_summary.json",
            summary,
        )
        summary["outputs"]["research_summary"] = str(summary_path)
        return summary
