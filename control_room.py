from pathlib import Path
from datetime import datetime
import json
import sys
import time

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

for folder in [
    "data/market", "data/live", "data/training", "data/research",
    "data/backtests", "results/backtests", "models/live", "reports"
]:
    (ROOT / folder).mkdir(parents=True, exist_ok=True)


# ───────────────────────── PAGE CONFIG ─────────────────────────
st.set_page_config(
    page_title="NAUTILUS | AI Trading Intelligence",
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
                    frame = fetch_yahoo(symbol.strip(), period, interval)
                if frame is None or frame.empty:
                    st.warning("No candles returned. Check the symbol, interval and source availability.")
                else:
                    out = ROOT / "data/market" / f"{symbol.strip().replace('/', '_')}_{interval}_{period}.parquet"
                    frame.to_parquet(out, index=False)
                    st.success(f"Saved {len(frame):,} rows to {out.relative_to(ROOT)}")
                    st.dataframe(frame.tail(20), width="stretch", hide_index=True)
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
    from src.stock_intelligence import (
        resolve_symbol, fetch_profile, add_indicators, fmt, market_cap_label,
    )

    section("Stock Intelligence", "FUNDAMENTALS · TECHNICALS · EXISTING AI PIPELINE")
    st.caption(
        "Yahoo Finance data can be delayed, incomplete or unavailable. "
        "This workspace is research-only; it does not place orders."
    )

    with st.form("stock_intelligence_search"):
        query = st.text_input(
            "Search NSE/BSE ticker or company",
            value=st.session_state.get("stock_query", "RELIANCE"),
            placeholder="RELIANCE, TCS, INFY or company name",
        )
        a, b, c = st.columns(3)
        with a:
            history_period = st.selectbox(
                "Historical range", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=3
            )
        with b:
            history_interval = st.selectbox(
                "Chart interval", ["5m", "15m", "30m", "1h", "1d"], index=4
            )
        with c:
            st.markdown("**Market data**")
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
            with st.spinner("Resolving symbol and loading historical market data…"):
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

                from src.market_data import fetch_yahoo, quality_report
                _, raw_frame = fetch_yahoo(symbol, history_period, history_interval)
                frame = add_indicators(raw_frame)
                profile = fetch_profile(symbol)
                info = profile.get("info", {})
        except Exception as exc:
            st.error(f"Stock analysis could not be loaded: {exc}")
            st.info(
                "Check the ticker, internet connection and Yahoo Finance availability. "
                "For Indian listings, try RELIANCE.NS or a BSE ticker ending in .BO."
            )
            st.stop()

        company = info.get("longName") or info.get("shortName") or symbol
        current = float(frame["close"].iloc[-1])
        previous = float(frame["close"].iloc[-2]) if len(frame) > 1 else current
        change = (current / previous - 1) * 100 if previous else 0
        last_bar = frame.iloc[-1]
        quality = quality_report(raw_frame)

        st.markdown(f"### {company}  ·  `{symbol}`")
        st.caption(
            f"Loaded {len(frame):,} candles · {raw_frame.index.min()} to "
            f"{raw_frame.index.max()} · Source: Yahoo Finance historical data"
        )

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Latest loaded close", fmt(current, " INR"), f"{change:+.2f}% vs prior bar")
        m2.metric("Market cap", market_cap_label(info.get("marketCap")))
        m3.metric("P/E (trailing)", fmt(info.get("trailingPE")))
        m4.metric("EPS (TTM)", fmt(info.get("trailingEps"), " INR"))
        m5.metric("Dividend yield", fmt((info.get("dividendYield") or 0) * 100, "%"))

        fundamentals_tab, chart_tab, outlook_tab, pipeline_tab, financials_tab = st.tabs([
            "Company Fundamentals", "Technical Chart", "Trading Outlook",
            "Existing AI Pipeline", "Financial Statements",
        ])

        with fundamentals_tab:
            st.subheader("Valuation & business quality")
            fields = [
                ("Sector", info.get("sector")),
                ("Industry", info.get("industry")),
                ("Exchange", info.get("exchange")),
                ("Currency", info.get("currency")),
                ("P/E forward", fmt(info.get("forwardPE"))),
                ("Price / book", fmt(info.get("priceToBook"))),
                ("Book value", fmt(info.get("bookValue"), " INR")),
                ("ROE", fmt((info.get("returnOnEquity") or 0) * 100, "%")),
                ("ROA", fmt((info.get("returnOnAssets") or 0) * 100, "%")),
                ("Profit margin", fmt((info.get("profitMargins") or 0) * 100, "%")),
                ("Operating margin", fmt((info.get("operatingMargins") or 0) * 100, "%")),
                ("Revenue growth", fmt((info.get("revenueGrowth") or 0) * 100, "%")),
                ("Earnings growth", fmt((info.get("earningsGrowth") or 0) * 100, "%")),
                ("Debt / equity", fmt(info.get("debtToEquity"))),
                ("Free cash flow", fmt(info.get("freeCashflow"), " INR")),
                ("Operating cash flow", fmt(info.get("operatingCashflow"), " INR")),
                ("52-week high", fmt(info.get("fiftyTwoWeekHigh"), " INR")),
                ("52-week low", fmt(info.get("fiftyTwoWeekLow"), " INR")),
                ("Beta", fmt(info.get("beta"))),
                ("Shares outstanding", fmt(info.get("sharesOutstanding"))),
                ("Promoter holding", "Not consistently available from Yahoo Finance"),
            ]
            left, right = st.columns(2)
            split = (len(fields) + 1) // 2
            for col, subset in ((left, fields[:split]), (right, fields[split:])):
                with col:
                    st.dataframe(
                        pd.DataFrame(subset, columns=["Metric", "Value"]),
                        hide_index=True, width="stretch",
                    )

            st.caption(
                "N/A means the provider did not supply a usable value. "
                "ROCE and reliable promoter/shareholding data are not consistently "
                "available through Yahoo Finance; use exchange filings for verification."
            )

            st.subheader("Shareholding data, when supplied")
            holders = profile.get("holders", {})
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
                st.info("Shareholding breakdown not supplied by the current data source.")

        with chart_tab:
            st.subheader("Price, volume and moving averages")
            try:
                import plotly.graph_objects as go
                from plotly.subplots import make_subplots

                chart = make_subplots(
                    rows=2, cols=1, shared_xaxes=True,
                    vertical_spacing=0.04, row_heights=[0.72, 0.28],
                )
                chart.add_trace(go.Candlestick(
                    x=frame.index, open=frame["open"], high=frame["high"],
                    low=frame["low"], close=frame["close"], name="Price",
                ), row=1, col=1)
                for key, label in [
                    ("ema_20", "EMA 20"), ("ema_50", "EMA 50"),
                    ("sma_200", "SMA 200"),
                ]:
                    if frame[key].notna().any():
                        chart.add_trace(go.Scatter(
                            x=frame.index, y=frame[key], mode="lines", name=label,
                        ), row=1, col=1)
                chart.add_trace(go.Bar(
                    x=frame.index, y=frame["volume"], name="Volume", opacity=0.55,
                ), row=2, col=1)
                chart.update_layout(
                    template="plotly_dark", height=650,
                    paper_bgcolor="#101a2b", plot_bgcolor="#101a2b",
                    xaxis_rangeslider_visible=False,
                    legend_orientation="h",
                    margin=dict(l=10, r=10, t=35, b=10),
                )
                st.plotly_chart(chart, width="stretch")
            except ImportError:
                st.warning("Plotly is not installed; showing close and volume instead.")
                st.line_chart(frame[["close", "ema_20", "ema_50"]], width="stretch")
                st.bar_chart(frame[["volume"]], width="stretch")

            i1, i2, i3, i4, i5 = st.columns(5)
            i1.metric("RSI (14)", fmt(last_bar.get("rsi_14")))
            i2.metric("MACD", fmt(last_bar.get("macd")))
            i3.metric("ATR (14)", fmt(last_bar.get("atr_14")))
            i4.metric("ADX (14)", fmt(last_bar.get("adx_14")))
            i5.metric("Volume / 20-bar avg", fmt(last_bar.get("volume_ratio_20"), "x"))

            st.subheader("Technical levels from loaded candles")
            levels = [
                ("Rolling support (20 bars)", last_bar.get("rolling_support_20")),
                ("Rolling resistance (20 bars)", last_bar.get("rolling_resistance_20")),
                ("Previous candle high", last_bar.get("previous_high")),
                ("Previous candle low", last_bar.get("previous_low")),
                ("EMA 20", last_bar.get("ema_20")),
                ("EMA 50", last_bar.get("ema_50")),
                ("VWAP over loaded window", last_bar.get("vwap_loaded_window")),
            ]
            st.dataframe(pd.DataFrame([
                {"Level": name, "Price": fmt(value, " INR")}
                for name, value in levels
            ]), hide_index=True, width="stretch")
            st.caption(
                "VWAP here is cumulative across the loaded dataset, not a guaranteed "
                "exchange-session VWAP. Rolling levels are calculated from the loaded "
                "candles; they are not guaranteed support/resistance."
            )

            st.subheader("Data quality")
            st.json(quality)

            st.markdown("**Latest indicator rows**")
            columns = [
                "open", "high", "low", "close", "volume", "ema_20", "ema_50",
                "rsi_14", "macd", "macd_signal", "atr_14", "adx_14",
                "volume_ratio_20",
            ]
            st.dataframe(frame[columns].tail(20), width="stretch")

        with outlook_tab:
            st.subheader("Intraday · Swing · Positional")
            st.caption(
                "These are descriptive technical conditions, not guaranteed forecasts. "
                "No entry/target is presented as a validated strategy without backtesting."
            )
            price = float(last_bar["close"])
            ema20 = last_bar.get("ema_20")
            ema50 = last_bar.get("ema_50")
            rsi = last_bar.get("rsi_14")
            macd = last_bar.get("macd")
            macd_signal = last_bar.get("macd_signal")
            atr = last_bar.get("atr_14")

            def condition(close, fast, slow, rsi_value, macd_value, signal_value):
                if pd.isna(fast) or pd.isna(slow):
                    return "INSUFFICIENT HISTORY", "Need more candles to evaluate trend."
                bullish = close > fast > slow
                bearish = close < fast < slow
                if bullish and (pd.isna(macd_value) or pd.isna(signal_value) or macd_value >= signal_value):
                    return "BULLISH BIAS", "Price is above both moving averages."
                if bearish and (pd.isna(macd_value) or pd.isna(signal_value) or macd_value <= signal_value):
                    return "BEARISH BIAS", "Price is below both moving averages."
                return "MIXED / NEUTRAL", "Trend indicators do not fully agree."

            trend_rows = []
            for label, fast_key, slow_key in [
                ("Intraday proxy", "ema_9", "ema_20"),
                ("Swing proxy", "ema_20", "ema_50"),
                ("Positional proxy", "ema_50", "sma_200"),
            ]:
                state, explanation = condition(
                    price, last_bar.get(fast_key), last_bar.get(slow_key),
                    rsi, macd, macd_signal,
                )
                trend_rows.append({
                    "Horizon": label,
                    "Technical bias": state,
                    "Explanation": explanation,
                })
            st.dataframe(pd.DataFrame(trend_rows), hide_index=True, width="stretch")

            if pd.notna(atr) and float(atr) > 0:
                st.markdown("**Illustrative volatility references — not trade signals**")
                st.write({
                    "Latest close": round(price, 2),
                    "ATR (14)": round(float(atr), 2),
                    "Close minus 1 ATR": round(price - float(atr), 2),
                    "Close plus 1 ATR": round(price + float(atr), 2),
                    "Close minus 2 ATR": round(price - 2 * float(atr), 2),
                    "Close plus 2 ATR": round(price + 2 * float(atr), 2),
                })
            else:
                st.info("ATR-based reference levels unavailable until sufficient history exists.")

            st.warning(
                "No confidence score or historical pattern win-rate is shown here because "
                "this page has not yet validated those estimates with an out-of-sample backtest."
            )

        with pipeline_tab:
            st.subheader("Existing multi-horizon AI model")
            st.caption(
                "This test replays Yahoo's historical 1-minute OHLCV bars through the "
                "existing LiveFeatureEngine and LiveModelService. It is a historical replay, "
                "not a live market feed."
            )
            if st.button("Run existing model on historical 1-minute bars", type="primary"):
                try:
                    from src.market_data import fetch_yahoo
                    from src.live.candle_aggregator import Candle
                    from src.live.feature_engine import LiveFeatureEngine
                    from src.live.model_service import LiveModelService

                    with st.spinner("Fetching 1-minute bars and replaying feature engine…"):
                        _, minute_frame = fetch_yahoo(symbol, "5d", "1m")
                        engine = LiveFeatureEngine(max_candles=1600)
                        latest_features = None
                        for timestamp, row in minute_frame.iterrows():
                            ts = pd.Timestamp(timestamp)
                            if ts.tzinfo is None:
                                ts = ts.tz_localize("UTC")
                            else:
                                ts = ts.tz_convert("UTC")
                            candle = Candle(
                                symbol=symbol,
                                start_time=ts.to_pydatetime(),
                                open=float(row["open"]),
                                high=float(row["high"]),
                                low=float(row["low"]),
                                close=float(row["close"]),
                                volume=float(row["volume"] or 0),
                                tick_count=1,
                                source="yahoo_historical_replay",
                            )
                            result = engine.update(candle)
                            if result is not None:
                                latest_features = result

                        service = LiveModelService.create(model_dir=ROOT / "models/live")
                        status = service.status()
                        st.json({
                            "data_source": "Yahoo Finance historical 1-minute bars",
                            "bars_loaded": len(minute_frame),
                            "model_status": status,
                        })
                        if latest_features is None:
                            st.warning(
                                "Feature engine did not become ready. It requires at least "
                                "240 completed 1-minute candles; the source may have returned fewer."
                            )
                        else:
                            prediction = service.predict(latest_features)
                            st.dataframe(
                                pd.DataFrame(prediction["predictions"]),
                                hide_index=True, width="stretch",
                            )
                            if not status["loaded_horizons"]:
                                st.warning(
                                    "No trained horizon models are loaded. Predictions correctly "
                                    "show NO_MODEL instead of fabricated signals."
                                )
                            st.json({
                                "symbol": prediction["symbol"],
                                "feature_timestamp": prediction["feature_timestamp"],
                                "engine": prediction["engine"],
                            })
                except Exception as exc:
                    st.error(f"Existing AI pipeline could not run: {exc}")

            st.markdown("**Existing outcome records**")
            symbol_outcomes = pd.DataFrame()
            if "outcomes" in globals() and not outcomes.empty and "symbol" in outcomes.columns:
                symbol_outcomes = outcomes[
                    outcomes["symbol"].astype(str).str.upper() == symbol.upper()
                ]
            if not symbol_outcomes.empty:
                st.dataframe(symbol_outcomes.tail(50), width="stretch", hide_index=True)
            else:
                st.info(
                    "No saved outcome records for this symbol. Outcome tracking needs subsequent "
                    "actual prices; a historical replay is not automatically counted as a new live outcome."
                )

        with financials_tab:
            for key, label in [
                ("annual", "Annual financials"),
                ("quarterly", "Quarterly financials"),
                ("balance_sheet", "Balance sheet"),
                ("cash_flow", "Cash flow"),
                ("quarterly_balance_sheet", "Quarterly balance sheet"),
                ("quarterly_cash_flow", "Quarterly cash flow"),
            ]:
                table = profile.get(key)
                st.subheader(label)
                if isinstance(table, pd.DataFrame) and not table.empty:
                    st.dataframe(table, width="stretch")
                else:
                    st.info(f"{label}: not supplied by the current provider.")

            dividends = profile.get("dividends")
            st.subheader("Dividend history")
            if isinstance(dividends, pd.Series) and not dividends.empty:
                st.dataframe(
                    dividends.rename("Dividend").to_frame().tail(30),
                    width="stretch",
                )
            else:
                st.info("Dividend history unavailable from the current provider.")

    else:
        st.info("Enter a ticker/company name and click Analyze stock to load the profile.")

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


# ───────────────────────── FOOTER ───────────────────────────────
st.markdown("""
<div class="footer">
  <b style="color:#9fb5d2">NAUTILUS INDIA AI</b>
  <span> · Research-first architecture · Local data control · Manual execution boundary</span><br>
  Metrics describe detected files and records; they do not independently validate data freshness,
  model quality, profitability or exchange connectivity.
</div>
""", unsafe_allow_html=True)
