import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/backtests"

decisions_file = max(OUT.glob("nautilus_sma_decisions_*.csv"), key=lambda p: p.stat().st_mtime)
fills_file = max(OUT.glob("nautilus_sma_fills_*.csv"), key=lambda p: p.stat().st_mtime)

decisions = pd.read_csv(decisions_file)
fills = pd.read_csv(fills_file)
fills["last_px"] = pd.to_numeric(fills["last_px"])
fills["last_qty"] = pd.to_numeric(fills["last_qty"])
fills["timestamp"] = pd.to_datetime(fills["ts_event"], unit="ns", utc=True)

completed = []
open_position = None

for row in fills.to_dict("records"):
    side = str(row["order_side"]).upper()
    qty = float(row["last_qty"])
    price = float(row["last_px"])

    if side == "BUY":
        if open_position is not None:
            raise ValueError("Unexpected BUY while a long position is already open.")
        open_position = {
            "entry_time": row["timestamp"].isoformat(),
            "entry_price": price,
            "quantity": qty,
        }
    elif side == "SELL":
        if open_position is None:
            raise ValueError("SELL found without a preceding BUY.")
        if qty != open_position["quantity"]:
            raise ValueError("Partial/mismatched quantities; manual audit required.")

        pnl = (price - open_position["entry_price"]) * qty
        completed.append({
            **open_position,
            "exit_time": row["timestamp"].isoformat(),
            "exit_price": price,
            "gross_pnl_inr": round(pnl, 2),
            "return_pct": round((price / open_position["entry_price"] - 1) * 100, 4),
        })
        open_position = None
    else:
        raise ValueError(f"Unexpected order side: {side}")

stamp = pd.Timestamp.now(tz="UTC").strftime("%Y%m%d_%H%M%S")
trades_path = OUT / f"trade_audit_{stamp}.csv"
summary_path = OUT / f"trade_audit_{stamp}.json"

pd.DataFrame(completed).to_csv(trades_path, index=False)

summary = {
    "source_decisions": str(decisions_file),
    "source_fills": str(fills_file),
    "signals": len(decisions),
    "fill_events": len(fills),
    "completed_round_trips": len(completed),
    "winning_completed_trades": sum(t["gross_pnl_inr"] > 0 for t in completed),
    "losing_completed_trades": sum(t["gross_pnl_inr"] < 0 for t in completed),
    "completed_gross_pnl_inr": round(sum(t["gross_pnl_inr"] for t in completed), 2),
    "open_position_at_end": open_position,
    "costs_included": False,
    "warnings": [
        "Gross PnL excludes brokerage, taxes, slippage and other costs.",
        "This ledger matches observed fill events; it does not validate execution timing.",
        "Open position is not marked to market in this report.",
    ],
    "trades_csv": str(trades_path),
}
summary_path.write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
print("\nCompleted-trade ledger saved:", trades_path)
