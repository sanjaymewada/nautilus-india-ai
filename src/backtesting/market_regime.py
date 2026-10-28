"""Rule-based market regime labels for historical OHLCV data.

This is a descriptive research helper, not a predictive model.
It does not submit orders or modify strategies.
"""

from pathlib import Path
import json
import time

import pandas as pd


def classify_market_regime(
    df: pd.DataFrame,
    close_col: str = "close",
    high_col: str = "high",
    low_col: str = "low",
    trend_window: int = 20,
    volatility_window: int = 20,
    high_volatility_threshold: float = 0.025,
    trend_threshold: float = 0.03,
) -> pd.DataFrame:
    if trend_window < 2 or volatility_window < 2:
        raise ValueError("Windows must be at least 2")
    if high_volatility_threshold <= 0 or trend_threshold < 0:
        raise ValueError("Thresholds must be positive (trend may be zero)")

    required = {close_col, high_col, low_col}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    result = df.copy()
    close = pd.to_numeric(result[close_col], errors="coerce")
    high = pd.to_numeric(result[high_col], errors="coerce")
    low = pd.to_numeric(result[low_col], errors="coerce")

    if (close.dropna() <= 0).any():
        raise ValueError("Close prices must be positive")

    returns = close.pct_change()
    result["regime_return_volatility"] = returns.rolling(
        volatility_window, min_periods=volatility_window
    ).std()

    rolling_high = high.rolling(
        trend_window, min_periods=trend_window
    ).max()
    rolling_low = low.rolling(
        trend_window, min_periods=trend_window
    ).min()

    result["regime_trend_strength"] = (
        rolling_high - rolling_low
    ) / close

    regimes = []
    for vol, strength, current_close, previous_close in zip(
        result["regime_return_volatility"],
        result["regime_trend_strength"],
        close,
        close.shift(trend_window),
    ):
        if pd.isna(vol) or pd.isna(strength) or pd.isna(previous_close):
            regimes.append("INSUFFICIENT_DATA")
        elif vol >= high_volatility_threshold:
            regimes.append("HIGH_VOLATILITY")
        elif strength < trend_threshold:
            regimes.append("SIDEWAYS")
        elif current_close > previous_close:
            regimes.append("TRENDING_UP")
        elif current_close < previous_close:
            regimes.append("TRENDING_DOWN")
        else:
            regimes.append("SIDEWAYS")

    result["market_regime"] = regimes
    return result


def export_regime_report(
    df: pd.DataFrame,
    output_dir: str | Path,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stamp = time.strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"market_regime_{stamp}.json"

    counts = (
        df["market_regime"].value_counts(dropna=False).to_dict()
        if "market_regime" in df.columns
        else {}
    )

    payload = {
        "rows": len(df),
        "regime_counts": counts,
        "records": json.loads(df.to_json(orient="records", date_format="iso")),
        "warning": (
            "Rule-based descriptive labels only. Thresholds need calibration; "
            "this report does not establish predictive value."
        ),
    }

    output_path.write_text(json.dumps(payload, indent=2, allow_nan=False))
    return output_path
