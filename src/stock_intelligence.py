"""Stock intelligence helpers built around Yahoo Finance historical data."""
from __future__ import annotations

import math
import pandas as pd


def resolve_symbol(query: str) -> tuple[str, list[dict]]:
    import yfinance as yf

    q = query.strip()
    if not q:
        raise ValueError("Enter a ticker or company name.")
    if "." in q and " " not in q:
        return q.upper(), []
    if " " not in q and q.replace("-", "").isalnum():
        return q.upper() + ".NS", []

    search = yf.Search(q, max_results=10)
    quotes = getattr(search, "quotes", []) or []
    candidates = []
    for item in quotes:
        symbol = item.get("symbol")
        if not symbol:
            continue
        exchange = str(item.get("exchange", "")).upper()
        name = item.get("shortname") or item.get("longname") or symbol
        candidates.append({"symbol": symbol, "name": name, "exchange": exchange})
    indian = [
        x for x in candidates
        if x["symbol"].upper().endswith((".NS", ".BO"))
        or x["exchange"] in {"NSI", "BSE", "NSE"}
    ]
    if indian:
        candidates = indian
    if not candidates:
        raise ValueError("No matching company found. Try RELIANCE.NS or TCS.NS.")
    return candidates[0]["symbol"], candidates


def fetch_profile(symbol: str) -> dict:
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    result = {"info": {}, "annual": pd.DataFrame(), "quarterly": pd.DataFrame(), "holders": {}}
    try:
        result["info"] = ticker.info or {}
    except Exception as exc:
        result["info_error"] = str(exc)

    for key, attr in [
        ("annual", "financials"),
        ("quarterly", "quarterly_financials"),
        ("balance_sheet", "balance_sheet"),
        ("cash_flow", "cashflow"),
        ("quarterly_balance_sheet", "quarterly_balance_sheet"),
        ("quarterly_cash_flow", "quarterly_cashflow"),
    ]:
        try:
            value = getattr(ticker, attr)
            result[key] = value if isinstance(value, pd.DataFrame) else pd.DataFrame()
        except Exception as exc:
            result[key] = pd.DataFrame()
            result[f"{key}_error"] = str(exc)

    for key, attr in [
        ("major_holders", "major_holders"),
        ("institutional_holders", "institutional_holders"),
        ("mutualfund_holders", "mutualfund_holders"),
    ]:
        try:
            value = getattr(ticker, attr)
            result["holders"][key] = value if isinstance(value, pd.DataFrame) else pd.DataFrame()
        except Exception:
            result["holders"][key] = pd.DataFrame()

    try:
        result["dividends"] = ticker.dividends
    except Exception:
        result["dividends"] = pd.Series(dtype=float)
    return result


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    """Add indicators without mutating the caller's historical OHLCV frame."""
    if frame is None or frame.empty:
        raise ValueError("Cannot calculate indicators: no OHLCV candles were supplied.")
    required = {"open", "high", "low", "close", "volume"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Cannot calculate indicators; missing columns: {sorted(missing)}")

    df = frame.copy().sort_index()
    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"])
    if df.empty:
        raise ValueError("No valid OHLC candles remain after data validation.")

    close, high, low = df["close"], df["high"], df["low"]
    volume = df["volume"].fillna(0).clip(lower=0)

    for period in (9, 20, 21, 50, 100, 200):
        df[f"ema_{period}"] = close.ewm(span=period, adjust=False, min_periods=period).mean()
    for period in (20, 50, 200):
        df[f"sma_{period}"] = close.rolling(period, min_periods=period).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    df["rsi_14"] = 100 - (100 / (1 + rs))
    df.loc[(loss == 0) & (gain > 0), "rsi_14"] = 100
    df.loc[(gain == 0) & (loss > 0), "rsi_14"] = 0
    df.loc[(gain == 0) & (loss == 0), "rsi_14"] = 50

    ema12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
    ema26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False, min_periods=9).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    previous_close = close.shift(1)
    true_range = pd.concat([
        high - low,
        (high - previous_close).abs(),
        (low - previous_close).abs(),
    ], axis=1).max(axis=1)
    df["atr_14"] = true_range.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    df["atr_pct"] = (df["atr_14"] / close.replace(0, float("nan"))) * 100

    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    atr = df["atr_14"].replace(0, float("nan"))
    plus_di = 100 * plus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean() / atr
    di_sum = (plus_di + minus_di).replace(0, float("nan"))
    dx = 100 * (plus_di - minus_di).abs() / di_sum
    df["plus_di_14"] = plus_di
    df["minus_di_14"] = minus_di
    df["adx_14"] = dx.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()

    typical = (high + low + close) / 3
    weighted = typical * volume
    cumulative_volume = volume.cumsum().replace(0, float("nan"))
    df["vwap_loaded_window"] = weighted.cumsum() / cumulative_volume
    # A session VWAP is meaningful only when the index represents intraday candles.
    # Group by each index date; daily candles will simply have one observation per session.
    try:
        session_key = pd.Index(df.index.date)
        session_weighted = weighted.groupby(session_key).cumsum()
        session_volume = volume.groupby(session_key).cumsum().replace(0, float("nan"))
        df["vwap_session"] = session_weighted / session_volume
    except (AttributeError, TypeError):
        df["vwap_session"] = float("nan")

    df["volume_avg_20"] = volume.rolling(20, min_periods=20).mean()
    df["volume_ratio_20"] = volume / df["volume_avg_20"].replace(0, float("nan"))
    df["previous_high"] = high.shift(1)
    df["previous_low"] = low.shift(1)
    df["rolling_support_20"] = low.rolling(20, min_periods=20).min()
    df["rolling_resistance_20"] = high.rolling(20, min_periods=20).max()
    df["return_pct"] = close.pct_change() * 100
    return df


def fmt(value, suffix="", divisor=1.0) -> str:
    try:
        n = float(value) / divisor
        if not math.isfinite(n):
            return "N/A"
        return f"{n:,.2f}{suffix}"
    except (TypeError, ValueError, ZeroDivisionError):
        return "N/A"


def market_cap_label(value) -> str:
    try:
        n = float(value)
        if not math.isfinite(n):
            return "N/A"
        if n >= 1e12:
            return f"₹{n / 1e12:,.2f} lakh cr"
        if n >= 1e7:
            return f"₹{n / 1e7:,.2f} cr"
        return f"₹{n:,.0f}"
    except (TypeError, ValueError):
        return "N/A"



# ============================================================
# NAUTILUS QUANT + ALGO ENGINE
# Historical analysis only. No order execution or backtesting.
# ============================================================

import math
import pandas as pd
import numpy as np


def _num(value):
    """Convert a value to a finite float, otherwise None."""
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def quant_engine(frame, benchmark=None):
    """
    Descriptive quantitative analysis of historical OHLCV data.

    Returns:
      - Returns and volatility
      - Drawdown
      - Momentum and price z-score
      - Benchmark correlation and beta
      - Descriptive market-regime classification

    IMPORTANT: These are historical statistics, not predictions.
    """

    if frame is None or frame.empty or "close" not in frame.columns:
        return {"status": "INSUFFICIENT_DATA",
                "reason": "Close-price data unavailable."}

    close = pd.to_numeric(frame["close"], errors="coerce").dropna()

    if len(close) < 30:
        return {
            "status": "INSUFFICIENT_DATA",
            "reason": f"Need 30 valid closes; found {len(close)}."
        }

    returns = close.pct_change().dropna()

    def return_over_bars(bars):
        if len(close) <= bars:
            return None
        return _num((close.iloc[-1] / close.iloc[-bars - 1] - 1) * 100)

    # Do not annualize intraday data with daily assumptions.
    try:
        interval = pd.Series(frame.index).diff().dropna().median()
        is_intraday = interval < pd.Timedelta(days=1)
    except Exception:
        is_intraday = False

    if is_intraday:
        # Approximate Indian regular-session bars per year.
        annualization = 252 * 75
        annualization_note = "Intraday annualization approximation"
    else:
        annualization = 252
        annualization_note = "Daily-bar annualization approximation"

    recent_returns = returns.tail(60)
    vol = None
    sharpe_like = None

    if len(recent_returns) >= 10:
        std = recent_returns.std(ddof=1)
        if pd.notna(std) and std > 0:
            vol = _num(std * math.sqrt(annualization) * 100)
            sharpe_like = _num(
                recent_returns.mean() / std * math.sqrt(annualization)
            )

    negative_returns = recent_returns[recent_returns < 0]
    downside_vol = None

    if len(negative_returns) >= 5:
        downside_vol = _num(
            negative_returns.std(ddof=1)
            * math.sqrt(annualization) * 100
        )

    drawdown = close / close.cummax() - 1
    max_drawdown = _num(drawdown.min() * 100)

    last = frame.iloc[-1]

    current_close = _num(last.get("close"))
    ema20 = _num(last.get("ema_20"))
    ema50 = _num(last.get("ema_50"))
    sma200 = _num(last.get("sma_200"))
    rsi = _num(last.get("rsi_14"))
    adx = _num(last.get("adx_14"))
    atr = _num(last.get("atr_14"))
    volume_ratio = _num(last.get("volume_ratio_20"))

    atr_pct = None
    if current_close and atr is not None:
        atr_pct = _num(atr / current_close * 100)

    zscore20 = None
    if len(close) >= 20:
        mean20 = close.rolling(20).mean().iloc[-1]
        std20 = close.rolling(20).std(ddof=1).iloc[-1]

        if pd.notna(std20) and std20 > 0:
            zscore20 = _num((close.iloc[-1] - mean20) / std20)

    # Benchmark comparison only if timestamps can be aligned.
    beta = correlation = relative_return_pct = None

    if (
        benchmark is not None
        and not benchmark.empty
        and "close" in benchmark.columns
    ):
        stock_returns = pd.to_numeric(
            frame["close"], errors="coerce"
        ).pct_change()

        benchmark_returns = pd.to_numeric(
            benchmark["close"], errors="coerce"
        ).pct_change()

        aligned = pd.concat(
            [
                stock_returns.rename("stock"),
                benchmark_returns.rename("benchmark")
            ],
            axis=1
        ).dropna()

        if len(aligned) >= 30:
            benchmark_variance = aligned["benchmark"].var(ddof=1)

            if (
                pd.notna(benchmark_variance)
                and benchmark_variance > 0
            ):
                beta = _num(
                    aligned["stock"].cov(aligned["benchmark"])
                    / benchmark_variance
                )
                correlation = _num(
                    aligned["stock"].corr(aligned["benchmark"])
                )

            # Compare returns only over the aligned observations.
            stock_growth = (1 + aligned["stock"]).prod()
            benchmark_growth = (1 + aligned["benchmark"]).prod()

            relative_return_pct = _num(
                (stock_growth - benchmark_growth) * 100
            )

    if adx is not None and adx >= 25:
        regime = "TRENDING_REGIME_HEURISTIC"
    elif adx is not None and adx < 18:
        regime = "WEAK_TREND_OR_RANGE_HEURISTIC"
    elif atr_pct is not None and atr_pct >= 3:
        regime = "HIGH_VOLATILITY_HEURISTIC"
    else:
        regime = "MIXED_OR_UNCLASSIFIED"

    return {
        "status": "OK",
        "observations": int(len(close)),
        "last_close": current_close,
        "return_5_bars_pct": return_over_bars(5),
        "return_20_bars_pct": return_over_bars(20),
        "return_60_bars_pct": return_over_bars(60),
        "return_120_bars_pct": return_over_bars(120),
        "annualized_volatility_pct_approx": vol,
        "downside_volatility_pct_approx": downside_vol,
        "sharpe_like_ratio": sharpe_like,
        "max_drawdown_pct_loaded_history": max_drawdown,
        "atr_pct": atr_pct,
        "price_zscore_20": zscore20,
        "rsi_14": rsi,
        "adx_14": adx,
        "relative_volume_20": volume_ratio,
        "beta_vs_benchmark": beta,
        "correlation_vs_benchmark": correlation,
        "relative_return_vs_benchmark_pct": relative_return_pct,
        "regime_heuristic": regime,
        "annualization_note": annualization_note,
        "warning": (
            "Historical descriptive statistics only. "
            "Not a forecast, backtest, or validated trading edge."
        )
    }


def algo_engine(frame):
    """
    Transparent deterministic rule ensemble.

    Modules:
      1. Trend-following
      2. Prior-range breakout + relative volume
      3. Momentum confirmation
      4. Mean-reversion candidate in weak-trend regimes

    Rules produce research classifications, not proven trade signals.
    """

    if frame is None or frame.empty or len(frame) < 30:
        return {
            "status": "INSUFFICIENT_DATA",
            "decision": "NO SETUP",
            "score": 0,
            "rules": []
        }

    required = {"open", "high", "low", "close", "volume"}
    if not required.issubset(frame.columns):
        return {
            "status": "INVALID_DATA",
            "decision": "NO SETUP",
            "missing_columns": sorted(required - set(frame.columns)),
            "rules": []
        }

    data = frame.copy()

    for column in ["open", "high", "low", "close", "volume"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data.dropna(subset=["high", "low", "close"])

    if len(data) < 30:
        return {
            "status": "INSUFFICIENT_DATA",
            "decision": "NO SETUP",
            "score": 0,
            "rules": []
        }

    close = data["close"]

    # Calculate indicators if the caller hasn't already calculated them.
    if "ema_9" not in data:
        data["ema_9"] = close.ewm(span=9, adjust=False).mean()
    if "ema_20" not in data:
        data["ema_20"] = close.ewm(span=20, adjust=False).mean()
    if "ema_50" not in data:
        data["ema_50"] = close.ewm(span=50, adjust=False).mean()

    if "rsi_14" not in data:
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(
            alpha=1/14, min_periods=14, adjust=False
        ).mean()
        loss = (-delta.clip(upper=0)).ewm(
            alpha=1/14, min_periods=14, adjust=False
        ).mean()

        rs = gain / loss.replace(0, np.nan)
        data["rsi_14"] = 100 - 100 / (1 + rs)
        data.loc[(loss == 0) & (gain > 0), "rsi_14"] = 100
        data.loc[(gain == 0) & (loss > 0), "rsi_14"] = 0

    if "macd_hist" not in data:
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        data["macd_hist"] = macd - macd.ewm(
            span=9, adjust=False
        ).mean()

    if "adx_14" not in data:
        data["adx_14"] = np.nan

    if "atr_14" not in data:
        previous_close = close.shift(1)
        tr = pd.concat(
            [
                data["high"] - data["low"],
                (data["high"] - previous_close).abs(),
                (data["low"] - previous_close).abs()
            ],
            axis=1
        ).max(axis=1)

        data["atr_14"] = tr.ewm(
            alpha=1/14, min_periods=14, adjust=False
        ).mean()

    if "volume_ratio_20" not in data:
        avg_volume = data["volume"].rolling(20).mean()
        data["volume_ratio_20"] = (
            data["volume"] / avg_volume.replace(0, np.nan)
        )

    last = data.iloc[-1]
    price = _num(last["close"])

    rules = []
    votes = []

    def add_rule(name, direction, evidence, vote):
        rules.append({
            "module": name,
            "output": direction,
            "evidence": evidence
        })
        votes.append(vote)

    # Module 1: trend-following
    e9 = _num(last["ema_9"])
    e20 = _num(last["ema_20"])
    e50 = _num(last["ema_50"])

    if None not in (price, e9, e20, e50):
        if price > e9 > e20 > e50:
            add_rule(
                "Trend-following", "BULLISH",
                "Close > EMA9 > EMA20 > EMA50", 1
            )
        elif price < e9 < e20 < e50:
            add_rule(
                "Trend-following", "BEARISH",
                "Close < EMA9 < EMA20 < EMA50", -1
            )
        else:
            add_rule(
                "Trend-following", "NEUTRAL",
                "EMA stack is not aligned", 0
            )
    else:
        add_rule(
            "Trend-following", "UNAVAILABLE",
            "EMA values missing", 0
        )

    # Module 2: break of the prior 20-bar range, excluding current candle.
    prior_high = data["high"].rolling(20).max().shift(1).iloc[-1]
    prior_low = data["low"].rolling(20).min().shift(1).iloc[-1]
    volume_ratio = _num(last.get("volume_ratio_20"))

    if pd.notna(prior_high) and pd.notna(prior_low):
        if (
            price is not None and price > prior_high
            and volume_ratio is not None and volume_ratio >= 1.5
        ):
            add_rule(
                "Range-breakout", "BULLISH",
                "Above prior 20-bar high with relative volume >= 1.5x", 1
            )
        elif (
            price is not None and price < prior_low
            and volume_ratio is not None and volume_ratio >= 1.5
        ):
            add_rule(
                "Range-breakout", "BEARISH",
                "Below prior 20-bar low with relative volume >= 1.5x", -1
            )
        else:
            add_rule(
                "Range-breakout", "NO CONFIRMED BREAK",
                "Range break and relative-volume conditions not both met", 0
            )
    else:
        add_rule(
            "Range-breakout", "UNAVAILABLE",
            "Prior range could not be calculated", 0
        )

    # Module 3: momentum
    rsi = _num(last.get("rsi_14"))
    macd_hist = _num(last.get("macd_hist"))

    if rsi is not None and macd_hist is not None:
        if rsi >= 55 and macd_hist > 0:
            add_rule(
                "Momentum", "BULLISH",
                "RSI >= 55 and MACD histogram positive", 1
            )
        elif rsi <= 45 and macd_hist < 0:
            add_rule(
                "Momentum", "BEARISH",
                "RSI <= 45 and MACD histogram negative", -1
            )
        else:
            add_rule(
                "Momentum", "NEUTRAL",
                "Momentum confirmation not met", 0
            )
    else:
        add_rule(
            "Momentum", "UNAVAILABLE",
            "RSI or MACD histogram missing", 0
        )

    # Module 4: mean-reversion candidate only if ADX is available and low.
    adx = _num(last.get("adx_14"))

    if adx is not None and rsi is not None and adx < 18:
        if rsi <= 30:
            add_rule(
                "Mean-reversion", "OVERSOLD CANDIDATE",
                "RSI <= 30 and ADX < 18", 1
            )
        elif rsi >= 70:
            add_rule(
                "Mean-reversion", "OVERBOUGHT CANDIDATE",
                "RSI >= 70 and ADX < 18", -1
            )
        else:
            add_rule(
                "Mean-reversion", "NO EXTREME",
                "RSI is not at an extreme", 0
            )
    else:
        add_rule(
            "Mean-reversion", "NOT ACTIVE",
            "Requires available ADX < 18 and RSI", 0
        )

    score = int(sum(votes))

    if score >= 2:
        decision = "BULLISH RESEARCH BIAS"
    elif score <= -2:
        decision = "BEARISH RESEARCH BIAS"
    else:
        decision = "NO CONFLUENCE / WAIT"

    atr = _num(last.get("atr_14"))
    atr_levels = None

    if price is not None and atr is not None and atr > 0:
        atr_levels = {
            "atr": atr,
            "illustrative_price_minus_2_atr": price - 2 * atr,
            "illustrative_price_plus_2_atr": price + 2 * atr
        }

    return {
        "status": "OK",
        "decision": decision,
        "rule_score": score,
        "rule_modules": rules,
        "illustrative_atr_levels": atr_levels,
        "warning": (
            "Rule-based classification only. Not a validated strategy. "
            "No win probability or profitability claim."
        )
    }
