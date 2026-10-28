"""Versioned registry for strategy experiments.

Tracks strategy configurations and evaluation status.
It does not execute strategies or select live trades.
"""

from pathlib import Path
import json
import time


class StrategyRegistry:
    ALLOWED_STATUSES = {
        "CREATED",
        "BACKTEST_PENDING",
        "BACKTESTED",
        "WALK_FORWARD_PENDING",
        "WALK_FORWARD_PASSED",
        "REJECTED",
        "PAPER_TRADING",
    }

    def __init__(self):
        self.strategies: list[dict] = []

    def register(
        self,
        name: str,
        version: str,
        parameters: dict,
        description: str = "",
    ) -> int:
        if not name.strip() or not version.strip():
            raise ValueError("Strategy name and version are required")

        for item in self.strategies:
            if item["name"] == name and item["version"] == version:
                raise ValueError("This strategy name/version already exists")

        record = {
            "name": name,
            "version": version,
            "parameters": dict(parameters),
            "description": description,
            "status": "CREATED",
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "evaluations": [],
        }
        self.strategies.append(record)
        return len(self.strategies) - 1

    def update_status(self, strategy_id: int, status: str) -> None:
        if status not in self.ALLOWED_STATUSES:
            raise ValueError(f"Unsupported status: {status}")

        self.strategies[strategy_id]["status"] = status

    def add_evaluation(
        self,
        strategy_id: int,
        dataset_name: str,
        metrics: dict,
        notes: str = "",
    ) -> None:
        self.strategies[strategy_id]["evaluations"].append({
            "dataset_name": dataset_name,
            "metrics": dict(metrics),
            "notes": notes,
            "evaluated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        })

    def export_json(self, output_dir: str | Path) -> Path:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        stamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"strategy_registry_{stamp}.json"

        output_path.write_text(json.dumps({
            "strategy_count": len(self.strategies),
            "strategies": self.strategies,
            "warning": (
                "Registry status is user-managed metadata, not proof that "
                "a strategy is profitable or safe for live trading."
            ),
        }, indent=2, allow_nan=False))

        return output_path
