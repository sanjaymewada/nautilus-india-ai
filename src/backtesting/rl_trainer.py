"""Tabular Q-learning trainer for offline historical-market experiments.

Actions: 0 = flat, 1 = long.
Uses historical closes only. No live trading or broker connection.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


class QLearningConfig:
    def __init__(
        self,
        episodes: int = 300,
        learning_rate: float = 0.1,
        discount_factor: float = 0.95,
        epsilon_start: float = 1.0,
        epsilon_min: float = 0.05,
        epsilon_decay: float = 0.99,
        transaction_cost_bps: float = 10.0,
        random_seed: int = 42,
    ) -> None:
        self.episodes = episodes
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon_start = epsilon_start
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.transaction_cost_bps = transaction_cost_bps
        self.random_seed = random_seed


class QLearningTrainer:
    """Learn a small long/flat policy from discretized historical features."""

    ACTIONS = ("FLAT", "LONG")

    def __init__(self, config: QLearningConfig | None = None) -> None:
        self.config = config or QLearningConfig()
        self.q_table = np.zeros((3 * 3 * 2, len(self.ACTIONS)), dtype=float)
        self.training_rewards: list[float] = []
        self.rng = np.random.default_rng(self.config.random_seed)

    @staticmethod
    def _prepare(data: pd.DataFrame) -> pd.DataFrame:
        frame = data.copy()

        if "close" not in frame.columns:
            matches = [c for c in frame.columns if str(c).lower() == "close"]
            if not matches:
                raise ValueError("Input data must contain a 'close' column")
            frame = frame.rename(columns={matches[0]: "close"})

        frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
        frame = frame.dropna(subset=["close"])
        frame = frame[frame["close"] > 0].copy()

        if len(frame) < 35:
            raise ValueError("At least 35 valid closing prices are required")

        frame["return_1"] = frame["close"].pct_change()
        frame["sma_10"] = frame["close"].rolling(10).mean()
        frame["sma_30"] = frame["close"].rolling(30).mean()
        frame["momentum"] = frame["close"].pct_change(5)
        frame = frame.dropna().reset_index(drop=True)

        if len(frame) < 2:
            raise ValueError("Not enough usable rows after feature preparation")

        return frame

    @staticmethod
    def _state(row: pd.Series, position: int) -> int:
        if row["sma_10"] > row["sma_30"] * 1.001:
            trend = 2
        elif row["sma_10"] < row["sma_30"] * 0.999:
            trend = 0
        else:
            trend = 1

        momentum = float(row["momentum"])
        if momentum > 0.005:
            momentum_state = 2
        elif momentum < -0.005:
            momentum_state = 0
        else:
            momentum_state = 1

        return trend * 6 + momentum_state * 2 + int(position)

    def train(self, data: pd.DataFrame) -> dict[str, Any]:
        frame = self._prepare(data)
        cost_rate = self.config.transaction_cost_bps / 10_000.0
        epsilon = self.config.epsilon_start
        rewards: list[float] = []

        # Episodes replay the same historical sequence in different
        # exploration orders. This is a research baseline, not live adaptation.
        for _ in range(self.config.episodes):
            position = 0
            total_reward = 0.0

            for i in range(len(frame) - 1):
                row = frame.iloc[i]
                next_row = frame.iloc[i + 1]
                state = self._state(row, position)

                if self.rng.random() < epsilon:
                    action = int(self.rng.integers(0, 2))
                else:
                    action = int(np.argmax(self.q_table[state]))

                next_position = action
                next_state = self._state(next_row, next_position)

                # Action is chosen from features available at row i.
                # Reward is the next close-to-close return for the held position.
                market_return = float(next_row["close"] / row["close"] - 1.0)
                turnover = abs(next_position - position)
                reward = (
                    next_position * market_return
                    - turnover * cost_rate
                )

                old_q = self.q_table[state, action]
                future_q = float(np.max(self.q_table[next_state]))
                target = reward + self.config.discount_factor * future_q
                self.q_table[state, action] = old_q + self.config.learning_rate * (
                    target - old_q
                )

                total_reward += reward
                position = next_position

            rewards.append(total_reward)
            epsilon = max(
                self.config.epsilon_min,
                epsilon * self.config.epsilon_decay,
            )

        self.training_rewards = rewards

        return {
            "algorithm": "tabular_q_learning",
            "episodes": self.config.episodes,
            "training_rows": len(frame),
            "state_count": int(self.q_table.shape[0]),
            "actions": list(self.ACTIONS),
            "transaction_cost_bps": self.config.transaction_cost_bps,
            "first_episode_reward": rewards[0],
            "last_episode_reward": rewards[-1],
            "best_episode_reward": max(rewards),
            "q_table": self.q_table.tolist(),
            "training_rewards": rewards,
            "limitations": [
                "Training rewards are in fractional-return units, not rupees.",
                "Episodes reuse the same historical data and are not independent samples.",
                "No separate out-of-sample evaluation is performed by train().",
                "Execution price, slippage, taxes, position sizing, and risk limits "
                "need fuller modelling before strategy comparisons.",
                "This is not a live-trading system.",
            ],
        }

    @staticmethod
    def export_json(
        report: dict[str, Any],
        path: str | Path = "data/research/rl_training_report.json",
    ) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2, allow_nan=False),
            encoding="utf-8",
        )
        return output_path
