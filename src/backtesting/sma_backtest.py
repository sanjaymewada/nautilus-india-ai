"""NautilusTrader SMA crossover research backtest.

Historical simulation only. No broker connection or live orders.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data/market/INFY_1d_1y.parquet"
OUTPUT_DIR = ROOT / "results/backtests"


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path)
    df.columns = [str(c).lower() for c in df.columns]

    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {sorted(missing)}")

    if not isinstance(df.index, pd.DatetimeIndex):
        date_col = next(
            (c for c in ("timestamp", "datetime", "date") if c in df.columns),
            None,
        )
        if date_col is None:
            raise ValueError("Parquet needs a DatetimeIndex or date/timestamp column")
        df[date_col] = pd.to_datetime(df[date_col], utc=True)
        df = df.set_index(date_col)

    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")].copy()
    df = df[list(required)].apply(pd.to_numeric, errors="coerce").dropna()
    df = df[(df["close"] > 0) & (df["volume"] >= 0)]

    if len(df) < 40:
        raise ValueError(f"Not enough valid candles: {len(df)}")
    return df


def run_backtest(df: pd.DataFrame, fast: int, slow: int, fee_bps: float):
    if fast < 2 or slow <= fast:
        raise ValueError("Require 2 <= fast SMA < slow SMA")
    if fee_bps < 0:
        raise ValueError("fee_bps cannot be negative")

    data = df.copy()
    data["sma_fast"] = data["close"].rolling(fast).mean()
    data["sma_slow"] = data["close"].rolling(slow).mean()

    # Signal is calculated using today's close; position starts next candle.
    data["signal"] = (data["sma_fast"] > data["sma_slow"]).astype(int)
    data.loc[data["sma_slow"].isna(), "signal"] = 0
    data["position"] = data["signal"].shift(1).fillna(0)

    data["market_return"] = data["close"].pct_change().fillna(0)
    data["turnover"] = data["position"].diff().abs().fillna(data["position"].abs())
    data["gross_return"] = data["position"] * data["market_return"]
    data["cost_return"] = data["turnover"] * fee_bps / 10_000
    data["net_return"] = data["gross_return"] - data["cost_return"]

    # Avoid reporting warm-up period as if it were tradable.
    valid = data["sma_slow"].notna()
    test = data.loc[valid].copy()
    if test.empty:
        raise ValueError("No rows remain after SMA warm-up")

    test["equity_curve"] = (1 + test["net_return"]).cumprod()
    total_return = float(test["equity_curve"].iloc[-1] - 1)
    days = max((test.index[-1] - test.index[0]).total_seconds() / 86400, 1)
    years = days / 365.25
    cagr = (
        float(test["equity_curve"].iloc[-1] ** (1 / years) - 1)
        if years > 0 and test["equity_curve"].iloc[-1] > 0
        else None
    )
    drawdown = test["equity_curve"] / test["equity_curve"].cummax() - 1
    daily_vol = float(test["net_return"].std(ddof=1) or 0)
    sharpe = (
        float(test["net_return"].mean() / daily_vol * (252**0.5))
        if daily_vol > 0
        else None
    )

    changes = test["position"].diff().fillna(test["position"].abs())
    entries = test.index[changes > 0]
    exits = test.index[changes < 0]
    trades = []
    entry_date = None
    for date, row in test.iterrows():
        prev_pos = test.loc[date, "position"]
        # Long-only state transitions: 0 -> 1 opens; 1 -> 0 closes.
        prev_idx = test.index.get_loc(date)
        previous_pos = test["position"].iloc[prev_idx - 1] if prev_idx > 0 else 0
        if previous_pos == 0 and prev_pos == 1:
            entry_date = date
        elif previous_pos == 1 and prev_pos == 0 and entry_date is not None:
            trades.append({
                "entry_date": str(entry_date),
                "exit_date": str(date),
                "entry_close": float(test.loc[entry_date, "close"]),
                "exit_close": float(row["close"]),
                "price_return_pct": round(
                    (float(row["close"]) / float(test.loc[entry_date, "close"]) - 1) * 100,
                    4,
                ),
            })
            entry_date = None

    summary = {
        "symbol": "INFY",
        "strategy": "SMA crossover long-only",
        "fast_sma": fast,
        "slow_sma": slow,
        "fee_assumption_bps_per_position_change": fee_bps,
        "candles_loaded": int(len(df)),
        "test_candles": int(len(test)),
        "start": str(test.index[0]),
        "end": str(test.index[-1]),
        "total_return_pct": round(total_return * 100, 4),
        "cagr_pct": round(cagr * 100, 4) if cagr is not None else None,
        "max_drawdown_pct": round(float(drawdown.min()) * 100, 4),
        "sharpe_approx": round(sharpe, 4) if sharpe is not None else None,
        "closed_trades": len(trades),
        "exposure_pct": round(float(test["position"].mean()) * 100, 2),
        "note": (
            "Pandas research baseline, not yet NautilusTrader engine execution. "
            "No slippage, taxes, brokerage, or live orders. Results are not a forecast."
        ),
    }
    return summary, test, trades


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DATA_FILE)
    parser.add_argument("--fast", type=int, default=10)
    parser.add_argument("--slow", type=int, default=30)
    parser.add_argument("--fee-bps", type=float, default=5.0)
    args = parser.parse_args()

    df = load_data(args.data)
    summary, test, trades = run_backtest(df, args.fast, args.slow, args.fee_bps)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    stamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    summary_path = OUTPUT_DIR / f"sma_summary_{stamp}.json"
    trades_path = OUTPUT_DIR / f"sma_trades_{stamp}.csv"
    curve_path = OUTPUT_DIR / f"sma_equity_curve_{stamp}.csv"

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pd.DataFrame(trades).to_csv(trades_path, index=False)
    test[["close", "sma_fast", "sma_slow", "position", "net_return", "equity_curve"]].to_csv(curve_path)

    print(json.dumps(summary, indent=2))
    print("\nSaved:")
    print(summary_path)
    print(trades_path)
    print(curve_path)


if __name__ == "__main__":
    main()
