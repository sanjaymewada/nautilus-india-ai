from pathlib import Path
from datetime import datetime
import json
import sqlite3
import sys
import time

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


@st.cache_data(ttl=300, show_spinner=False)
def cached_yahoo_history(symbol: str, period: str, interval: str):
    """Cache free-provider historical candles briefly to reduce repeated requests."""
    from src.market_data import fetch_yahoo
    return fetch_yahoo(symbol, period, interval)


@st.cache_data(ttl=900, show_spinner=False)
def cached_company_profile(symbol: str):
    """Cache provider fundamentals briefly; missing provider fields remain missing."""
    from src.stock_intelligence import fetch_profile
    return fetch_profile(symbol)

for folder in [
    "data/market", "data/live", "data/training", "data/research",
    "data/backtests", "results/backtests", "models/live", "reports"
]:
    (ROOT / folder).mkdir(parents=True, exist_ok=True)


# ───────────────────────── PAGE CONFIG ─────────────────────────
st.set_page_config(
    page_title="NAUTILUS | Trading Intelligence Pro",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ───────────────────────── DESIGN SYSTEM ────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');

:root {
  --bg: #080d18;
  --panel: #101a2b;
  --panel2: #121f33;
  --line: rgba(148,177,216,.15);
  --text: #edf4ff;
  --muted: #8fa3bf;
  --blue: #5b8cff;
  --cyan: #45d6d0;
  --green: #3de0a1;
  --amber: #ffbf69;
  --red: #ff6b81;
}

html, body, [class*="css"] {
  font-family: 'Manrope', sans-serif;
}
.stApp {
  background:
    radial-gradient(ellipse at 12% 0%, rgba(42,91,180,.17), transparent 38%),
    radial-gradient(ellipse at 92% 8%, rgba(32,194,177,.09), transparent 28%),
    var(--bg);
  color: var(--text);
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { right: 1rem; }
.block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1800px; }
[data-testid="stSidebar"] {
  background: linear-gradient(180deg,#0d1626 0%,#0a111e 100%);
  border-right: 1px solid var(--line);
}
[data-testid="stSidebar"] > div { padding-top: 1.5rem; }
[data-testid="stMetric"] {
  background: linear-gradient(145deg,rgba(20,34,55,.97),rgba(13,23,39,.96));
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 18px 20px;
  min-height: 118px;
  box-shadow: 0 8px 26px rgba(0,0,0,.12);
  transition: transform .22s ease, border-color .22s ease, box-shadow .22s ease;
  animation: fadeUp .45s ease both;
}
[data-testid="stMetric"]:hover {
  transform: translateY(-3px);
  border-color: rgba(91,140,255,.5);
  box-shadow: 0 12px 32px rgba(30,90,190,.13);
}
[data-testid="stMetricLabel"] {
  color: var(--muted) !important;
  font-size: .78rem !important;
  font-weight: 700 !important;
  letter-spacing: .07em;
  text-transform: uppercase;
}
[data-testid="stMetricValue"] {
  color: var(--text) !important;
  font-size: clamp(1.4rem,2vw,2rem) !important;
  font-weight: 800 !important;
}
[data-testid="stMetricDelta"] { font-size: .76rem !important; }
h1,h2,h3 { color: var(--text) !important; letter-spacing: -.035em; }
h1 { font-weight: 800 !important; }
h2 { font-weight: 750 !important; margin-top: .6rem !important; }
h3 { font-weight: 700 !important; }
p, label, .stMarkdown { color: var(--text); }
small, .muted { color: var(--muted); }
hr { border-color: var(--line); }
div[data-testid="stVerticalBlockBorderWrapper"] {
  background: rgba(16,26,43,.72);
  border: 1px solid var(--line);
  border-radius: 16px;
}
.stButton button, .stDownloadButton button {
  border-radius: 10px;
  border: 1px solid rgba(91,140,255,.42);
  background: linear-gradient(135deg,#315fe0,#397fce);
  color: white;
  font-weight: 750;
  transition: all .2s ease;
}
.stButton button:hover, .stDownloadButton button:hover {
  transform: translateY(-2px);
  border-color: var(--cyan);
  box-shadow: 0 7px 22px rgba(60,130,255,.2);
}
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
  background: #0c1627;
  border-color: var(--line);
  border-radius: 10px;
}
[data-testid="stDataFrame"] {
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
}
[data-testid="stProgressBar"] > div > div {
  background: linear-gradient(90deg,var(--blue),var(--cyan));
}
[data-testid="stAlert"] { border-radius: 12px; }
div[role="radiogroup"] label {
  border: 1px solid transparent;
  border-radius: 9px;
  padding: 7px 10px;
}
div[role="radiogroup"] label:hover {
  background: rgba(91,140,255,.09);
}
.hero {
  position: relative;
  overflow: hidden;
  padding: 27px 30px;
  border: 1px solid rgba(91,140,255,.27);
  border-radius: 20px;
  background: linear-gradient(115deg,rgba(26,48,83,.93),rgba(13,29,46,.96) 58%,rgba(15,54,64,.72));
  margin-bottom: 20px;
  animation: fadeUp .4s ease both;
}
.hero:after {
  content: "";
  position: absolute;
  width: 240px; height: 240px;
  right: -55px; top: -120px;
  border: 1px solid rgba(69,214,208,.19);
  border-radius: 50%;
  box-shadow: 0 0 0 28px rgba(69,214,208,.025),0 0 0 56px rgba(91,140,255,.025);
  pointer-events: none;
}
.eyebrow {
  color: var(--cyan);
  font-family: 'DM Mono',monospace;
  font-size: .72rem;
  letter-spacing: .15em;
  text-transform: uppercase;
}
.hero-title { font-size: clamp(1.8rem,3vw,2.65rem); font-weight: 800; margin: 7px 0 6px; }
.hero-sub { color: #a7bad4; font-size: .93rem; }
.pill {
  display:inline-flex; align-items:center; gap:7px;
  border:1px solid var(--line); border-radius:999px;
  padding:7px 11px; font-size:.74rem; font-weight:750;
  background:rgba(5,12,23,.36); color:#d9e6fb;
  margin:4px 5px 0 0;
}
.dot {
  display:inline-block; width:7px; height:7px; border-radius:50%;
  background:var(--green); box-shadow:0 0 11px rgba(61,224,161,.8);
  animation:pulse 2s infinite;
}
.section-head {
  display:flex; align-items:center; justify-content:space-between;
  gap:12px; margin:22px 0 12px;
}
.section-title { font-size:1.03rem; font-weight:800; }
.section-note { color:var(--muted); font-size:.76rem; }
.panel {
  padding:18px 20px; border-radius:15px;
  background:linear-gradient(145deg,rgba(17,29,48,.95),rgba(12,21,36,.96));
  border:1px solid var(--line); height:100%;
}
.panel-title { font-size:.9rem; font-weight:800; margin-bottom:5px; }
.panel-note { color:var(--muted); font-size:.78rem; line-height:1.55; }
.status-good { color:var(--green); font-weight:800; }
.status-warn { color:var(--amber); font-weight:800; }
.status-bad { color:var(--red); font-weight:800; }
.big-number { font-size:1.8rem; font-weight:800; letter-spacing:-.04em; }
.mono { font-family:'DM Mono',monospace; }
.footer {
  color:#7186a3; font-size:.73rem; padding-top:20px;
  border-top:1px solid var(--line); margin-top:28px;
}
@keyframes fadeUp { from {opacity:0;transform:translateY(8px)} to {opacity:1;transform:translateY(0)} }
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(.82)} }
@media (prefers-reduced-motion: reduce) {
  *, *:before, *:after { animation:none !important; transition:none !important; }
}
</style>
""", unsafe_allow_html=True)


# ───────────────────────── DATA HELPERS ─────────────────────────
def folder_files(relative, patterns=("**/*",)):
    base = ROOT / relative
    found = []
    if base.exists():
        for pattern in patterns:
            found.extend(p for p in base.glob(pattern) if p.is_file())
    return sorted(set(found), key=lambda p: p.stat().st_mtime, reverse=True)


def count_files(relative, patterns=("**/*",)):
    return len(folder_files(relative, patterns))


def read_json(path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def read_jsonl(path, limit=1000):
    rows = []
    try:
        with path.open(errors="ignore") as f:
            for line in f.readlines()[-limit:]:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return pd.DataFrame(rows)


def size_label(path):
    try:
        n = path.stat().st_size
        return f"{n/1024:.1f} KB" if n < 1024**2 else f"{n/1024**2:.2f} MB"
    except Exception:
        return "—"


def section(title, note=""):
    st.markdown(
        f'<div class="section-head"><div class="section-title">{title}</div>'
        f'<div class="section-note">{note}</div></div>',
        unsafe_allow_html=True,
    )


def panel(title, description, status="Available", color="good"):
    css = {"good": "status-good", "warn": "status-warn", "bad": "status-bad"}.get(color, "status-good")
    st.markdown(
        f'<div class="panel"><div class="panel-title">{title}</div>'
        f'<div class="panel-note">{description}</div><br>'
        f'<div class="{css}">● {status}</div></div>',
        unsafe_allow_html=True,
    )


def metric_row(items):
    cols = st.columns(len(items))
    for col, (label, value, delta) in zip(cols, items):
        col.metric(label, value, delta)


def latest_files(relative, patterns=("**/*",), limit=8):
    files = folder_files(relative, patterns)
    return files[:limit]


def jsonl_inventory():
    out = []
    for p in folder_files("data/live", ("*.jsonl", "*.log", "*.json")):
        out.append({
            "File": p.name,
            "Type": p.suffix.lower(),
            "Size": size_label(p),
            "Updated": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d %b %H:%M"),
        })
    return pd.DataFrame(out)


def module_status():
    checks = [
        ("Market data", "src.market_data"),
        ("SMA backtesting", "src.backtesting.sma_backtest"),
        ("ML trainer", "src.backtesting.ml_trainer"),
        ("RL trainer", "src.backtesting.rl_trainer"),
        ("Live model trainer", "src.live.model_trainer"),
    ]
    results = []
    import importlib
    for name, mod in checks:
        try:
            importlib.import_module(mod)
            results.append((name, True, "Loaded"))
        except Exception as e:
            results.append((name, False, type(e).__name__))
    return results


# ───────────────────────── GLOBAL INVENTORY ─────────────────────
market_files = folder_files("data/market", ("*.parquet", "*.csv", "*.feather"))
live_files = folder_files("data/live", ("*.jsonl", "*.log", "*.json"))
training_files = folder_files("data/training", ("*.csv", "*.parquet"))
model_files = folder_files("models", ("*.joblib", "*.pkl", "*.json", "*.pt", "*.onnx"))
research_files = (
    folder_files("data/research") +
    folder_files("results") +
    folder_files("reports")
)
live_jsonl = {p.stem: p for p in live_files if p.suffix == ".jsonl"}

def live_frame(key):
    path = live_jsonl.get(key)
    return read_jsonl(path) if path else pd.DataFrame()


# Persistent local activity ledger adapted from Dashboard 1's event-store workflow.
EVENT_DB = ROOT / "data/research" / "learning_journal.sqlite3"

def record_app_event(component, message, details=""):
    EVENT_DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(EVENT_DB) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS app_events (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, level TEXT NOT NULL, component TEXT NOT NULL, message TEXT NOT NULL, details TEXT)")
        conn.execute("INSERT INTO app_events (created_at,level,component,message,details) VALUES (?,?,?,?,?)", (datetime.now().isoformat(timespec="seconds"), "INFO", str(component), str(message), str(details)))
        conn.commit()

def read_app_events(limit=100):
    EVENT_DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(EVENT_DB) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS app_events (id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, level TEXT NOT NULL, component TEXT NOT NULL, message TEXT NOT NULL, details TEXT)")
        return pd.read_sql_query("SELECT created_at AS Timestamp, level AS Level, component AS Component, message AS Event, details AS Details FROM app_events ORDER BY id DESC LIMIT ?", conn, params=(int(limit),))


predictions = live_frame("predictions")
candles = live_frame("candles")
features = live_frame("features")
outcomes = live_frame("outcomes")


# ───────────────────────── SIDEBAR ──────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:5px 4px 22px">
      <div style="font-family:'DM Mono',monospace;color:#45d6d0;letter-spacing:.18em;font-size:.7rem">NAUTILUS / INDIA</div>
      <div style="font-size:1.45rem;font-weight:800;letter-spacing:-.05em;margin-top:5px">INTELLIGENCE<span style="color:#5b8cff">.</span></div>
      <div style="font-size:.75rem;color:#8fa3bf;margin-top:4px">AI Trading Control Room</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">WORKSPACES</div>', unsafe_allow_html=True)
    page = st.radio(
        "Navigation",
        [
            "Command Center",
            "Market Data Engine",
            "Stock Intelligence",
            "Backtesting Lab",
            "AI & Learning",
            "Live Prediction Room",
            "Risk & Paper Trading",
            "System Monitor",
            "Experiments & Reports",
            "Multi-Stock Scanner",
            "Learning & Mistakes",
            "Trade Journal",
            "API Explorer",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown('<div class="eyebrow">OPERATING MODE</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pill"><span class="dot"></span> Research / Simulation</div>'
        '<div class="pill">NSE · BSE</div>'
        '<div class="pill">Orders: DISABLED</div>',
        unsafe_allow_html=True,
    )
    st.caption("Local-first workspace · Manual execution only")
    if st.button("↻ Refresh dashboard", width="stretch"):
        st.rerun()


# ───────────────────────── UNIVERSAL HEADER ─────────────────────
st.markdown(f"""
<div class="hero">
  <div class="eyebrow">◈ AUTONOMOUS RESEARCH ENVIRONMENT / INDIA</div>
  <div class="hero-title">Trading Intelligence <span style="color:#45d6d0">Control Room</span></div>
  <div class="hero-sub">One workspace for market data, strategy research, model intelligence, predictions and risk oversight.</div>
  <div style="margin-top:14px">
    <span class="pill"><span class="dot"></span> SYSTEM UI READY</span>
    <span class="pill">RESEARCH MODE</span>
    <span class="pill">LIVE ORDER EXECUTION OFF</span>
    <span class="pill mono">{datetime.now().strftime("%d %b %Y · %H:%M:%S")}</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ───────────────────────── COMMAND CENTER ────────────────────────
if page == "Command Center":
    section("Executive overview", "LIVE INVENTORY · LOCAL FILES · LAST REFRESH")

    metric_row([
        ("Market datasets", str(len(market_files)), "CSV / Parquet"),
        ("Live log streams", str(len(live_files)), "Files discovered"),
        ("Training datasets", str(len(training_files)), "Ready for review"),
        ("Model artifacts", str(len(model_files)), "Saved artifacts"),
        ("Research / reports", str(len(set(research_files))), "Files discovered"),
    ])

    section("Intelligence at a glance", "LATEST AVAILABLE LOCAL STATE")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        panel("Market data engine",
              f"{len(market_files)} datasets discovered. Fetch and validate candles from the Market Data workspace.",
              "Data found" if market_files else "Needs data",
              "good" if market_files else "warn")
    with c2:
        panel("Prediction pipeline",
              f"{len(predictions)} prediction records and {len(features)} feature records currently readable.",
              "Records found" if len(predictions) else "No predictions",
              "good" if len(predictions) else "warn")
    with c3:
        panel("Model readiness",
              f"{len(model_files)} model/report artifacts detected. Presence alone does not mean a model is approved.",
              "Artifacts found" if model_files else "No model artifacts",
              "good" if model_files else "warn")
    with c4:
        panel("Risk & execution",
              "This control room is for research and simulation. Live order placement is not enabled here.",
              "Execution disabled", "warn")

    left, right = st.columns([1.3, 1])
    with left:
        section("Module health", "IMPORT CHECKS")
        checks = module_status()
        for name, ok, detail in checks:
            a, b = st.columns([3, 1])
            a.markdown(f"**{name}**")
            b.markdown(
                f'<span class="{"status-good" if ok else "status-bad"}">'
                f'{"● READY" if ok else "● CHECK"}</span>',
                unsafe_allow_html=True,
            )
            if not ok:
                st.caption(f"{name}: {detail}")
    with right:
        section("Activity snapshot", "MOST RECENT FILES")
        activity = []
        for f in sorted(set(market_files + live_files + training_files + model_files),
                        key=lambda p: p.stat().st_mtime, reverse=True)[:8]:
            activity.append({
                "Artifact": f.name,
                "Area": f.parent.name,
                "Updated": datetime.fromtimestamp(f.stat().st_mtime).strftime("%H:%M:%S"),
            })
        if activity:
            st.dataframe(pd.DataFrame(activity), hide_index=True, width="stretch")
        else:
            st.info("No project artifacts found yet.")

    section("Data stream overview", "RECORD COUNTS FROM LOCAL JSONL")
    stream_cols = st.columns(4)
    for col, label, frame in zip(
        stream_cols,
        ["Candles", "Features", "Predictions", "Outcomes"],
        [candles, features, predictions, outcomes],
    ):
        col.metric(label, len(frame), "records read")

    if len(predictions):
        section("Latest predictions", "RAW LOCAL RECORDS · NOT A TRADE RECOMMENDATION")
        st.dataframe(predictions.tail(8), width="stretch", hide_index=True)
    else:
        st.info("Prediction log is empty or has not been generated. Open Live Prediction Room to inspect available inputs.")

    section("Quick actions", "JUMP DIRECTLY TO A WORKSPACE")
    q1, q2, q3, q4 = st.columns(4)
    with q1:
        if st.button("↗ Market Data", width="stretch"):
            st.session_state["quick_page"] = "Market Data Engine"
            st.rerun()
    with q2:
        if st.button("↗ Backtesting", width="stretch"):
            st.session_state["quick_page"] = "Backtesting Lab"
            st.rerun()
    with q3:
        if st.button("↗ AI & Learning", width="stretch"):
            st.session_state["quick_page"] = "AI & Learning"
            st.rerun()
    with q4:
        if st.button("↗ System Health", width="stretch"):
            st.session_state["quick_page"] = "System Monitor"
            st.rerun()


# ───────────────────────── MARKET DATA ──────────────────────────
elif page == "Market Data Engine":
    section("Market data engine", "FETCH · VALIDATE · INSPECT")
    metric_row([
        ("Available datasets", len(market_files), "Local market files"),
        ("Live candles", len(candles), "JSONL records"),
        ("Feature records", len(features), "JSONL records"),
    ])
    with st.container(border=True):
        st.subheader("Fetch historical market data")
        st.caption("Yahoo Finance is an external data source. Data may be delayed, incomplete or unavailable.")
        a, b, c = st.columns(3)
        with a:
            symbol = st.text_input("Ticker", "RELIANCE.NS")
        with b:
            period = st.selectbox("History", ["5d", "1mo", "3mo", "6mo", "1y", "2y"], index=3)
        with c:
            interval = st.selectbox("Candle interval", ["1m", "5m", "15m", "30m", "1h", "1d"], index=5)
        if st.button("Fetch & validate data", type="primary"):
            try:
                from src.market_data import fetch_yahoo
                with st.spinner("Fetching market data…"):
                    ticker, frame = fetch_yahoo(symbol.strip(), period, interval)
                if frame is None or frame.empty:
                    st.warning("No candles returned. Check the symbol, interval and source availability.")
                else:
                    # Preserve the candle timestamp index when saving historical OHLCV data.
                    safe_ticker = ticker.replace("/", "_").replace(":", "_")
                    out = ROOT / "data/market" / f"{safe_ticker}_{interval}_{period}.parquet"
                    out.parent.mkdir(parents=True, exist_ok=True)
                    frame.to_parquet(out)
                    st.success(f"Saved {len(frame):,} rows for {ticker} to {out.relative_to(ROOT)}")
                    st.dataframe(frame.tail(20), width="stretch")
            except Exception as e:
                st.error(f"Fetch failed: {e}")
    section("Dataset inventory", "CLICK A FILE TO INSPECT")
    if market_files:
        options = {f"{p.name} · {size_label(p)}": p for p in market_files}
        chosen = st.selectbox("Dataset", list(options.keys()))
        p = options[chosen]
        try:
            frame = pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p)
            a, b, c = st.columns(3)
            a.metric("Rows", f"{len(frame):,}")
            b.metric("Columns", len(frame.columns))
            c.metric("Missing cells", f"{int(frame.isna().sum().sum()):,}")
            st.dataframe(frame.tail(100), width="stretch", hide_index=True)
            numeric = frame.select_dtypes("number")
            if not numeric.empty:
                st.line_chart(numeric.iloc[:, :4])
        except Exception as e:
            st.error(f"Could not read file: {e}")
    else:
        st.info("No local market datasets yet. Fetch historical data above.")


# ───────────────────────── BACKTESTING ──────────────────────────
elif page == "Backtesting Lab":
    section("Backtesting laboratory", "HYPOTHESIS → TEST → REVIEW")
    st.warning("Research only. Results may exclude slippage, taxes, brokerage and market-impact costs.")
    a, b, c = st.columns(3)
    a.metric("Market files", len(market_files))
    b.metric("Saved backtests", count_files("results/backtests"))
    c.metric("Research artifacts", len(set(research_files)))
    with st.container(border=True):
        st.subheader("SMA crossover baseline")
        if not market_files:
            st.info("Fetch a dataset in Market Data Engine first.")
        else:
            options = {p.name: p for p in market_files}
            selected = st.selectbox("Input dataset", list(options.keys()))
            x, y, z = st.columns(3)
            fast = x.number_input("Fast SMA", 2, 100, 10)
            slow = y.number_input("Slow SMA", 3, 300, 30)
            fee = z.number_input("Fee (basis points)", 0.0, 100.0, 5.0, .5)
            if st.button("Run SMA backtest", type="primary"):
                if fast >= slow:
                    st.error("Fast SMA must be smaller than Slow SMA.")
                else:
                    try:
                        from src.backtesting.sma_backtest import load_data, run_backtest
                        data = load_data(str(options[selected]))
                        result = run_backtest(data, int(fast), int(slow), float(fee))
                        st.success("Backtest finished.")
                        if isinstance(result, tuple):
                            report, trades = result[0], result[1] if len(result) > 1 else None
                        else:
                            report, trades = result, None
                        st.json(report if isinstance(report, dict) else {"result": str(report)})
                        out = ROOT / "results/backtests" / f"sma_{datetime.now():%Y%m%d_%H%M%S}.json"
                        out.write_text(json.dumps(report, default=str, indent=2))
                        st.caption(f"Saved report: {out.relative_to(ROOT)}")
                        if isinstance(trades, pd.DataFrame):
                            st.dataframe(trades.tail(100), width="stretch")
                        elif isinstance(trades, list):
                            st.dataframe(pd.DataFrame(trades), width="stretch")
                    except Exception as e:
                        st.error(f"Backtest error: {e}")
    section("Previous experiment outputs", "LATEST RESULTS")
    result_files = latest_files("results/backtests", limit=15)
    if result_files:
        st.dataframe(pd.DataFrame([{
            "File": p.name,
            "Size": size_label(p),
            "Updated": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d %b %H:%M"),
        } for p in result_files]), width="stretch", hide_index=True)
    else:
        st.caption("No backtest reports saved yet.")


# ───────────────────────── AI & LEARNING ────────────────────────
elif page == "AI & Learning":
    section("AI & learning", "OFFLINE TRAINING · MODEL EVALUATION")
    metric_row([
        ("Training datasets", len(training_files), "Prepared inputs"),
        ("Model artifacts", len(model_files), "Saved files"),
        ("Prediction rows", len(predictions), "Local log"),
    ])
    with st.container(border=True):
        st.subheader("Random Forest research trainer")
        st.caption("Offline research only. A trained model is not automatically approved for trading.")
        if not training_files:
            st.info("Training CSVs not found in data/training. Prepare a labelled dataset before training.")
        else:
            chosen = st.selectbox("Training dataset", training_files, format_func=lambda p: p.name)
            if st.button("Train research model", type="primary"):
                try:
                    from src.backtesting.ml_trainer import MLTrainer
                    frame = pd.read_csv(chosen) if chosen.suffix == ".csv" else pd.read_parquet(chosen)
                    trainer = MLTrainer()
                    prepared = trainer.prepare_data(frame)
                    report = trainer.train(prepared)
                    st.success("Training call completed. Review metrics before using the model.")
                    st.json(report if isinstance(report, dict) else {"result": str(report)})
                    out = ROOT / "reports" / f"ml_report_{datetime.now():%Y%m%d_%H%M%S}.json"
                    out.write_text(json.dumps(report, default=str, indent=2))
                    st.caption(f"Report saved: {out.relative_to(ROOT)}")
                except Exception as e:
                    st.error(f"Training failed: {e}")
    section("Saved model inventory", "ARTIFACTS ARE NOT AUTOMATICALLY PROMOTED")
    if model_files:
        st.dataframe(pd.DataFrame([{
            "Artifact": p.name, "Directory": str(p.parent.relative_to(ROOT)),
            "Size": size_label(p),
            "Updated": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d %b %H:%M"),
        } for p in model_files]), width="stretch", hide_index=True)
    else:
        st.info("No saved model artifacts detected.")
    st.markdown(
        '<div class="panel"><div class="panel-title">Model governance</div>'
        '<div class="panel-note">Keep training, validation, promotion and live inference separate. '
        'Never infer model quality from the presence of a model file alone.</div></div>',
        unsafe_allow_html=True,
    )


# ───────────────────────── LIVE PREDICTIONS ─────────────────────
elif page == "Live Prediction Room":
    section("Live prediction room", "LOCAL LOG INSPECTION · PIPELINE VISIBILITY")
    metric_row([
        ("Prediction events", len(predictions), "predictions.jsonl"),
        ("Feature events", len(features), "features.jsonl"),
        ("Candle events", len(candles), "candles.jsonl"),
        ("Outcome events", len(outcomes), "outcomes.jsonl"),
    ])
    st.warning("A populated log does not prove a live exchange feed is active. Confirm timestamps and controller logs.")

    # Dashboard 3 feature: explicit multi-horizon readiness, based on actual files.
    section("Multi-horizon model readiness", "FILE CHECKS · NOT A QUALITY CERTIFICATION")
    horizon_rows = []
    for horizon in (1, 5, 15, 30, 60, 240):
        model_path = ROOT / "models/live" / f"model_{horizon}m.joblib"
        metadata_path = ROOT / "models/live" / f"model_{horizon}m.json"
        horizon_rows.append({
            "Horizon": f"{horizon}m",
            "Model file": "FOUND" if model_path.exists() else "MISSING",
            "Metadata": "FOUND" if metadata_path.exists() else "MISSING",
            "Model updated": datetime.fromtimestamp(model_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M") if model_path.exists() else "—",
        })
    st.dataframe(pd.DataFrame(horizon_rows), width="stretch", hide_index=True)
    st.caption("A model file being present does not prove validation quality, freshness, or profitability.")

    # Show counts grouped by horizon/timeframe when the log schema contains such a field.
    if not predictions.empty:
        horizon_col = next((c for c in ("horizon", "timeframe", "horizon_minutes", "target_horizon") if c in predictions.columns), None)
        if horizon_col:
            section("Prediction coverage by horizon", "COUNTS FROM SAVED JSONL RECORDS")
            st.dataframe(
                predictions[horizon_col].fillna("UNKNOWN").astype(str).value_counts().rename_axis("Horizon").reset_index(name="Prediction records"),
                width="stretch", hide_index=True,
            )

    # Pipeline component checks from the monitoring dashboard, without starting services.
    with st.expander("Live pipeline module inventory"):
        import importlib.util
        live_modules = [
            "src.live.market_feed", "src.live.candle_aggregator", "src.live.feature_engine",
            "src.live.prediction_engine", "src.live.event_store", "src.live.outcome_tracker",
            "src.live.model_trainer", "src.live.model_promotion", "src.live.model_service",
        ]
        module_rows = []
        for module_name in live_modules:
            try:
                found = importlib.util.find_spec(module_name) is not None
            except (ImportError, ModuleNotFoundError, ValueError):
                found = False
            module_rows.append({"Module": module_name, "Status": "PRESENT" if found else "NOT FOUND"})
        st.dataframe(pd.DataFrame(module_rows), width="stretch", hide_index=True)

    for title, frame in [
        ("Latest predictions", predictions),
        ("Latest feature records", features),
        ("Latest candles", candles),
        ("Latest outcomes", outcomes),
    ]:
        with st.expander(f"{title} · {len(frame)} records", expanded=(title == "Latest predictions")):
            if frame.empty:
                st.caption("No readable records.")
            else:
                st.dataframe(frame.tail(30), width="stretch", hide_index=True)
    logs = [p for p in live_files if p.suffix == ".log"]
    if logs:
        with st.expander("Controller logs"):
            chosen = st.selectbox("Log file", logs, format_func=lambda p: p.name)
            try:
                st.code("\n".join(chosen.read_text(errors="ignore").splitlines()[-100:]))
            except Exception as e:
                st.error(str(e))


# ───────────────────────── RISK / PAPER TRADING ─────────────────
elif page == "Risk & Paper Trading":
    section("Risk & paper trading", "SIMULATION GUARDRAILS")
    st.warning("This workspace does not place real orders. The following values are planning inputs, not connected broker controls.")
    a, b, c = st.columns(3)
    with a:
        capital = st.number_input("Paper capital (₹)", 10000, 100000000, 100000, 10000)
    with b:
        risk_pct = st.slider("Risk per trade (%)", .1, 2.0, .5, .1)
    with c:
        stop_pct = st.slider("Stop distance (%)", .1, 5.0, 1.0, .1)
    risk_amount = capital * risk_pct / 100
    exposure = risk_amount / (stop_pct / 100)
    x, y = st.columns(2)
    x.metric("Illustrative risk budget", f"₹{risk_amount:,.0f}")
    y.metric("Illustrative position value", f"₹{exposure:,.0f}")
    st.caption("Position value is a simplified calculation; it excludes liquidity, lot sizes, gaps, leverage rules and fees.")
    section("Risk checklist", "REVIEW BEFORE ANY EXPERIMENT")
    for item in [
        "Define entry, invalidation and exit rules before testing",
        "Include realistic transaction costs and slippage",
        "Test out-of-sample and across different market regimes",
        "Track drawdown, losing streaks and exposure limits",
        "Keep live execution disabled until separate approval and testing",
    ]:
        st.checkbox(item, key="risk_" + str(abs(hash(item))))


# ───────────────────────── SYSTEM MONITOR ────────────────────────
elif page == "System Monitor":
    section("System monitor", "APPLICATION · STORAGE · MODULE READINESS")
    import shutil
    disk = shutil.disk_usage(ROOT)
    a, b, c = st.columns(3)
    a.metric("Disk total", f"{disk.total / 1024**3:.1f} GB")
    b.metric("Disk free", f"{disk.free / 1024**3:.1f} GB")
    c.metric("Python", sys.version.split()[0])
    st.progress(disk.used / disk.total, text=f"Disk used: {disk.used / disk.total:.1%}")
    section("Python module checks", "IMPORT TESTS · NOT A FULL FUNCTIONAL TEST")
    for name, ok, detail in module_status():
        x, y = st.columns([3, 1])
        x.write(name)
        y.markdown(
            f'<span class="{"status-good" if ok else "status-bad"}">'
            f'{"READY" if ok else "ERROR"}</span>',
            unsafe_allow_html=True,
        )
        if not ok:
            st.caption(detail)
    section("Persistent activity ledger", "SQLITE EVENT STORE · RECENT WORKFLOW EVENTS")
    event_frame = read_app_events(100)
    if not event_frame.empty:
        st.dataframe(event_frame, width="stretch", hide_index=True)
        st.download_button("Export activity ledger CSV", event_frame.to_csv(index=False).encode("utf-8"), file_name="nautilus_activity_ledger.csv", mime="text/csv")
    else:
        st.caption("No app events recorded yet. Scanner runs and journal saves will appear here.")

    section("Storage map", "PROJECT FOLDER COUNTS")
    dirs = ["data/market", "data/live", "data/training", "data/research",
            "data/backtests", "models", "models/live", "results/backtests", "reports"]
    st.dataframe(pd.DataFrame([{
        "Directory": d,
        "Files": count_files(d),
        "Exists": (ROOT / d).exists(),
    } for d in dirs]), width="stretch", hide_index=True)


# ───────────────────────── REPORTS ──────────────────────────────
elif page == "Experiments & Reports":
    section("Experiments & reports", "CENTRAL ARTIFACT LIBRARY")
    all_files = sorted(set(
        folder_files("data/research") + folder_files("results") +
        folder_files("reports") + folder_files("data/backtests")
    ), key=lambda p: p.stat().st_mtime, reverse=True)
    metric_row([
        ("Total artifacts", len(all_files), "Research & reports"),
        ("JSON reports", sum(p.suffix == ".json" for p in all_files), "Structured outputs"),
        ("CSV datasets", sum(p.suffix == ".csv" for p in all_files), "Tabular outputs"),
    ])
    if all_files:
        st.dataframe(pd.DataFrame([{
            "Artifact": p.name,
            "Location": str(p.parent.relative_to(ROOT)),
            "Format": p.suffix or "file",
            "Size": size_label(p),
            "Modified": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        } for p in all_files]), width="stretch", hide_index=True)
        selected = st.selectbox("Preview artifact", all_files, format_func=lambda p: f"{p.name} · {p.parent.name}")
        try:
            if selected.suffix == ".json":
                st.json(read_json(selected))
            elif selected.suffix in [".csv", ".jsonl"]:
                df = pd.read_csv(selected) if selected.suffix == ".csv" else read_jsonl(selected)
                st.dataframe(df.tail(100), width="stretch")
            elif selected.suffix == ".log":
                st.code("\n".join(selected.read_text(errors="ignore").splitlines()[-100:]))
            else:
                st.caption(f"Preview not available for {selected.suffix or 'this file type'}.")
            st.download_button("Download selected artifact", selected.read_bytes(),
                               file_name=selected.name, width="stretch")
        except Exception as e:
            st.error(f"Could not preview artifact: {e}")
    else:
        st.info("No reports yet. Run a research workflow to create artifacts.")


# ───────────────────────── API EXPLORER ─────────────────────────

# ───────────────────── STOCK INTELLIGENCE ───────────────────────
elif page == "Stock Intelligence":
    import os
    from src.stock_intelligence import (
        resolve_symbol, fetch_profile, add_indicators, fmt, market_cap_label,
        quant_engine, algo_engine,
    )
    from src.market_data import quality_report

    section("Stock Intelligence", "DEEP TECHNICALS · FUNDAMENTALS · MULTI-TIMEFRAME · AI RESEARCH")

    # NAUTILUS_LIGHTWEIGHT_INDEX_BOARD
    # Clickable Indian index board + TradingView Lightweight Charts.
    import json
    import streamlit.components.v1 as components

    st.markdown("## Indian Market Index Board")
    st.caption(
        "Select an index to load its chart and research analysis. "
        "Data availability and delay depend on the configured market-data source."
    )

    _index_defs = [
        ("NIFTY 50", "^NSEI"),
        ("BANK NIFTY", "^NSEBANK"),
        ("FIN NIFTY", "NIFTY_FIN_SERVICE.NS"),
        ("MIDCAP SELECT", "NIFTY_MID_SELECT.NS"),
        ("SENSEX", "^BSESN"),
    ]

    if "nautilus_selected_index" not in st.session_state:
        st.session_state["nautilus_selected_index"] = "NIFTY 50"

    _index_cols = st.columns(len(_index_defs))
    for _icol, (_iname, _iticker) in zip(_index_cols, _index_defs):
        _selected_style = (
            "● " if st.session_state["nautilus_selected_index"] == _iname else ""
        )
        if _icol.button(
            _selected_style + _iname,
            key="nautilus_index_btn_" + _iname.replace(" ", "_"),
            use_container_width=True,
        ):
            st.session_state["nautilus_selected_index"] = _iname
            st.rerun()

    _index_lookup = dict(_index_defs)
    _index_name = st.session_state["nautilus_selected_index"]
    _index_ticker = _index_lookup[_index_name]

    _period_choices = {
        "5m": ("1d", "5m"),
        "15m": ("5d", "15m"),
        "1h": ("1mo", "1h"),
        "1D": ("1y", "1d"),
        "1W": ("5y", "1wk"),
    }
    _controls = st.columns([1, 2, 3])
    _index_tf = _controls[0].selectbox(
        "Chart timeframe",
        list(_period_choices),
        index=3,
        key="nautilus_index_chart_tf",
    )
    _index_period, _index_interval = _period_choices[_index_tf]
    _index_indicators = _controls[1].multiselect(
        "Chart overlays",
        ["EMA 9", "EMA 20", "EMA 50", "EMA 200",
         "Bollinger Bands", "RSI (14)", "MACD"],
        default=["EMA 20", "EMA 50"],
        key="nautilus_index_overlays",
    )
    _controls[2].caption(
        f"Selected: {_index_name} · Yahoo Finance symbol: {_index_ticker}"
    )

    _idx_raw = None
    _idx_frame = None
    _idx_quant = {}
    _idx_algo = {}
    _idx_error = None

    try:
        with st.spinner(f"Loading {_index_name} market data..."):
            _, _idx_raw = cached_yahoo_history(
                _index_ticker, _index_period, _index_interval
            )
            if _idx_raw is None or _idx_raw.empty:
                raise ValueError(
                    "No candles returned for this symbol/timeframe. "
                    "The Yahoo Finance symbol may not be supported."
                )

            _idx_frame = add_indicators(_idx_raw.copy())
            if _idx_frame is None or _idx_frame.empty:
                raise ValueError("Indicator processing returned no candle data.")

            try:
                _idx_quant = quant_engine(_idx_frame)
                if not isinstance(_idx_quant, dict):
                    _idx_quant = {"result": str(_idx_quant)}
            except Exception as _e:
                _idx_quant = {"error": str(_e)}

            try:
                _idx_algo = algo_engine(_idx_frame)
                if not isinstance(_idx_algo, dict):
                    _idx_algo = {"result": str(_idx_algo)}
            except Exception as _e:
                _idx_algo = {"error": str(_e)}

    except Exception as _e:
        _idx_error = str(_e)

    if _idx_error:
        st.error(f"{_index_name} data load failed: {_idx_error}")
        st.info(
            "Chart and analysis need historical OHLC data from the configured "
            "data source. The other dashboard sections remain available."
        )
    else:
        def _idx_find_column(df, wanted):
            for col in df.columns:
                name = str(col[-1] if isinstance(col, tuple) else col).strip().lower()
                if name == wanted.lower():
                    return col
            return None

        _c_open = _idx_find_column(_idx_frame, "Open")
        _c_high = _idx_find_column(_idx_frame, "High")
        _c_low = _idx_find_column(_idx_frame, "Low")
        _c_close = _idx_find_column(_idx_frame, "Close")
        _c_volume = _idx_find_column(_idx_frame, "Volume")

        if any(c is None for c in (_c_open, _c_high, _c_low, _c_close)):
            st.error(
                "OHLC columns were not found in the returned dataset. "
                "Chart rendering skipped to avoid showing incorrect candles."
            )
        else:
            import pandas as pd

            _idx_chart_df = pd.DataFrame(index=_idx_frame.index)
            _idx_chart_df["Open"] = pd.to_numeric(_idx_frame[_c_open], errors="coerce")
            _idx_chart_df["High"] = pd.to_numeric(_idx_frame[_c_high], errors="coerce")
            _idx_chart_df["Low"] = pd.to_numeric(_idx_frame[_c_low], errors="coerce")
            _idx_chart_df["Close"] = pd.to_numeric(_idx_frame[_c_close], errors="coerce")
            _idx_chart_df["Volume"] = (
                pd.to_numeric(_idx_frame[_c_volume], errors="coerce").fillna(0)
                if _c_volume is not None else 0
            )
            _idx_chart_df = _idx_chart_df.dropna(
                subset=["Open", "High", "Low", "Close"]
            )
            _idx_chart_df = _idx_chart_df[~_idx_chart_df.index.duplicated(keep="last")]
            _idx_chart_df = _idx_chart_df.sort_index()

            if _idx_chart_df.empty:
                st.error("No valid OHLC candles remain after cleaning.")
            else:
                _idx_close = _idx_chart_df["Close"]
                _idx_last = float(_idx_close.iloc[-1])
                _idx_prev = (
                    float(_idx_close.iloc[-2])
                    if len(_idx_close) > 1 else _idx_last
                )
                _idx_change = (
                    ((_idx_last / _idx_prev) - 1) * 100
                    if _idx_prev else 0.0
                )

                _metric_cols = st.columns(4)
                _metric_cols[0].metric(
                    f"{_index_name} latest close",
                    f"{_idx_last:,.2f}",
                    f"{_idx_change:+.2f}%"
                )
                _metric_cols[1].metric(
                    "Quant regime",
                    str(_idx_quant.get(
                        "regime",
                        _idx_quant.get("market_regime", _idx_quant.get("status", "N/A"))
                    ))
                )
                _metric_cols[2].metric(
                    "Algo research bias",
                    str(_idx_algo.get(
                        "decision",
                        _idx_algo.get("signal", _idx_algo.get("status", "N/A"))
                    ))
                )
                _metric_cols[3].metric(
                    "Rule score",
                    str(_idx_algo.get(
                        "rule_score",
                        _idx_algo.get("score", "N/A")
                    ))
                )

                _chart_rows = []
                _overlay_rows = {
                    "EMA 9": [],
                    "EMA 20": [],
                    "EMA 50": [],
                    "EMA 200": [],
                    "Bollinger Bands": {"upper": [], "middle": [], "lower": []},
                }

                for _ts, _row in _idx_chart_df.iterrows():
                    _time = int(pd.Timestamp(_ts).timestamp())
                    _chart_rows.append({
                        "time": _time,
                        "open": float(_row["Open"]),
                        "high": float(_row["High"]),
                        "low": float(_row["Low"]),
                        "close": float(_row["Close"]),
                        "volume": max(0.0, float(_row["Volume"])),
                        "volumeColor": (
                            "#26a69a" if _row["Close"] >= _row["Open"]
                            else "#ef5350"
                        ),
                    })

                for _span, _name in [
                    (9, "EMA 9"), (20, "EMA 20"),
                    (50, "EMA 50"), (200, "EMA 200")
                ]:
                    _series = _idx_close.ewm(
                        span=_span, adjust=False, min_periods=_span
                    ).mean()
                    for _ts, _val in _series.items():
                        if pd.notna(_val):
                            _overlay_rows[_name].append({
                                "time": int(pd.Timestamp(_ts).timestamp()),
                                "value": float(_val),
                            })

                _bb_mid = _idx_close.rolling(20).mean()
                _bb_std = _idx_close.rolling(20).std()
                for _ts, _mid, _std in zip(
                    _idx_chart_df.index, _bb_mid, _bb_std
                ):
                    if pd.notna(_mid) and pd.notna(_std):
                        _time = int(pd.Timestamp(_ts).timestamp())
                        _overlay_rows["Bollinger Bands"]["upper"].append({
                            "time": _time, "value": float(_mid + 2 * _std)
                        })
                        _overlay_rows["Bollinger Bands"]["middle"].append({
                            "time": _time, "value": float(_mid)
                        })
                        _overlay_rows["Bollinger Bands"]["lower"].append({
                            "time": _time, "value": float(_mid - 2 * _std)
                        })

                # NAUTILUS_RSI_MACD_FIXED
                _delta = _idx_close.diff()
                _gain = _delta.clip(lower=0).ewm(
                    alpha=1/14, adjust=False, min_periods=14
                ).mean()
                _loss = (-_delta.clip(upper=0)).ewm(
                    alpha=1/14, adjust=False, min_periods=14
                ).mean()
                _rs = _gain / _loss.replace(0, float("nan"))
                _rsi = 100 - (100 / (1 + _rs))
                _rsi = _rsi.where(_loss != 0, 100.0)

                _macd_line = (
                    _idx_close.ewm(span=12, adjust=False).mean()
                    - _idx_close.ewm(span=26, adjust=False).mean()
                )
                _macd_signal_line = _macd_line.ewm(
                    span=9, adjust=False
                ).mean()
                _macd_hist = _macd_line - _macd_signal_line

                def _line_points(series):
                    return [
                        {"time": int(pd.Timestamp(ts).timestamp()),
                         "value": float(value)}
                        for ts, value in series.items()
                        if pd.notna(value)
                    ]

                _chart_payload = {
                    "candles": _chart_rows,
                    "overlays": _overlay_rows,
                    "selected": _index_name,
                    "timeframe": _index_tf,
                    "visibleIndicators": _index_indicators,
                    "rsi": _line_points(_rsi),
                    "macd": _line_points(_macd_line),
                    "macdSignal": _line_points(_macd_signal_line),
                    "macdHistogram": _line_points(_macd_hist),
                }

                _chart_html = r"""
                <div id="nautilus-chart" style="width:100%;height:540px;"></div>
                <div id="nautilus-rsi-title" style="font:13px sans-serif;color:#d1d4dc;padding:8px 0 2px;">RSI (14)</div>
                <div id="nautilus-rsi-chart" style="width:100%;height:170px;display:none;"></div>
                <div id="nautilus-macd-title" style="font:13px sans-serif;color:#d1d4dc;padding:8px 0 2px;">MACD (12, 26, 9)</div>
                <div id="nautilus-macd-chart" style="width:100%;height:190px;display:none;"></div>
                <div id="nautilus-chart-status"
                     style="font:12px sans-serif;color:#888;padding:5px 0;"></div>
                <script src="https://unpkg.com/lightweight-charts@5.0.8/dist/lightweight-charts.standalone.production.js"></script>
                <script>
                const payload = __PAYLOAD__;
                const root = document.getElementById('nautilus-chart');
                const status = document.getElementById('nautilus-chart-status');

                if (!window.LightweightCharts) {
                  status.textContent = 'Chart library failed to load. Check internet/CDN access.';
                } else if (!payload.candles.length) {
                  status.textContent = 'No valid candles available.';
                } else {
                  const LC = window.LightweightCharts;
                  const chart = LC.createChart(root, {
                    autoSize: true,
                    height: 540,
                    layout: {
                      background: { type: 'solid', color: '#0e1117' },
                      textColor: '#d1d4dc'
                    },
                    grid: {
                      vertLines: { color: '#20242e' },
                      horzLines: { color: '#20242e' }
                    },
                    rightPriceScale: { borderColor: '#363a45' },
                    timeScale: { borderColor: '#363a45', timeVisible: true, secondsVisible: false },
                    crosshair: { mode: LC.CrosshairMode.Normal }
                  });

                  const candles = chart.addSeries(LC.CandlestickSeries, {
                    upColor: '#26a69a',
                    downColor: '#ef5350',
                    borderVisible: false,
                    wickUpColor: '#26a69a',
                    wickDownColor: '#ef5350'
                  });
                  candles.setData(payload.candles);

                  const volume = chart.addSeries(LC.HistogramSeries, {
                    priceFormat: { type: 'volume' },
                    priceScaleId: 'volume'
                  });
                  volume.setData(payload.candles.map(c => ({
                    time: c.time, value: c.volume, color: c.volumeColor
                  })));
                  chart.priceScale('volume').applyOptions({
                    scaleMargins: { top: 0.82, bottom: 0 }
                  });

                  const colors = {
                    'EMA 9': '#ffca28',
                    'EMA 20': '#42a5f5',
                    'EMA 50': '#ab47bc',
                    'EMA 200': '#ef8b2c'
                  };
                  payload.visibleIndicators.forEach(name => {
                    if (name.startsWith('EMA') && payload.overlays[name]) {
                      const line = chart.addSeries(LC.LineSeries, {
                        color: colors[name], lineWidth: 2, title: name,
                        priceLineVisible: false, lastValueVisible: true
                      });
                      line.setData(payload.overlays[name]);
                    }
                    if (name === 'Bollinger Bands') {
                      [
                        ['upper', '#78909c', 'BB Upper'],
                        ['middle', '#90a4ae', 'BB Middle'],
                        ['lower', '#78909c', 'BB Lower']
                      ].forEach(([key, color, title]) => {
                        const line = chart.addSeries(LC.LineSeries, {
                          color, lineWidth: 1, title,
                          priceLineVisible: false, lastValueVisible: false
                        });
                        line.setData(payload.overlays['Bollinger Bands'][key]);
                      });
                    }
                  });

                  const selected = payload.visibleIndicators || [];
                  if (selected.includes('RSI (14)')) {
                    document.getElementById('nautilus-rsi-title').style.display = 'block';
                    document.getElementById('nautilus-rsi-chart').style.display = 'block';
                    const rsiRoot = document.getElementById('nautilus-rsi-chart');
                    const rsiChart = LC.createChart(rsiRoot, {
                      autoSize: true, height: 170,
                      layout: { background: { type: 'solid', color: '#0e1117' }, textColor: '#d1d4dc' },
                      grid: { vertLines: { color: '#20242e' }, horzLines: { color: '#20242e' } },
                      rightPriceScale: { borderColor: '#363a45' },
                      timeScale: { visible: true, borderColor: '#363a45' }
                    });
                    const rsiSeries = rsiChart.addSeries(LC.LineSeries, {
                      color: '#ab47bc', lineWidth: 2, title: 'RSI 14'
                    });
                    rsiSeries.setData(payload.rsi);
                    [30, 70].forEach(level => {
                      rsiSeries.createPriceLine({
                        price: level, color: '#888888', lineWidth: 1,
                        lineStyle: LC.LineStyle.Dashed, axisLabelVisible: true,
                        title: String(level)
                      });
                    });
                    new ResizeObserver(entries => {
                      if (entries.length) rsiChart.applyOptions({ width: entries[0].contentRect.width });
                    }).observe(rsiRoot);
                  } else {
                    document.getElementById('nautilus-rsi-title').style.display = 'none';
                    document.getElementById('nautilus-rsi-chart').style.display = 'none';
                  }

                  if (selected.includes('MACD')) {
                    document.getElementById('nautilus-macd-title').style.display = 'block';
                    document.getElementById('nautilus-macd-chart').style.display = 'block';
                    const macdRoot = document.getElementById('nautilus-macd-chart');
                    const macdChart = LC.createChart(macdRoot, {
                      autoSize: true, height: 190,
                      layout: { background: { type: 'solid', color: '#0e1117' }, textColor: '#d1d4dc' },
                      grid: { vertLines: { color: '#20242e' }, horzLines: { color: '#20242e' } },
                      rightPriceScale: { borderColor: '#363a45' },
                      timeScale: { visible: true, borderColor: '#363a45' }
                    });
                    const macdSeries = macdChart.addSeries(LC.LineSeries, {
                      color: '#42a5f5', lineWidth: 2, title: 'MACD'
                    });
                    macdSeries.setData(payload.macd);
                    const signalSeries = macdChart.addSeries(LC.LineSeries, {
                      color: '#ffca28', lineWidth: 2, title: 'Signal'
                    });
                    signalSeries.setData(payload.macdSignal);
                    const histSeries = macdChart.addSeries(LC.HistogramSeries, {
                      title: 'Histogram', priceScaleId: 'hist'
                    });
                    histSeries.setData(payload.macdHistogram.map(point => ({
                      time: point.time, value: point.value,
                      color: point.value >= 0 ? '#26a69a' : '#ef5350'
                    })));
                    macdChart.priceScale('hist').applyOptions({
                      scaleMargins: { top: 0.7, bottom: 0 }
                    });
                    new ResizeObserver(entries => {
                      if (entries.length) macdChart.applyOptions({ width: entries[0].contentRect.width });
                    }).observe(macdRoot);
                  } else {
                    document.getElementById('nautilus-macd-title').style.display = 'none';
                    document.getElementById('nautilus-macd-chart').style.display = 'none';
                  }

                  chart.timeScale().fitContent();
                  new ResizeObserver(entries => {
                    if (entries.length) {
                      chart.applyOptions({ width: entries[0].contentRect.width });
                    }
                  }).observe(root);

                  status.textContent =
                    payload.selected + ' · ' + payload.timeframe +
                    ' · ' + payload.candles.length +
                    ' candles · chart data supplied by the configured data source';

                  const attribution = document.createElement('div');
                  attribution.style.cssText =
                    'text-align:right;font:11px sans-serif;padding-top:4px;';
                  attribution.innerHTML =
                    '<a href="https://www.tradingview.com/" target="_blank" ' +
                    'rel="noopener noreferrer" style="color:#9aa0aa;">Charts by TradingView</a>';
                  root.after(attribution);
                }
                </script>
                """
                _chart_html = _chart_html.replace(
                    "__PAYLOAD__", json.dumps(_chart_payload, separators=(",", ":"))
                )
                _chart_height = (
                    570
                    + (190 if "RSI (14)" in _index_indicators else 0)
                    + (210 if "MACD" in _index_indicators else 0)
                )
                components.html(_chart_html, height=_chart_height, scrolling=False)

                with st.expander(f"{_index_name} — full Quant + Algo output"):
                    st.markdown("**Quant engine**")
                    st.json(_idx_quant)
                    st.markdown("**Algo engine**")
                    st.json(_idx_algo)

                st.caption(
                    "Research information only; not a forecast or a validated trading signal. "
                    "Lightweight Charts is an interactive display library, not a market-data provider."
                )

    st.divider()
    # END NAUTILUS_LIGHTWEIGHT_INDEX_BOARD

    st.caption(
        "Research-only dashboard. Yahoo Finance is historical/delayed data, not a live feed. "
        "No orders, backtests or paper trades are run from this page."
    )

    with st.form("stock_intelligence_search"):
        query = st.text_input(
            "NSE/BSE ticker or company",
            value=st.session_state.get("stock_query", "RELIANCE"),
            placeholder="RELIANCE, TCS, INFY, RELIANCE.NS or company name",
        )
        a, b, c = st.columns(3)
        with a:
            history_interval = st.selectbox(
                "Chart candle interval", ["5m", "15m", "30m", "1h", "1d"], index=4
            )
        with b:
            if history_interval in ("5m", "15m", "30m"):
                period_options = ["1d", "5d", "1mo"]
                default_period_index = 1
            elif history_interval == "1h":
                period_options = ["5d", "1mo", "3mo", "6mo", "1y", "2y"]
                default_period_index = 4
            else:
                period_options = ["1mo", "3mo", "6mo", "1y", "2y", "5y"]
                default_period_index = 3
            saved_period = st.session_state.get("stock_period")
            selected_period_index = period_options.index(saved_period) if saved_period in period_options else default_period_index
            history_period = st.selectbox(
                "Chart history", period_options, index=selected_period_index
            )
        with c:
            st.markdown("**Source**")
            st.caption("Yahoo Finance · historical")
        submitted = st.form_submit_button("Analyze stock", type="primary", width="stretch")

    if submitted:
        st.session_state["stock_query"] = query
        st.session_state["stock_period"] = history_period
        st.session_state["stock_interval"] = history_interval
        st.session_state["stock_run"] = True

    if st.session_state.get("stock_run", False):
        query = st.session_state.get("stock_query", query)
        history_period = st.session_state.get("stock_period", history_period)
        history_interval = st.session_state.get("stock_interval", history_interval)

        try:
            with st.spinner("Resolving listing and loading historical candles…"):
                symbol, candidates = resolve_symbol(query)
                if candidates and len(candidates) > 1:
                    labels = {
                        f"{x['symbol']} — {x['name']} ({x['exchange']})": x["symbol"]
                        for x in candidates
                    }
                    selected = st.selectbox(
                        "Matching listings", list(labels.keys()),
                        key="stock_candidate_selection",
                    )
                    symbol = labels[selected]
                _, raw_frame = cached_yahoo_history(symbol, history_period, history_interval)
                frame = add_indicators(raw_frame)
                profile = cached_company_profile(symbol)
                info = profile.get("info", {}) or {}
        except Exception as exc:
            st.error(f"Stock analysis could not be loaded: {exc}")
            st.info(
                "Check the ticker, connection and Yahoo availability. "
                "Indian listings commonly use .NS (NSE) or .BO (BSE)."
            )
            st.stop()

        if frame.empty:
            st.error("No valid historical candles were returned.")
            st.stop()

        def _num(value):
            try:
                number = float(value)
                return number if pd.notna(number) and number not in (float("inf"), float("-inf")) else None
            except (TypeError, ValueError):
                return None

        def _shown(value, suffix="", divisor=1.0):
            number = _num(value)
            return "N/A" if number is None else fmt(number, suffix, divisor)

        def _pct(value):
            number = _num(value)
            return "N/A" if number is None else f"{number * 100:,.2f}%"

        def _technical_state(data, label):
            if data is None or data.empty:
                return {
                    "Horizon": label, "Bias": "DATA UNAVAILABLE",
                    "Evidence": "Historical candles could not be loaded.",
                    "Latest candle": "N/A", "Candles": 0,
                }
            last = data.iloc[-1]
            close = _num(last.get("close"))
            fast = _num(last.get("ema_9" if label == "Intraday" else "ema_20"))
            slow = _num(last.get("ema_20" if label == "Intraday" else "ema_50"))
            rsi = _num(last.get("rsi_14"))
            hist = _num(last.get("macd_hist"))
            adx = _num(last.get("adx_14"))
            if close is None or fast is None or slow is None:
                return {
                    "Horizon": label, "Bias": "INSUFFICIENT DATA",
                    "Evidence": "Need more valid candles for the selected indicators.",
                    "Latest candle": str(data.index[-1]), "Candles": len(data),
                }
            score = 0
            evidence = []
            if close > fast > slow:
                score += 1
                evidence.append("close > fast EMA > slow EMA")
            elif close < fast < slow:
                score -= 1
                evidence.append("close < fast EMA < slow EMA")
            else:
                evidence.append("moving averages mixed")
            if rsi is not None:
                if rsi >= 55:
                    score += 1
                    evidence.append(f"RSI {rsi:.1f} supports positive momentum")
                elif rsi <= 45:
                    score -= 1
                    evidence.append(f"RSI {rsi:.1f} supports negative momentum")
                else:
                    evidence.append(f"RSI {rsi:.1f} is in a middle zone")
            else:
                evidence.append("RSI unavailable")
            if hist is not None:
                if hist > 0:
                    score += 1
                    evidence.append("MACD histogram positive")
                elif hist < 0:
                    score -= 1
                    evidence.append("MACD histogram negative")
            else:
                evidence.append("MACD histogram unavailable")
            if adx is not None:
                evidence.append(f"ADX {adx:.1f}" + (" (trend strength elevated)" if adx >= 20 else " (trend strength modest)"))
            bias = "BULLISH BIAS" if score >= 2 else "BEARISH BIAS" if score <= -2 else "MIXED / NEUTRAL"
            return {
                "Horizon": label, "Bias": bias,
                "Evidence": "; ".join(evidence),
                "Latest candle": str(data.index[-1]), "Candles": len(data),
            }

        def _price_action(data):
            if data is None or data.empty or len(data) < 25:
                return {"Status": "INSUFFICIENT DATA", "Details": "At least 25 candles are needed for this descriptive structure check."}
            last = data.iloc[-1]
            prev = data.iloc[-2]
            close = _num(last.get("close"))
            prior_res = _num(data["high"].rolling(20, min_periods=20).max().shift(1).iloc[-1])
            prior_sup = _num(data["low"].rolling(20, min_periods=20).min().shift(1).iloc[-1])
            vol_ratio = _num(last.get("volume_ratio_20"))
            gap = ((_num(last.get("open")) / _num(prev.get("close"))) - 1) * 100 if _num(last.get("open")) is not None and _num(prev.get("close")) else None
            if prior_res is not None and close is not None and close > prior_res:
                status = "UPSIDE BREAKOUT CANDIDATE"
                detail = "Close exceeded the prior 20-candle high."
                detail += " Relative volume confirms activity." if vol_ratio is not None and vol_ratio >= 1.5 else " Relative volume is not >= 1.5x; breakout strength is unconfirmed."
            elif prior_sup is not None and close is not None and close < prior_sup:
                status = "DOWNSIDE BREAK CANDIDATE"
                detail = "Close fell below the prior 20-candle low."
                detail += " Relative volume confirms activity." if vol_ratio is not None and vol_ratio >= 1.5 else " Relative volume is not >= 1.5x; selling pressure is unconfirmed."
            else:
                status = "NO 20-CANDLE BREAKOUT"
                detail = "Close remains within the prior 20-candle high/low range."
            pattern = "No simple engulfing pattern detected"
            if len(data) >= 2:
                p_open, p_close = _num(prev.get("open")), _num(prev.get("close"))
                c_open, c_close = _num(last.get("open")), _num(last.get("close"))
                if None not in (p_open, p_close, c_open, c_close):
                    if p_close < p_open and c_close > c_open and c_open <= p_close and c_close >= p_open:
                        pattern = "Bullish engulfing candidate"
                    elif p_close > p_open and c_close < c_open and c_open >= p_close and c_close <= p_open:
                        pattern = "Bearish engulfing candidate"
            # Confirm pivots only after two candles to the right exist.
            highs, lows = data["high"].astype(float), data["low"].astype(float)
            pivot_highs, pivot_lows = [], []
            for i in range(2, len(data) - 2):
                if highs.iloc[i] >= highs.iloc[i-2:i+3].max():
                    pivot_highs.append((data.index[i], float(highs.iloc[i])))
                if lows.iloc[i] <= lows.iloc[i-2:i+3].min():
                    pivot_lows.append((data.index[i], float(lows.iloc[i])))
            structure = "Not enough confirmed swing pivots"
            if len(pivot_highs) >= 2 and len(pivot_lows) >= 2:
                hh = pivot_highs[-1][1] > pivot_highs[-2][1]
                hl = pivot_lows[-1][1] > pivot_lows[-2][1]
                lh = pivot_highs[-1][1] < pivot_highs[-2][1]
                ll = pivot_lows[-1][1] < pivot_lows[-2][1]
                if hh and hl:
                    structure = "Higher-high / higher-low structure"
                elif lh and ll:
                    structure = "Lower-high / lower-low structure"
                else:
                    structure = "Mixed swing structure"
                if close is not None and close > pivot_highs[-1][1]:
                    structure += " · close above last confirmed swing high (BOS candidate)"
                elif close is not None and close < pivot_lows[-1][1]:
                    structure += " · close below last confirmed swing low (BOS candidate)"
            return {
                "Status": status, "Details": detail,
                "Prior 20-candle resistance": prior_res,
                "Prior 20-candle support": prior_sup,
                "Gap vs previous close (%)": gap,
                "Relative volume (x)": vol_ratio,
                "Confirmed swing structure": structure,
                "Last candle pattern check": pattern,
            }

        company = info.get("longName") or info.get("shortName") or symbol
        last_bar = frame.iloc[-1]
        current = _num(last_bar.get("close"))
        prev = _num(frame["close"].iloc[-2]) if len(frame) > 1 else None
        change = ((current / prev) - 1) * 100 if current is not None and prev else None
        quality = quality_report(raw_frame)
        last_ts = pd.Timestamp(raw_frame.index[-1])
        st.markdown(f"### {company} · `{symbol}`")
        st.caption(
            f"Historical candles: {len(frame):,} · Range: {raw_frame.index.min()} to "
            f"{raw_frame.index.max()} · Latest candle timestamp: {last_ts} · "
            "The latest close is not guaranteed to be the current market price."
        )
        if len(frame) < 200:
            st.warning(f"Only {len(frame)} candles loaded. Long-period indicators such as SMA 200 may be unavailable or immature.")
        if quality.get("missing_values", 0) > 0 or quality.get("invalid_ohlc", 0) > 0:
            st.warning("Data-quality checks found missing values or invalid OHLC rows. Review the Data Quality section before relying on the analysis.")

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Latest loaded close", _shown(current, " INR"), f"{change:+.2f}% vs prior candle" if change is not None else "Change unavailable")
        m2.metric("Market cap", market_cap_label(info.get("marketCap")))
        m3.metric("Trailing P/E", _shown(info.get("trailingPE")))
        m4.metric("EPS (TTM)", _shown(info.get("trailingEps"), " INR"))
        m5.metric("Dividend yield", _pct(info.get("dividendYield")))

        # Independent history windows: these are separate candle datasets, not proxy labels.
        timeframe_specs = [
            ("Intraday", "5d", "5m"),
            ("Swing", "1y", "1d"),
            ("Positional", "5y", "1wk"),
        ]
        timeframe_frames = {"Selected chart": frame}
        timeframe_errors = {}
        with st.spinner("Building independent intraday, swing and positional views…"):
            for label, period, interval in timeframe_specs:
                if label == "Intraday" and history_interval == "5m" and history_period == "5d":
                    timeframe_frames[label] = frame
                    continue
                if label == "Swing" and history_interval == "1d" and history_period in ("1y", "2y", "5y"):
                    timeframe_frames[label] = frame
                    continue
                try:
                    _, tf_raw = cached_yahoo_history(symbol, period, interval)
                    timeframe_frames[label] = add_indicators(tf_raw)
                except Exception as exc:
                    timeframe_errors[label] = str(exc)
                    timeframe_frames[label] = pd.DataFrame()

        tf_rows = [
            _technical_state(timeframe_frames.get("Intraday"), "Intraday"),
            _technical_state(timeframe_frames.get("Swing"), "Swing"),
            _technical_state(timeframe_frames.get("Positional"), "Positional"),
        ]





        fundamentals_tab, chart_tab, timeframe_tab, ai_tab, financials_tab = st.tabs([
            "Fundamentals", "Technical Chart", "Multi-Timeframe", "AI Research Report", "Financial Statements",
        ])

        with fundamentals_tab:
            st.subheader("Valuation, profitability and business quality")
            fundamental_fields = [
                ("Sector", info.get("sector")),
                ("Industry", info.get("industry")),
                ("Exchange", info.get("exchange")),
                ("Currency", info.get("currency")),
                ("Trailing P/E", _shown(info.get("trailingPE"))),
                ("Forward P/E", _shown(info.get("forwardPE"))),
                ("Price / book", _shown(info.get("priceToBook"))),
                ("Book value", _shown(info.get("bookValue"), " INR")),
                ("Return on equity", _pct(info.get("returnOnEquity"))),
                ("Return on assets", _pct(info.get("returnOnAssets"))),
                ("Profit margin", _pct(info.get("profitMargins"))),
                ("Operating margin", _pct(info.get("operatingMargins"))),
                ("Revenue growth (provider)", _pct(info.get("revenueGrowth"))),
                ("Earnings growth (provider)", _pct(info.get("earningsGrowth"))),
                ("Debt / equity", _shown(info.get("debtToEquity"))),
                ("Free cash flow", _shown(info.get("freeCashflow"), " INR")),
                ("Operating cash flow", _shown(info.get("operatingCashflow"), " INR")),
                ("52-week high", _shown(info.get("fiftyTwoWeekHigh"), " INR")),
                ("52-week low", _shown(info.get("fiftyTwoWeekLow"), " INR")),
                ("Beta", _shown(info.get("beta"))),
                ("Shares outstanding", _shown(info.get("sharesOutstanding"))),
            ]
            left, right = st.columns(2)
            split = (len(fundamental_fields) + 1) // 2
            for col, subset in ((left, fundamental_fields[:split]), (right, fundamental_fields[split:])):
                with col:
                    st.dataframe(pd.DataFrame(subset, columns=["Metric", "Value"]), hide_index=True, width="stretch")
            st.caption("Provider values may be missing, stale or differently defined. N/A means no usable value was supplied; it does not mean zero. Verify important figures against exchange filings and company reports.")

            holders = profile.get("holders", {}) or {}
            st.subheader("Shareholding data")
            any_holders = False
            for holder_key, label in [
                ("major_holders", "Major holders"),
                ("institutional_holders", "Institutional holders"),
                ("mutualfund_holders", "Mutual fund holders"),
            ]:
                table = holders.get(holder_key)
                if isinstance(table, pd.DataFrame) and not table.empty:
                    any_holders = True
                    st.markdown(f"**{label}**")
                    st.dataframe(table, width="stretch", hide_index=True)
            if not any_holders:
                st.info("Shareholding breakdown was not supplied by this source.")

            st.subheader("Fundamental interpretation (rule-based, not a rating)")
            margin = _num(info.get("profitMargins"))
            debt_equity = _num(info.get("debtToEquity"))
            roe = _num(info.get("returnOnEquity"))
            notes = []
            if margin is not None:
                notes.append(f"Profit margin: {margin * 100:.2f}% (interpret relative to the company's sector and history).")
            else:
                notes.append("Profit margin: unavailable.")
            if debt_equity is not None:
                notes.append(f"Debt/equity reported as {debt_equity:.2f}; check provider units and compare with sector peers.")
            else:
                notes.append("Debt/equity: unavailable.")
            if roe is not None:
                notes.append(f"ROE: {roe * 100:.2f}%; compare with leverage and multi-year consistency.")
            else:
                notes.append("ROE: unavailable.")
            st.write("\n\n".join(notes))

        with chart_tab:
            st.subheader("Candles, trend and volume")
            try:
                import plotly.graph_objects as go
                from plotly.subplots import make_subplots
                chart = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.035,
                                      row_heights=[0.62, 0.20, 0.18])
                chart.add_trace(go.Candlestick(
                    x=frame.index, open=frame["open"], high=frame["high"],
                    low=frame["low"], close=frame["close"], name="Price",
                ), row=1, col=1)
                for key, label in [
                    ("ema_9", "EMA 9"), ("ema_20", "EMA 20"),
                    ("ema_50", "EMA 50"), ("sma_200", "SMA 200"),
                ]:
                    if key in frame and frame[key].notna().any():
                        chart.add_trace(go.Scatter(x=frame.index, y=frame[key], mode="lines", name=label), row=1, col=1)
                chart.add_trace(go.Bar(x=frame.index, y=frame["volume"], name="Volume", opacity=0.6), row=2, col=1)
                for key, label in [("rsi_14", "RSI 14"), ("macd_hist", "MACD histogram")]:
                    if key in frame and frame[key].notna().any():
                        chart.add_trace(go.Scatter(x=frame.index, y=frame[key], mode="lines", name=label), row=3, col=1)
                chart.update_layout(template="plotly_dark", height=820, paper_bgcolor="#101a2b",
                                    plot_bgcolor="#101a2b", xaxis_rangeslider_visible=False,
                                    legend_orientation="h", margin=dict(l=10, r=10, t=35, b=10))
                st.plotly_chart(chart, width="stretch")
            except ImportError:
                st.warning("Plotly is unavailable; showing fallback charts.")
                st.line_chart(frame[[c for c in ["close", "ema_20", "ema_50", "sma_200"] if c in frame]], width="stretch")
                st.bar_chart(frame[["volume"]], width="stretch")

            cols = st.columns(6)
            for col, label, key in zip(cols,
                ["RSI (14)", "MACD", "MACD histogram", "ATR (14)", "ADX (14)", "Relative volume"],
                ["rsi_14", "macd", "macd_hist", "atr_14", "adx_14", "volume_ratio_20"]):
                col.metric(label, _shown(last_bar.get(key), "x" if key == "volume_ratio_20" else ""))

            st.subheader("Calculated levels")
            levels = [
                ("20-candle rolling support", last_bar.get("rolling_support_20")),
                ("20-candle rolling resistance", last_bar.get("rolling_resistance_20")),
                ("Previous candle high", last_bar.get("previous_high")),
                ("Previous candle low", last_bar.get("previous_low")),
                ("EMA 20", last_bar.get("ema_20")),
                ("EMA 50", last_bar.get("ema_50")),
            ]
            st.dataframe(pd.DataFrame([{"Level": n, "Price": _shown(v, " INR")} for n, v in levels]), hide_index=True, width="stretch")
            if history_interval != "1d":
                st.caption("Session VWAP is grouped by the candle date in the provider timestamp. Confirm timezone/session boundaries; this is still historical provider data.")
                st.metric("Session VWAP (historical intraday)", _shown(last_bar.get("vwap_session"), " INR"))
            else:
                st.caption("Daily candles cannot provide a meaningful intraday session VWAP. VWAP is therefore not presented as an intraday signal on this daily chart.")
            st.subheader("Price action, breakout and gap checks")
            pa = _price_action(frame)
            st.json(pa)
            st.caption("Breakout and candle-pattern labels are descriptive heuristics. A breakout candidate can fail; they are not validated entries. Swing pivots require later candles for confirmation.")

            st.subheader("Relative strength vs NIFTY 50")
            try:
                _, nifty_raw = cached_yahoo_history("^NSEI", history_period, history_interval)
                stock_return = (float(raw_frame["close"].iloc[-1]) / float(raw_frame["close"].iloc[0]) - 1) * 100
                nifty_return = (float(nifty_raw["close"].iloc[-1]) / float(nifty_raw["close"].iloc[0]) - 1) * 100
                relative_return = stock_return - nifty_return
                rs1, rs2, rs3 = st.columns(3)
                rs1.metric("Stock return over loaded range", f"{stock_return:+.2f}%")
                rs2.metric("NIFTY 50 return over loaded range", f"{nifty_return:+.2f}%")
                rs3.metric("Relative performance", f"{relative_return:+.2f} pp")
                st.caption("Calculated from the first and last loaded closes, not a live index feed. Different trading calendars or missing bars can affect comparability.")
            except Exception as exc:
                st.info(f"Relative-strength comparison unavailable: {exc}")

            st.subheader("Data quality")
            st.json(quality)
            st.markdown("**Latest calculated rows**")
            columns = [c for c in [
                "open", "high", "low", "close", "volume", "ema_9", "ema_20", "ema_50",
                "sma_200", "rsi_14", "macd", "macd_signal", "macd_hist", "atr_14", "adx_14",
                "volume_ratio_20",
            ] if c in frame]
            st.dataframe(frame[columns].tail(30), width="stretch")

        with timeframe_tab:
            st.subheader("Independent timeframe views")
            st.caption("Intraday uses 5-minute candles, swing uses daily candles, and positional uses weekly candles. Each view is calculated from its own fetched dataset; it is not a forecast or validated trading signal.")

            # Quant + Algo engines: descriptive research only, no orders or predictions.
            st.subheader("Quant + Algo Research")
            st.caption(
                "Uses each timeframe's own candles. NIFTY 50 (^NSEI) is fetched "
                "at the matching interval for benchmark-aware metrics where available. "
                "Rule labels and historical statistics are not validated forecasts."
            )

            qa_rows = []
            qa_details = {}
            benchmark_cache = {}

            def _qa_pick(payload, candidates, default="—"):
                if not isinstance(payload, dict):
                    return default
                for key in candidates:
                    value = payload.get(key)
                    if value is not None and value != "":
                        return value
                return default

            for _qa_label, _qa_period, _qa_interval in timeframe_specs:
                _qa_frame = timeframe_frames.get(_qa_label, pd.DataFrame())
                _qa_quant = {}
                _qa_algo = {}
                _qa_errors = []

                if _qa_frame is None or _qa_frame.empty:
                    _qa_errors.append("No timeframe candles available.")
                else:
                    try:
                        _qa_bkey = (_qa_period, _qa_interval)
                        if _qa_bkey not in benchmark_cache:
                            try:
                                _, _qa_bench_raw = cached_yahoo_history(
                                    "^NSEI", _qa_period, _qa_interval
                                )
                                benchmark_cache[_qa_bkey] = _qa_bench_raw
                            except Exception as _qa_exc:
                                benchmark_cache[_qa_bkey] = None
                                _qa_errors.append(
                                    f"NIFTY benchmark unavailable: {_qa_exc}"
                                )

                        _qa_benchmark = benchmark_cache.get(_qa_bkey)
                        _qa_quant = quant_engine(
                            _qa_frame, benchmark=_qa_benchmark
                        )
                        if not isinstance(_qa_quant, dict):
                            _qa_quant = {"result": str(_qa_quant)}
                    except Exception as _qa_exc:
                        _qa_errors.append(f"Quant engine: {_qa_exc}")

                    try:
                        _qa_algo = algo_engine(_qa_frame)
                        if not isinstance(_qa_algo, dict):
                            _qa_algo = {"result": str(_qa_algo)}
                    except Exception as _qa_exc:
                        _qa_errors.append(f"Algo engine: {_qa_exc}")

                _qa_regime = _qa_pick(
                    _qa_quant, ("regime", "market_regime", "regime_label", "status")
                )
                _qa_decision = _qa_pick(
                    _qa_algo, ("decision", "signal", "label", "status")
                )
                _qa_score = _qa_pick(
                    _qa_algo, ("rule_score", "score", "confluence_score")
                )

                qa_rows.append({
                    "Timeframe": _qa_label,
                    "Candles": len(_qa_frame) if _qa_frame is not None else 0,
                    "Quant regime/status": _qa_regime,
                    "Algo status": _qa_pick(_qa_algo, ("status",)),
                    "Algo research bias": _qa_decision,
                    "Rule score": _qa_score,
                    "Notes": "; ".join(_qa_errors) if _qa_errors else "—",
                })
                qa_details[_qa_label] = {
                    "Quant": _qa_quant,
                    "Algo": _qa_algo,
                    "Notes": _qa_errors,
                }

            st.dataframe(pd.DataFrame(qa_rows), hide_index=True, width="stretch")
            for _qa_label in ("Intraday", "Swing", "Positional"):
                with st.expander(f"{_qa_label}: Quant + Algo details"):
                    st.json(qa_details.get(_qa_label, {}))
            st.caption(
                "No probability of profit, predictive confidence, backtest result, "
                "paper trade or order execution is generated by this section."
            )

            st.dataframe(pd.DataFrame(tf_rows), hide_index=True, width="stretch")
            if timeframe_errors:
                with st.expander("Timeframe fetch warnings"):
                    for label, error in timeframe_errors.items():
                        st.warning(f"{label}: {error}")
            for label in ["Intraday", "Swing", "Positional"]:
                data = timeframe_frames.get(label, pd.DataFrame())
                if data is not None and not data.empty:
                    with st.expander(f"{label}: indicator detail"):
                        st.write(f"Candles: {len(data)} · Latest timestamp: {data.index[-1]}")
                        last = data.iloc[-1]
                        st.json({
                            "Close": _num(last.get("close")),
                            "EMA 9": _num(last.get("ema_9")),
                            "EMA 20": _num(last.get("ema_20")),
                            "EMA 50": _num(last.get("ema_50")),
                            "SMA 200": _num(last.get("sma_200")),
                            "RSI 14": _num(last.get("rsi_14")),
                            "MACD histogram": _num(last.get("macd_hist")),
                            "ATR 14": _num(last.get("atr_14")),
                            "ADX 14": _num(last.get("adx_14")),
                            "Relative volume": _num(last.get("volume_ratio_20")),
                        })
            st.warning("No prediction accuracy, probability of profit or confidence score is shown: the current model has not been validated for this stock/timeframe with a suitable out-of-sample evaluation.")

        with ai_tab:
            st.subheader("Evidence-based AI research report")
            st.caption("Quantitative indicators are computed in Python. AI may explain the evidence but cannot turn missing data into facts or produce a validated prediction.")
            provider_mode = st.selectbox(
                "Analysis engine",
                ["Hybrid auto (local Ollama, then configured cloud)", "Local Ollama only", "Rules-only (no AI call)"],
                key="stock_ai_provider_mode",
            )
            model_local = os.getenv("OLLAMA_MODEL", "llama3:8b")
            model_cloud = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            st.caption(f"Local model setting: {model_local} · Cloud model setting: {model_cloud if os.getenv('OPENAI_API_KEY') else 'not configured (OPENAI_API_KEY missing)'}")

            fundamentals_payload = {
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "trailingPE": _num(info.get("trailingPE")),
                "forwardPE": _num(info.get("forwardPE")),
                "profitMargins": _num(info.get("profitMargins")),
                "operatingMargins": _num(info.get("operatingMargins")),
                "revenueGrowth": _num(info.get("revenueGrowth")),
                "earningsGrowth": _num(info.get("earningsGrowth")),
                "debtToEquity": _num(info.get("debtToEquity")),
                "returnOnEquity": _num(info.get("returnOnEquity")),
                "freeCashflow": _num(info.get("freeCashflow")),
            }
            research_payload = {
                "company": company, "symbol": symbol,
                "source": "Yahoo Finance historical data; not a live feed",
                "chart_interval": history_interval, "chart_period": history_period,
                "latest_candle_timestamp": str(raw_frame.index[-1]),
                "latest_loaded_close": current, "change_vs_prior_candle_pct": change,
                "data_quality": quality, "timeframe_analysis": tf_rows,
                "chart_indicators": {
                    key: _num(last_bar.get(key)) for key in [
                        "ema_9", "ema_20", "ema_50", "sma_200", "rsi_14",
                        "macd", "macd_signal", "macd_hist", "atr_14", "adx_14",
                        "volume_ratio_20", "rolling_support_20", "rolling_resistance_20",
                    ]
                },
                "fundamentals": fundamentals_payload,
                "limits": [
                    "No validated prediction model or strategy performance available.",
                    "No live feed; historical provider timestamps only.",
                    "Some fundamentals may be missing or stale.",
                    "This is not a buy/sell instruction.",
                ],
            }

            def _rules_report(payload):
                rows = payload["timeframe_analysis"]
                bias_counts = {}
                for row in rows:
                    bias_counts[row["Bias"]] = bias_counts.get(row["Bias"], 0) + 1
                return (
                    "## Rule-based evidence summary\n"
                    f"- Instrument: {payload['company']} ({payload['symbol']})\n"
                    f"- Latest loaded close: {payload['latest_loaded_close']} (historical, not live)\n"
                    f"- Candle timestamp: {payload['latest_candle_timestamp']}\n"
                    f"- Timeframe results: {json.dumps(rows, ensure_ascii=False)}\n"
                    f"- Fundamentals supplied: {json.dumps(payload['fundamentals'], ensure_ascii=False)}\n"
                    f"- Cross-timeframe tally: {json.dumps(bias_counts, ensure_ascii=False)}\n"
                    "- Interpretation: mixed signals should be treated as uncertainty, not forced into a directional call.\n"
                    "- No entry, target, win probability or confidence score is validated by this report.\n"
                )

            if st.button("Generate research report", type="primary", key="generate_stock_ai_report"):
                report_text = None
                report_source = "Rules-only fallback"
                prompt = (
                    "You are a cautious equity research assistant. Explain only the JSON evidence below. "
                    "Do not invent facts, news, prices, indicators, or financial figures. Treat null as unavailable. "
                    "State bullish/bearish/mixed evidence, conflicts, risks, data quality limitations, and what should be verified. "
                    "Do not give a guaranteed forecast, invented confidence/probability, or claim this is a validated strategy. "
                    "Make clear the market data is historical and not live. No order execution. "
                    "Return concise Markdown with sections: Summary, Evidence by timeframe, Fundamentals, Conflicts and risks, Missing data, Conclusion.\n\n"
                    + json.dumps(research_payload, ensure_ascii=False, default=str)
                )
                if provider_mode != "Rules-only (no AI call)":
                    try:
                        import requests
                    except ImportError:
                        requests = None
                    if requests is not None:
                        if provider_mode.startswith("Hybrid"):
                            try:
                                response = requests.post(
                                    os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/") + "/api/generate",
                                    json={"model": model_local, "prompt": prompt, "stream": False},
                                    timeout=35,
                                )
                                response.raise_for_status()
                                answer = response.json().get("response", "").strip()
                                if answer:
                                    report_text, report_source = answer, f"Local Ollama · {model_local}"
                            except Exception as exc:
                                st.info(f"Local AI unavailable; trying configured cloud fallback. ({exc})")
                        if report_text is None and os.getenv("OPENAI_API_KEY") and provider_mode.startswith("Hybrid"):
                            try:
                                response = requests.post(
                                    os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions",
                                    headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"], "Content-Type": "application/json"},
                                    json={"model": model_cloud, "messages": [
                                        {"role": "system", "content": "You are a cautious, evidence-grounded equity research analyst. Never invent data."},
                                        {"role": "user", "content": prompt},
                                    ], "temperature": 0.2},
                                    timeout=40,
                                )
                                response.raise_for_status()
                                answer = response.json()["choices"][0]["message"]["content"].strip()
                                if answer:
                                    report_text, report_source = answer, f"Configured cloud AI · {model_cloud}"
                            except Exception as exc:
                                st.warning(f"Cloud AI request failed: {exc}")
                        if report_text is None and provider_mode == "Local Ollama only":
                            try:
                                response = requests.post(
                                    os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/") + "/api/generate",
                                    json={"model": model_local, "prompt": prompt, "stream": False},
                                    timeout=35,
                                )
                                response.raise_for_status()
                                answer = response.json().get("response", "").strip()
                                if answer:
                                    report_text, report_source = answer, f"Local Ollama · {model_local}"
                            except Exception as exc:
                                st.warning(f"Local Ollama request failed: {exc}")
                if report_text is None:
                    report_text = _rules_report(research_payload)
                st.session_state["stock_ai_report_text"] = report_text
                st.session_state["stock_ai_report_source"] = report_source
                st.session_state["stock_ai_report_symbol"] = symbol

            if st.session_state.get("stock_ai_report_symbol") == symbol and st.session_state.get("stock_ai_report_text"):
                st.caption("Report engine: " + st.session_state.get("stock_ai_report_source", "unknown"))
                st.markdown(st.session_state["stock_ai_report_text"])
                st.download_button(
                    "Download research report (.md)",
                    data=st.session_state["stock_ai_report_text"],
                    file_name=f"{symbol.replace('.', '_')}_research_report.md",
                    mime="text/markdown",
                )
            st.info("AI text is an interpretation of supplied evidence, not a verified prediction. Verify important financial facts against company/exchange filings.")

        with financials_tab:
            st.subheader("Annual and quarterly statements")
            for key, label in [
                ("annual", "Annual income statement"),
                ("quarterly", "Quarterly income statement"),
                ("balance_sheet", "Balance sheet"),
                ("cash_flow", "Cash flow"),
                ("quarterly_balance_sheet", "Quarterly balance sheet"),
                ("quarterly_cash_flow", "Quarterly cash flow"),
            ]:
                statement = profile.get(key)
                with st.expander(label):
                    if isinstance(statement, pd.DataFrame) and not statement.empty:
                        st.dataframe(statement, width="stretch")
                    else:
                        st.info("This statement is unavailable from the current provider.")
            annual = profile.get("annual")
            if isinstance(annual, pd.DataFrame) and not annual.empty:
                st.subheader("Available annual financial trend rows")
                selected_rows = [
                    idx for idx in annual.index
                    if any(term in str(idx).lower() for term in [
                        "total revenue", "operating revenue", "net income", "net profit",
                        "operating income", "gross profit", "diluted eps",
                    ])
                ]
                if selected_rows:
                    st.dataframe(annual.loc[selected_rows], width="stretch")
                else:
                    st.caption("No recognizable revenue/profit rows were supplied; see the full annual statement above.")

        st.caption("Important: technical bias is a descriptive rule output. No historical win rate, model accuracy, target probability or investment recommendation is asserted.")
elif page == "API Explorer":
    section("API & integration explorer", "CONFIGURATION VISIBILITY · NO SECRET VALUES")
    st.caption("This page intentionally does not print API keys, tokens or credentials.")
    env_names = [
        "ALPACA_API_KEY", "ALPACA_SECRET_KEY", "UPSTOX_API_KEY",
        "FYERS_APP_ID", "ANGELONE_API_KEY", "KITE_API_KEY",
        "TELEGRAM_BOT_TOKEN", "GEMINI_API_KEY", "OPENAI_API_KEY",
    ]
    import os
    st.dataframe(pd.DataFrame([{
        "Integration variable": name,
        "Configured in environment": "Yes" if os.getenv(name) else "No",
        "Value": "••••••••" if os.getenv(name) else "Not set",
    } for name in env_names]), width="stretch", hide_index=True)
    section("Detected integration modules", "IMPORT AVAILABILITY")
    for name, mod in [
        ("Yahoo Finance", "yfinance"),
        ("HTTP client", "requests"),
        ("Broker SDK: Kite", "kiteconnect"),
        ("Broker SDK: Upstox", "upstox_client"),
        ("Telegram bot", "telegram"),
    ]:
        try:
            __import__(mod)
            ok = True
        except Exception:
            ok = False
        st.markdown(
            f'<div class="panel" style="margin-bottom:8px;padding:12px 16px">'
            f'<b>{name}</b><span style="float:right" class="{"status-good" if ok else "status-warn"}">'
            f'{"AVAILABLE" if ok else "NOT DETECTED"}</span></div>',
            unsafe_allow_html=True,
        )
    st.info("No broker connection or live order placement is performed by this page.")


# ─────────────────────── MULTI-STOCK SCANNER ────────────────────
elif page == "Multi-Stock Scanner":
    section("Multi-stock scanner", "NSE EQUITIES · HISTORICAL DATA · RULE-BASED RESEARCH")
    st.caption("Scanner signals are simple SMA research labels, not AI predictions or trade recommendations. Yahoo Finance data may be delayed or incomplete.")

    defaults = "RELIANCE.NS, HDFCBANK.NS, ICICIBANK.NS, SBIN.NS, INFY.NS, TCS.NS, BHARTIARTL.NS, ITC.NS, LT.NS, TATAMOTORS.NS"
    with st.form("multi_stock_scanner_form"):
        symbols_text = st.text_area("Symbols (comma-separated)", value=st.session_state.get("scanner_symbols", defaults), height=90)
        a, b, c = st.columns(3)
        period = a.selectbox("History", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)
        fast_period = b.number_input("Fast SMA", min_value=2, max_value=50, value=5)
        slow_period = c.number_input("Slow SMA", min_value=5, max_value=200, value=20)
        run_scan = st.form_submit_button("Run scanner", type="primary", width="stretch")

    if run_scan:
        symbols = list(dict.fromkeys(s.strip().upper() for s in symbols_text.split(",") if s.strip()))[:40]
        st.session_state["scanner_symbols"] = symbols_text
        if fast_period >= slow_period:
            st.error("Fast SMA must be smaller than Slow SMA.")
        elif not symbols:
            st.error("Enter at least one ticker symbol.")
        else:
            try:
                import yfinance as yf
                results = []
                progress = st.progress(0, text="Fetching historical data…")
                for idx, symbol in enumerate(symbols, start=1):
                    try:
                        ticker = symbol if "." in symbol else f"{symbol}.NS"
                        hist = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=True, timeout=12)
                        if hist.empty or "Close" not in hist:
                            results.append({"Symbol": ticker, "Price": None, "SMA Fast": None, "SMA Slow": None, "Signal": "NO DATA", "As of": "—", "Reason": "No historical bars returned"})
                        else:
                            close = pd.to_numeric(hist["Close"], errors="coerce").dropna()
                            sf = close.rolling(int(fast_period)).mean()
                            ss = close.rolling(int(slow_period)).mean()
                            price = float(close.iloc[-1])
                            fast_value = float(sf.iloc[-1]) if pd.notna(sf.iloc[-1]) else None
                            slow_value = float(ss.iloc[-1]) if pd.notna(ss.iloc[-1]) else None
                            if fast_value is None or slow_value is None:
                                signal, reason = "WAIT", "Not enough bars for both averages"
                            elif price > fast_value > slow_value:
                                signal, reason = "BULLISH", "Close > fast SMA > slow SMA"
                            elif price < fast_value < slow_value:
                                signal, reason = "BEARISH", "Close < fast SMA < slow SMA"
                            else:
                                signal, reason = "WAIT", "SMA conditions do not align"
                            results.append({"Symbol": ticker, "Price": price, "SMA Fast": fast_value, "SMA Slow": slow_value, "Signal": signal, "As of": str(hist.index[-1]), "Reason": reason})
                    except Exception as exc:
                        results.append({"Symbol": symbol, "Price": None, "SMA Fast": None, "SMA Slow": None, "Signal": "ERROR", "As of": "—", "Reason": str(exc)[:160]})
                    progress.progress(idx / len(symbols), text=f"Scanned {idx}/{len(symbols)}")
                progress.empty()
                scan_df = pd.DataFrame(results)
                st.session_state["scanner_results"] = scan_df
                record_app_event("multi-stock-scanner", f"Scanned {len(scan_df)} symbols", f"period={period}; fast_sma={int(fast_period)}; slow_sma={int(slow_period)}; bullish={int((scan_df['Signal'] == 'BULLISH').sum())}; bearish={int((scan_df['Signal'] == 'BEARISH').sum())}")
                st.session_state["scanner_period"] = period
                st.session_state["scanner_fast"] = int(fast_period)
                st.session_state["scanner_slow"] = int(slow_period)
            except Exception as exc:
                st.error(f"Scanner could not start: {exc}. Check that yfinance is installed.")

    scan_df = st.session_state.get("scanner_results", pd.DataFrame())
    if isinstance(scan_df, pd.DataFrame) and not scan_df.empty:
        bullish = int((scan_df["Signal"] == "BULLISH").sum())
        bearish = int((scan_df["Signal"] == "BEARISH").sum())
        waiting = int(scan_df["Signal"].isin(["WAIT", "NO DATA", "ERROR"]).sum())
        a, b, c, d = st.columns(4)
        a.metric("Stocks scanned", len(scan_df))
        b.metric("Bullish", bullish)
        c.metric("Bearish", bearish)
        d.metric("Wait / unavailable", waiting)
        filter_signal = st.selectbox("Filter", ["ALL", "BULLISH", "BEARISH", "WAIT", "NO DATA", "ERROR"])
        view = scan_df if filter_signal == "ALL" else scan_df[scan_df["Signal"] == filter_signal]
        st.dataframe(view, width="stretch", hide_index=True, column_config={
            "Price": st.column_config.NumberColumn("Price (₹)", format="₹%.2f"),
            "SMA Fast": st.column_config.NumberColumn("Fast SMA (₹)", format="₹%.2f"),
            "SMA Slow": st.column_config.NumberColumn("Slow SMA (₹)", format="₹%.2f"),
        })
        st.download_button("Download scanner CSV", scan_df.to_csv(index=False).encode("utf-8"), file_name="nautilus_scanner_results.csv", mime="text/csv")
        available = scan_df.loc[scan_df["Signal"].isin(["BULLISH", "BEARISH", "WAIT"]), "Symbol"].tolist()
        if available:
            chart_symbol = st.selectbox("Chart a scanned stock", available)
            try:
                import yfinance as yf
                chart = yf.Ticker(chart_symbol).history(period="3mo", interval="1d", auto_adjust=True, timeout=12)
                if not chart.empty:
                    chart["SMA Fast"] = chart["Close"].rolling(int(st.session_state.get("scanner_fast", 5))).mean()
                    chart["SMA Slow"] = chart["Close"].rolling(int(st.session_state.get("scanner_slow", 20))).mean()
                    st.line_chart(chart[["Close", "SMA Fast", "SMA Slow"]])
            except Exception as exc:
                st.caption(f"Chart unavailable: {exc}")
    else:
        st.info("Run the scanner to populate the results table. No data is invented when a symbol cannot be fetched.")


# ───────────────────── LEARNING & MISTAKES ──────────────────────
elif page == "Learning & Mistakes":
    section("Learning & mistakes", "PERSISTENT NOTES · OUTCOME REVIEW · NO AUTO-RETRAINING")
    st.caption("This journal stores your review notes. It does not automatically modify or retrain any model.")
    journal_dir = ROOT / "data/research"
    journal_dir.mkdir(parents=True, exist_ok=True)
    db_path = journal_dir / "learning_journal.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
            symbol TEXT NOT NULL, horizon TEXT, setup TEXT, prediction TEXT,
            actual_outcome TEXT, mistake_type TEXT, lesson TEXT NOT NULL, next_action TEXT
        )""")
        conn.commit()

    metric_row([
        ("Saved lessons", int(pd.read_sql_query("SELECT COUNT(*) AS n FROM lessons", sqlite3.connect(db_path)).iloc[0]["n"]), "SQLite journal"),
        ("Prediction records", len(predictions), "predictions.jsonl"),
        ("Outcome records", len(outcomes), "outcomes.jsonl"),
    ])
    with st.form("lesson_form", clear_on_submit=True):
        st.subheader("Record a lesson")
        a, b, c = st.columns(3)
        symbol = a.text_input("Symbol", placeholder="RELIANCE.NS").strip().upper()
        horizon = b.selectbox("Horizon", ["1m", "5m", "15m", "30m", "60m", "240m", "Swing", "Positional", "Other"])
        setup = c.text_input("Setup / strategy", placeholder="Describe the setup")
        a, b = st.columns(2)
        prediction = a.selectbox("Original prediction", ["UP", "DOWN", "FLAT", "NO_MODEL", "Not recorded"])
        actual = b.selectbox("Observed outcome", ["UP", "DOWN", "FLAT", "Unknown / not matured"])
        mistake_type = st.selectbox("Review category", ["No mistake identified", "False signal", "Late entry", "Early exit", "Risk sizing", "Data quality", "Model unavailable", "Overtrading", "Other"])
        lesson = st.text_area("What did you learn?", placeholder="Write the evidence-based lesson…")
        next_action = st.text_input("Next action", placeholder="e.g. test on a separate period")
        save_lesson = st.form_submit_button("Save lesson", type="primary", width="stretch")
    if save_lesson:
        if not symbol or not lesson.strip():
            st.error("Symbol and lesson are required.")
        else:
            with sqlite3.connect(db_path) as conn:
                conn.execute("INSERT INTO lessons (created_at,symbol,horizon,setup,prediction,actual_outcome,mistake_type,lesson,next_action) VALUES (?,?,?,?,?,?,?,?,?)", (datetime.now().isoformat(timespec="seconds"), symbol, horizon, setup, prediction, actual, mistake_type, lesson.strip(), next_action))
                conn.commit()
            record_app_event("learning-journal", f"Lesson saved for {symbol}", f"horizon={horizon}; review={mistake_type}")
            st.success("Lesson saved to the local journal.")
            st.rerun()

    lessons = pd.read_sql_query("SELECT * FROM lessons ORDER BY id DESC", sqlite3.connect(db_path))
    section("Saved learning history", "USER-RECORDED · NOT MODEL TRAINING DATA BY DEFAULT")
    if not lessons.empty:
        st.dataframe(lessons, width="stretch", hide_index=True)
        st.download_button("Export learning journal CSV", lessons.to_csv(index=False).encode("utf-8"), file_name="nautilus_learning_journal.csv", mime="text/csv")
    else:
        st.info("No lessons saved yet.")
    for title, frame in (("Latest actual outcomes", outcomes), ("Latest predictions", predictions)):
        with st.expander(f"Inspect {title.lower()} · {len(frame)} records"):
            if frame.empty:
                st.caption("No records available.")
            else:
                st.dataframe(frame.tail(50), width="stretch", hide_index=True)


# ───────────────────────── TRADE JOURNAL ────────────────────────
elif page == "Trade Journal":
    section("Trade journal", "MANUAL ENTRIES · REVIEWABLE P&L · NO BROKER SYNC")
    st.caption("Record trades you place manually. P&L below is gross and excludes brokerage, taxes, slippage and funding costs.")
    journal_dir = ROOT / "data/research"
    journal_dir.mkdir(parents=True, exist_ok=True)
    db_path = journal_dir / "learning_journal.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
            trade_date TEXT, symbol TEXT NOT NULL, side TEXT NOT NULL, setup TEXT,
            entry REAL, stop REAL, exit_price REAL, quantity REAL, gross_pnl REAL,
            notes TEXT
        )""")
        conn.commit()
    with st.form("manual_trade_form", clear_on_submit=True):
        a, b, c = st.columns(3)
        trade_date = a.date_input("Trade date", value=datetime.now().date())
        symbol = b.text_input("Symbol", placeholder="NIFTY / RELIANCE.NS").strip().upper()
        side = c.selectbox("Side", ["BUY", "SELL"])
        a, b, c, d = st.columns(4)
        entry = a.number_input("Entry price", min_value=0.0, value=0.0, format="%.2f")
        stop = b.number_input("Stop / invalidation", min_value=0.0, value=0.0, format="%.2f")
        exit_price = c.number_input("Exit price", min_value=0.0, value=0.0, format="%.2f")
        quantity = d.number_input("Quantity", min_value=0.0, value=0.0, format="%.4f")
        setup = st.text_input("Setup / timeframe")
        notes = st.text_area("Notes / review")
        save_trade = st.form_submit_button("Save trade", type="primary", width="stretch")
    if save_trade:
        if not symbol:
            st.error("Symbol is required.")
        else:
            pnl = None
            if entry > 0 and exit_price > 0 and quantity > 0:
                pnl = (exit_price - entry) * quantity if side == "BUY" else (entry - exit_price) * quantity
            with sqlite3.connect(db_path) as conn:
                conn.execute("INSERT INTO trades (created_at,trade_date,symbol,side,setup,entry,stop,exit_price,quantity,gross_pnl,notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (datetime.now().isoformat(timespec="seconds"), str(trade_date), symbol, side, setup, entry or None, stop or None, exit_price or None, quantity or None, pnl, notes))
                conn.commit()
            record_app_event("trade-journal", f"Trade saved for {symbol}", f"side={side}; gross_pnl={pnl}")
            st.success("Trade saved locally.")
            st.rerun()

    trades = pd.read_sql_query("SELECT * FROM trades ORDER BY id DESC", sqlite3.connect(db_path))
    if not trades.empty:
        closed = trades[trades["gross_pnl"].notna()]
        a, b, c, d = st.columns(4)
        a.metric("Journal entries", len(trades))
        b.metric("Closed trades", len(closed))
        c.metric("Gross P&L", f"₹{closed['gross_pnl'].sum():,.2f}" if not closed.empty else "—")
        d.metric("Win rate", f"{(closed['gross_pnl'] > 0).mean() * 100:.1f}%" if not closed.empty else "—")
        st.dataframe(trades, width="stretch", hide_index=True)
        st.download_button("Export trade journal CSV", trades.to_csv(index=False).encode("utf-8"), file_name="nautilus_trade_journal.csv", mime="text/csv")
    else:
        st.info("No manual trades recorded yet.")


# ───────────────────────── FOOTER ───────────────────────────────
st.markdown("""
<div class="footer">
  <b style="color:#9fb5d2">NAUTILUS TRADING INTELLIGENCE PRO</b>
  <span> · Research-first architecture · Local data control · Manual execution boundary</span><br>
  Metrics describe detected files and records; they do not independently validate data freshness,
  model quality, profitability or exchange connectivity.
</div>
""", unsafe_allow_html=True)
