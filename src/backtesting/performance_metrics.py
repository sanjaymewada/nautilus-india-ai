"""Performance metrics for completed trades and realized equity curves.

Input P&L values must represent completed trades, preferably net of costs.
This module does not generate trading signals or place orders.
"""

from pathlib import Path
import json
import time


def calculate_metrics(
    trade_pnls: list[float],
    starting_equity: float = 1_000_000.0,
) -> dict:
    pnls = [float(value) for value in trade_pnls]
    equity = float(starting_equity)

    if equity <= 0:
        raise ValueError("starting_equity must be positive")

    if any(not (value == value and abs(value) != float("inf")) for value in pnls):
        raise ValueError("trade P&L values must be finite numbers")

    wins = [value for value in pnls if value > 0]
    losses = [value for value in pnls if value < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    equity_curve = [equity]
    peak_equity = equity
    max_drawdown = 0.0
    max_drawdown_pct = 0.0

    current_win_streak = 0
    current_loss_streak = 0
    max_win_streak = 0
    max_loss_streak = 0

    for pnl in pnls:
        equity += pnl
        equity_curve.append(equity)

        peak_equity = max(peak_equity, equity)
        drawdown = peak_equity - equity
        drawdown_pct = drawdown / peak_equity if peak_equity > 0 else 0.0

        max_drawdown = max(max_drawdown, drawdown)
        max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)

        if pnl > 0:
            current_win_streak += 1
            current_loss_streak = 0
        elif pnl < 0:
            current_loss_streak += 1
            current_win_streak = 0
        else:
            current_win_streak = 0
            current_loss_streak = 0

        max_win_streak = max(max_win_streak, current_win_streak)
        max_loss_streak = max(max_loss_streak, current_loss_streak)

    count = len(pnls)
    win_rate = len(wins) / count if count else 0.0
    average_win = sum(wins) / len(wins) if wins else 0.0
    average_loss = sum(losses) / len(losses) if losses else 0.0
    expectancy = sum(pnls) / count if count else 0.0

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = None
    else:
        profit_factor = 0.0

    return {
        "completed_trades": count,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "breakeven_trades": count - len(wins) - len(losses),
        "win_rate": win_rate,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "net_pnl": sum(pnls),
        "average_win": average_win,
        "average_loss": average_loss,
        "expectancy_per_trade": expectancy,
        "profit_factor": profit_factor,
        "starting_equity": float(starting_equity),
        "ending_equity": equity,
        "max_drawdown": max_drawdown,
        "max_drawdown_pct": max_drawdown_pct,
        "max_consecutive_wins": max_win_streak,
        "max_consecutive_losses": max_loss_streak,
        "equity_curve": equity_curve,
        "pnl_input_cost_basis": "unspecified; caller must document gross or net",
    }


def export_metrics(
    metrics: dict,
    output_dir: str | Path,
    label: str = "strategy",
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"{label}_metrics_{stamp}.json"
    output_path.write_text(json.dumps(metrics, indent=2, allow_nan=False))
    return output_path
