import json
import time
import traceback
from pathlib import Path

import pandas as pd

from nautilus_trader.backtest import BacktestEngine, BacktestEngineConfig
from decimal import Decimal
from nautilus_trader.execution import MakerTakerFeeModel
from nautilus_trader.trading import Strategy, StrategyConfig
from nautilus_trader.model import (
    AccountType, Bar, BarAggregation, BarSpecification, BarType,
    Currency, Equity, InstrumentId, Money, OmsType, OrderSide,
    Price, PriceType, Quantity, Symbol, TimeInForce, Venue,
)

ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data/market/INFY_1d_1y.parquet"
OUT_DIR = ROOT / "results/backtests"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FAST = 10
SLOW = 30
ORDER_QTY = 1
STARTING_CASH = 1_000_000


def load_bars(instrument_id, bar_type):
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Historical data not found: {DATA_FILE}")

    df = pd.read_parquet(DATA_FILE).copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Support timestamp stored either as a column or as the index.
    time_col = next(
        (c for c in ("timestamp", "datetime", "date", "time", "ts_event")
         if c in df.columns),
        None,
    )
    if time_col:
        timestamps = pd.to_datetime(df.pop(time_col), utc=True)
    else:
        timestamps = pd.to_datetime(df.index, utc=True)

    required = ("open", "high", "low", "close", "volume")
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing columns {missing}; available columns: {list(df.columns)}"
        )

    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["timestamp"] = timestamps
    df = df.dropna(subset=["timestamp", *required])
    df = df.sort_values("timestamp").drop_duplicates("timestamp")
    df = df[
        (df["open"] > 0) & (df["high"] > 0) &
        (df["low"] > 0) & (df["close"] > 0) & (df["volume"] >= 0)
    ]
    df = df[
        (df["high"] >= df[["open", "close", "low"]].max(axis=1)) &
        (df["low"] <= df[["open", "close", "high"]].min(axis=1))
    ]

    bars = []
    for row in df.itertuples(index=False):
        values = row._asdict()
        ts = int(pd.Timestamp(values["timestamp"]).value)
        bars.append(
            Bar(
                bar_type,
                Price(float(values["open"]), 2),
                Price(float(values["high"]), 2),
                Price(float(values["low"]), 2),
                Price(float(values["close"]), 2),
                Quantity(float(values["volume"]), 0),
                ts,
                ts,
            )
        )

    if len(bars) <= SLOW:
        raise ValueError(f"Need more than {SLOW} valid candles; found {len(bars)}")

    return bars



class SmaCrossConfig(StrategyConfig):
    def __init__(self, instrument_id, bar_type):
        super().__init__()
        object.__setattr__(self, "instrument_id", instrument_id)
        object.__setattr__(self, "bar_type", bar_type)


class SmaCrossStrategy(Strategy):
    def __init__(self, config: SmaCrossConfig):
        super().__init__(config)
        self.instrument_id = config.instrument_id
        self.bar_type = config.bar_type
        self.closes = []
        self.in_position = False
        self.decisions = []
        self.fills = []

    def on_start(self):
        self.subscribe_bars(self.bar_type)

    def on_bar(self, bar):
        close = float(bar.close)
        self.closes.append(close)

        if len(self.closes) < SLOW:
            return

        fast_now = sum(self.closes[-FAST:]) / FAST
        slow_now = sum(self.closes[-SLOW:]) / SLOW
        previous = self.closes[:-1]

        fast_prev = sum(previous[-FAST:]) / FAST
        slow_prev = sum(previous[-SLOW:]) / SLOW

        signal = None
        if fast_prev <= slow_prev and fast_now > slow_now and not self.in_position:
            signal = "BUY"
        elif fast_prev >= slow_prev and fast_now < slow_now and self.in_position:
            signal = "SELL"

        if signal is None:
            return

        self.decisions.append({
            "timestamp_ns": int(bar.ts_event),
            "close": close,
            "fast_sma": fast_now,
            "slow_sma": slow_now,
            "signal": signal,
        })

        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.BUY if signal == "BUY" else OrderSide.SELL,
            quantity=Quantity(ORDER_QTY, 0),
            time_in_force=TimeInForce.DAY,
        )
        self.submit_order(order)
        self.in_position = signal == "BUY"

    def on_order_filled(self, event):
        self.fills.append({
            "instrument_id": str(event.instrument_id),
            "order_side": str(event.order_side),
            "last_qty": str(event.last_qty),
            "last_px": str(event.last_px),
            "ts_event": int(event.ts_event),
        })


def main():
    stamp = time.strftime("%Y%m%d_%H%M%S")
    venue = Venue("SIM")
    instrument_id = InstrumentId(Symbol("INFY"), venue)
    currency = Currency.from_str("INR")
    bar_type = BarType(
        instrument_id,
        BarSpecification(1, BarAggregation.DAY, PriceType.LAST),
    )

    bars = load_bars(instrument_id, bar_type)
    instrument = Equity(
        instrument_id=instrument_id,
        raw_symbol=Symbol("INFY"),
        currency=currency,
        price_precision=2,
        price_increment=Price(0.01, 2),
        ts_event=0,
        ts_init=0,
    )

    engine = BacktestEngine(config=BacktestEngineConfig())
    strategy = SmaCrossStrategy(SmaCrossConfig(instrument_id=instrument_id, bar_type=bar_type))

    try:
        engine.add_venue(
            venue=venue,
            oms_type=OmsType.NETTING,
            account_type=AccountType.CASH,
            starting_balances=[Money(STARTING_CASH, currency)],
            fee_model=MakerTakerFeeModel(maker_rate=Decimal("0"), taker_rate=Decimal("0")),
        )
        engine.add_instrument(instrument)
        engine.add_data(bars)
        engine.add_strategy(strategy)
        engine.run()

        decisions_path = OUT_DIR / f"nautilus_sma_decisions_{stamp}.csv"
        fills_path = OUT_DIR / f"nautilus_sma_fills_{stamp}.csv"
        summary_path = OUT_DIR / f"nautilus_sma_summary_{stamp}.json"

        pd.DataFrame(strategy.decisions).to_csv(decisions_path, index=False)
        pd.DataFrame(strategy.fills).to_csv(fills_path, index=False)

        summary = {
            "engine": "NautilusTrader",
            "symbol": "INFY",
            "strategy": "SMA crossover long-only",
            "fast_sma": FAST,
            "slow_sma": SLOW,
            "order_quantity": ORDER_QTY,
            "starting_cash_inr": STARTING_CASH,
            "historical_candles_loaded": len(bars),
            "signals_generated": len(strategy.decisions),
            "fill_events_observed": len(strategy.fills),
            "data_file": str(DATA_FILE),
            "decisions_file": str(decisions_path),
            "fills_file": str(fills_path),
            "caveats": [
                "Initial engine integration test; not a validated trading strategy.",
                "No brokerage, taxes, slippage, or realistic market impact configured.",
                "Signal state is simplified and is not yet reconciled against actual positions.",
                "No live broker connection or live orders.",
            ],
        }
        summary_path.write_text(json.dumps(summary, indent=2))
        print(json.dumps(summary, indent=2))
        print("\nNAUTILUS BACKTEST RUN COMPLETED")
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
