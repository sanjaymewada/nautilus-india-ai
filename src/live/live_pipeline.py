"""Connect live market events to candles, features, predictions and outcomes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.live.candle_aggregator import CandleAggregator
from src.live.alert_rules import AlertRules
from src.live.telegram_alerts import TelegramAlertSender
from src.live.event_store import LiveEventStore
from src.live.feature_engine import LiveFeatureEngine
from src.live.market_feed import MarketTick
from src.live.outcome_tracker import OutcomeTracker
from src.live.prediction_engine import LivePredictionEngine


class LivePipeline:
    """Broker-independent live processing pipeline."""

    def __init__(
        self,
        aggregator: CandleAggregator | None = None,
        feature_engine: LiveFeatureEngine | None = None,
        prediction_engine: LivePredictionEngine | None = None,
        event_store: LiveEventStore | None = None,
        outcome_tracker: OutcomeTracker | None = None,
        alert_rules: AlertRules | None = None,
        telegram_sender: TelegramAlertSender | None = None,
    ) -> None:
        self.aggregator = aggregator or CandleAggregator(interval_seconds=60)
        self.feature_engine = feature_engine or LiveFeatureEngine()
        self.prediction_engine = prediction_engine or LivePredictionEngine()
        self.event_store = event_store or LiveEventStore()
        self.outcome_tracker = outcome_tracker or OutcomeTracker()
        self.alert_rules = alert_rules or AlertRules()
        self.telegram_sender = telegram_sender or TelegramAlertSender()
        self._sent_alert_keys: set[tuple[str, int, str, str]] = set()
        self.latest_features: dict[str, dict[str, Any]] = {}
        self.latest_horizon_features: dict[str, dict[str, Any]] = {}
        self.latest_predictions: dict[str, dict[str, Any]] = {}
        self.latest_prices: dict[str, float] = {}

    def on_tick(self, tick: MarketTick) -> list[dict[str, Any]]:
        """Process one tick and return newly created prediction snapshots."""
        self.latest_prices[tick.symbol] = float(tick.last_price)

        outcomes = self.outcome_tracker.update_price(
            tick.symbol,
            float(tick.last_price),
            tick.timestamp,
        )
        for outcome in outcomes:
            self.event_store.save_outcome(outcome)

        candle = self.aggregator.update(tick)
        if candle is None:
            return []

        candle_data = candle.to_dict()
        self.event_store.save_candle(candle_data)

        features = self.feature_engine.update(candle)
        if features is None:
            return []

        self.latest_features[tick.symbol] = features
        self.latest_horizon_features[tick.symbol] = features.get("horizons", {})
        self.event_store.save_features(features)

        prediction = self.prediction_engine.predict(features)
        self.latest_predictions[tick.symbol] = prediction
        self.event_store.save_prediction(prediction)

        decision = self.alert_rules.evaluate(prediction)
        if decision["should_alert"]:
            for item in decision["qualified_predictions"]:
                alert_key = (
                    str(prediction.get("symbol")),
                    int(item["horizon_minutes"]),
                    str(item.get("direction")),
                    str(prediction.get("feature_timestamp")),
                )
                if alert_key in self._sent_alert_keys:
                    continue
                result = self.telegram_sender.send_prediction({
                    **prediction,
                    "predictions": [item],
                })
                self.event_store.append("alert_results", {
                    "symbol": prediction.get("symbol"),
                    "horizon_minutes": item.get("horizon_minutes"),
                    "decision": decision,
                    "delivery": result,
                })
                if result.get("ok"):
                    self._sent_alert_keys.add(alert_key)

        self.outcome_tracker.register_prediction(
            prediction=prediction,
            reference_price=float(candle.close),
            timestamp=candle.start_time.replace(tzinfo=timezone.utc)
            if candle.start_time.tzinfo is None
            else candle.start_time,
        )

        return [prediction]

    def snapshot(self) -> dict[str, Any]:
        """Return current in-memory state for a dashboard."""
        symbols = sorted(
            set(self.latest_prices)
            | set(self.latest_features)
            | set(self.latest_predictions)
        )
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "symbols": {
                symbol: {
                    "last_price": self.latest_prices.get(symbol),
                    "features": self.latest_features.get(symbol),
                    "horizon_features": self.latest_horizon_features.get(symbol),
                    "prediction": self.latest_predictions.get(symbol),
                }
                for symbol in symbols
            },
            "pending_outcomes": self.outcome_tracker.pending_count(),
        }
