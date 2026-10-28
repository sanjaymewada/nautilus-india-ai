from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "market"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def fetch_yahoo(symbol, period, interval):
    import yfinance as yf
    ticker = symbol.strip().upper()
    if not ticker:
        raise ValueError("Enter a valid symbol, e.g. RELIANCE.NS")
    frame = yf.download(
        ticker, period=period, interval=interval,
        auto_adjust=True, progress=False, threads=False
    )
    if frame is None or frame.empty:
        raise ValueError("No data returned. Check symbol, interval, period and connection.")
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    frame.columns = [str(c).strip().lower().replace(" ", "_") for c in frame.columns]
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Required OHLCV fields missing: {sorted(missing)}")
    frame = frame[["open", "high", "low", "close", "volume"]].copy()
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    frame = frame.dropna(subset=["open", "high", "low", "close"])
    if frame.empty:
        raise ValueError("No valid OHLCV rows after data validation.")
    return ticker, frame

def quality_report(frame):
    return {
        "rows": int(len(frame)),
        "duplicate_timestamps": int(frame.index.duplicated().sum()),
        "missing_values": int(frame.isna().sum().sum()),
        "invalid_ohlc": int(((frame["high"] < frame[["open","close","low"]].max(axis=1)) |
                             (frame["low"] > frame[["open","close","high"]].min(axis=1))).sum()),
        "first_timestamp": str(frame.index.min()),
        "last_timestamp": str(frame.index.max()),
    }
