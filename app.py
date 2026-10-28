import json
import os
import platform
import time
from pathlib import Path

import pandas as pd
import streamlit as st
import nautilus_trader

from src.store import init_db, event, events, runs, save_run, datasets, save_dataset
from src.market_data import fetch_yahoo, quality_report, DATA_DIR
from src.system_info import snapshot

ROOT = Path(__file__).resolve().parent
for folder in ("data", "results", "logs", "config"):
    (ROOT / folder).mkdir(parents=True, exist_ok=True)
init_db()

st.set_page_config(
    page_title="Nautilus India AI",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.block-container {padding-top:1.3rem; padding-bottom:2rem; max-width:1600px}
[data-testid="stMetric"] {border:1px solid rgba(128,128,128,.22);padding:15px 16px;border-radius:12px}
[data-testid="stSidebar"] {border-right:1px solid rgba(128,128,128,.18)}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:12px}
.small-muted {font-size:12px; opacity:.72}
</style>
""", unsafe_allow_html=True)

PAGES = [
    "Command Center", "Market Data", "Backtesting Lab",
    "AI & Learning", "Risk & Paper Trading",
    "System Monitor", "Reports & Runs", "API Explorer",
]

with st.sidebar:
    st.markdown("## ◈ NAUTILUS")
    st.caption("INDIA · RESEARCH TERMINAL")
    page = st.radio("WORKSPACES", PAGES, label_visibility="collapsed")
    st.divider()
    st.markdown("**Environment**")
    st.caption("NSE / BSE cash equities")
    st.caption("Simulation only · No live orders")
    st.caption(f"Engine package {nautilus_trader.__version__}")
    st.divider()
    st.caption("Data source status")
    st.warning("Yahoo Finance: on-demand only")

def heading(title, subtitle):
    st.title(title)
    st.caption(subtitle)

def show_events(limit=15):
    rows = events(limit)
    if rows:
        frame = pd.DataFrame(rows)
        frame = frame.rename(columns={
            "ts":"Timestamp (UTC)", "level":"Level",
            "component":"Component", "message":"Event", "details":"Details"
        })
        st.dataframe(
            frame[["Timestamp (UTC)", "Level", "Component", "Event", "Details"]],
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No events recorded yet. Activity will appear here as tasks run.")

if page == "Command Center":
    heading("Command Center", "System status, data availability and research activity.")
    info = snapshot()
    all_datasets = datasets()
    all_runs = runs()
    completed = sum(1 for r in all_runs if r["status"] == "COMPLETED")
    errors = sum(1 for e in events(500) if e["level"] == "ERROR")

    a, b, c, d = st.columns(4)
    a.metric("NautilusTrader", info["NautilusTrader"])
    b.metric("Saved datasets", len(all_datasets))
    c.metric("Recorded runs", len(all_runs))
    d.metric("Recorded errors", errors)

    st.subheader("Service readiness")
    services = pd.DataFrame([
        {"Component":"Python environment","Status":"Available","Notes":info["Python"]},
        {"Component":"NautilusTrader package","Status":"Installed","Notes":info["NautilusTrader"]},
        {"Component":"Market data","Status":"On demand","Notes":"No live feed configured"},
        {"Component":"Backtest engine workflow","Status":"Integration pending","Notes":"No backtest is claimed as executed"},
        {"Component":"Broker execution","Status":"Disabled","Notes":"Live orders are not available"},
        {"Component":"Persistent event store","Status":"Available","Notes":"SQLite local database"},
    ])
    st.dataframe(services, use_container_width=True, hide_index=True)
    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("Recent system activity")
        show_events(8)
    with right:
        st.subheader("Latest saved runs")
        if all_runs:
            st.dataframe(pd.DataFrame(all_runs)[["id","created_at","run_type","status"]],
                         use_container_width=True, hide_index=True)
        else:
            st.caption("No runs recorded yet.")
    st.caption("Only recorded system values are shown. Missing integrations are labelled explicitly.")

elif page == "Market Data":
    heading("Market Data", "Fetch, validate and save historical OHLCV data for research.")
    st.warning("Yahoo Finance is an unofficial data source. Verify completeness and exchange timestamps before relying on results.")
    with st.form("data_fetch"):
        c1, c2, c3 = st.columns(3)
        symbol = c1.text_input("NSE symbol", "RELIANCE.NS", help="Examples: RELIANCE.NS, TCS.NS, SBIN.NS")
        period = c2.selectbox("Historical range", ["1mo","3mo","6mo","1y","2y","5y"], index=3)
        interval = c3.selectbox("Candle interval", ["1d","1h","30m","15m","5m"], index=0)
        fetch_clicked = st.form_submit_button("Fetch & validate data", type="primary", use_container_width=True)
    if fetch_clicked:
        try:
            event("INFO", "market-data", f"Fetch requested: {symbol} / {period} / {interval}")
            with st.spinner("Fetching and validating historical candles..."):
                ticker, frame = fetch_yahoo(symbol, period, interval)
                report = quality_report(frame)
                safe = ticker.replace("/", "_").replace(":", "_")
                path = DATA_DIR / f"{safe}_{interval}_{period}.parquet"
                frame.to_parquet(path)
                save_dataset(ticker, "Yahoo Finance (yfinance)", frame, path)
                event("INFO", "market-data", f"Saved {len(frame)} rows for {ticker}", path)
                st.session_state["last_market_frame"] = frame
                st.session_state["last_market_symbol"] = ticker
                st.session_state["last_market_report"] = report
            st.success(f"Saved {len(frame):,} rows for {ticker}.")
        except Exception as exc:
            event("ERROR", "market-data", "Fetch or validation failed", repr(exc))
            st.error(f"Data fetch failed: {exc}")
    frame = st.session_state.get("last_market_frame")
    if frame is not None:
        report = st.session_state.get("last_market_report", {})
        st.subheader(f"{st.session_state.get('last_market_symbol', '')} · Loaded dataset")
        cols = st.columns(4)
        cols[0].metric("Rows", f"{report.get('rows',0):,}")
        cols[1].metric("Missing values", report.get("missing_values", "—"))
        cols[2].metric("Duplicate timestamps", report.get("duplicate_timestamps", "—"))
        cols[3].metric("Invalid OHLC rows", report.get("invalid_ohlc", "—"))
        st.line_chart(frame["close"], height=300)
        st.dataframe(frame.tail(30), use_container_width=True)
        st.download_button("Download loaded candles as CSV", frame.to_csv().encode(),
                           file_name=f"{st.session_state.get('last_market_symbol','data')}.csv",
                           mime="text/csv")
    st.subheader("Saved datasets")
    saved = datasets()
    if saved:
        st.dataframe(pd.DataFrame(saved), use_container_width=True, hide_index=True)
    else:
        st.caption("No saved datasets yet.")

elif page == "Backtesting Lab":
    heading("Backtesting Lab", "Configure reproducible simulations and inspect saved run records.")
    st.info("The NautilusTrader engine execution path is not yet wired into this screen. This page does not generate fabricated performance metrics.")
    with st.form("backtest_config"):
        symbol = st.text_input("Instrument", "RELIANCE.NS")
        strategy = st.selectbox("Strategy template", ["SMA crossover (planned)", "Custom Nautilus strategy"])
        capital = st.number_input("Starting capital (INR)", min_value=10000, value=100000, step=10000)
        fee_bps = st.number_input("Fee assumption (basis points)", min_value=0.0, max_value=100.0, value=5.0)
        slippage_bps = st.number_input("Slippage assumption (basis points)", min_value=0.0, max_value=100.0, value=2.0)
        notes = st.text_area("Run notes", placeholder="Data source, assumptions, experiment ID...")
        save_config = st.form_submit_button("Save research configuration", type="primary")
    if save_config:
        config = {"symbol":symbol.upper(), "strategy":strategy, "starting_capital_inr":capital,
                  "fee_bps":fee_bps, "slippage_bps":slippage_bps, "notes":notes,
                  "engine":"NautilusTrader", "execution_status":"NOT_RUN"}
        run_id = save_run("BACKTEST_CONFIG", "CONFIG_SAVED", config)
        event("INFO", "backtest", f"Configuration saved as run #{run_id}", json.dumps(config))
        st.success(f"Configuration saved. Run ID: {run_id}. No backtest was executed.")
    st.subheader("Saved configurations and runs")
    history = runs()
    if history:
        st.dataframe(pd.DataFrame(history)[["id","created_at","run_type","status","error"]],
                     use_container_width=True, hide_index=True)
    else:
        st.caption("No research runs yet.")

elif page == "AI & Learning":
    heading("AI & Learning Lab", "Auditable experiments, trade mistakes and strategy promotion.")
    st.info("No model is trained or learning from trades yet. This workspace is designed to keep AI suggestions separate from validated strategy changes.")
    with st.form("experiment"):
        name = st.text_input("Experiment name", placeholder="e.g. trend filter v1")
        hypothesis = st.text_area("Hypothesis", placeholder="What change are you testing, and why?")
        baseline = st.text_input("Baseline strategy version", "baseline-v1")
        candidate = st.text_input("Candidate version", "candidate-v1")
        submit = st.form_submit_button("Record experiment")
    if submit:
        if not name.strip():
            st.error("Enter an experiment name.")
        else:
            config = {"name":name, "hypothesis":hypothesis, "baseline":baseline,
                      "candidate":candidate, "promotion_status":"NOT_VALIDATED"}
            run_id = save_run("AI_EXPERIMENT", "RECORDED_NOT_VALIDATED", config)
            event("INFO", "ai-lab", f"Experiment recorded as #{run_id}")
            st.success(f"Experiment recorded as #{run_id}. No model was trained.")
    st.subheader("Experiment history")
    history = [r for r in runs() if "EXPERIMENT" in r["run_type"]]
    if history:
        st.dataframe(pd.DataFrame(history)[["id","created_at","status","config_json"]],
                     use_container_width=True, hide_index=True)
    else:
        st.caption("No experiments recorded yet.")

elif page == "Risk & Paper Trading":
    heading("Risk & Paper Trading", "Simulation-only controls. No broker credentials or live order routes.")
    st.warning("Paper execution is not connected yet. The limits below are configuration drafts, not active enforcement.")
    with st.form("risk_config"):
        daily_loss = st.number_input("Proposed daily loss limit (INR)", min_value=500, value=2000, step=500)
        position_limit = st.number_input("Proposed max position value (INR)", min_value=1000, value=20000, step=1000)
        max_positions = st.number_input("Proposed maximum open positions", min_value=1, max_value=50, value=3)
        submit = st.form_submit_button("Save risk configuration", type="primary")
    if submit:
        config = {"daily_loss_limit_inr":daily_loss, "max_position_value_inr":position_limit,
                  "max_open_positions":max_positions, "enforcement":"NOT_ACTIVE"}
        run_id = save_run("RISK_CONFIG", "CONFIG_SAVED_NOT_ENFORCED", config)
        event("WARNING", "risk", f"Risk config saved as #{run_id}; enforcement not active")
        st.success(f"Saved configuration #{run_id}. Limits are not yet enforced by an execution engine.")
    st.subheader("Execution safety")
    st.write("- Live orders: disabled")
    st.write("- Broker connection: not configured")
    st.write("- Simulated order lifecycle: pending integration")
    st.write("- Risk rejection audit trail: available after enforcement is implemented")

elif page == "System Monitor":
    heading("System Monitor", "Runtime inventory, persisted events and operational diagnostics.")
    info = snapshot()
    st.subheader("Runtime")
    st.json(info)
    st.subheader("Project directories")
    directory_rows = []
    for name in ("src","data","results","logs","config"):
        p = ROOT / name
        directory_rows.append({"Directory":name, "Files":sum(1 for x in p.rglob("*") if x.is_file()),
                               "Path":str(p)})
    st.dataframe(pd.DataFrame(directory_rows), use_container_width=True, hide_index=True)
    st.subheader("Event stream")
    c1, c2 = st.columns([1,3])
    limit = c1.selectbox("Events to show", [25,50,100,250], index=1)
    level = c2.selectbox("Filter level", ["ALL","INFO","WARNING","ERROR"])
    ev = events(limit)
    if level != "ALL":
        ev = [e for e in ev if e["level"] == level]
    if ev:
        st.dataframe(pd.DataFrame(ev), use_container_width=True, hide_index=True)
        st.download_button("Export event log CSV", pd.DataFrame(ev).to_csv(index=False).encode(),
                           file_name="system_events.csv", mime="text/csv")
    else:
        st.caption("No events match this filter.")

elif page == "Reports & Runs":
    heading("Reports & Runs", "Persistent research configurations, experiment records and saved data.")
    tab1, tab2 = st.tabs(["Run history", "Dataset registry"])
    with tab1:
        history = runs(500)
        if history:
            st.dataframe(pd.DataFrame(history), use_container_width=True, hide_index=True)
            st.download_button("Export run registry CSV", pd.DataFrame(history).to_csv(index=False).encode(),
                               file_name="run_registry.csv", mime="text/csv")
        else:
            st.info("No runs recorded.")
    with tab2:
        saved = datasets()
        if saved:
            st.dataframe(pd.DataFrame(saved), use_container_width=True, hide_index=True)
        else:
            st.info("No datasets recorded.")

elif page == "API Explorer":
    heading("Nautilus API Explorer", "Inspect the installed package without assuming every API is operationally integrated.")
    query = st.text_input("Filter exported names", placeholder="backtest, model, strategy, risk...")
    import importlib
    candidates = [
        "nautilus_trader.backtest",
        "nautilus_trader.config",
        "nautilus_trader.model",
        "nautilus_trader.trading",
        "nautilus_trader.indicators",
        "nautilus_trader.persistence",
        "nautilus_trader.execution",
        "nautilus_trader.portfolio",
        "nautilus_trader.risk",
        "nautilus_trader.data",
        "nautilus_trader.adapters",
    ]
    rows = []
    for module_name in candidates:
        try:
            module = importlib.import_module(module_name)
            public = [n for n in dir(module) if not n.startswith("_")]
            filtered = [n for n in public if query.lower() in n.lower()] if query else public
            rows.append({"Module":module_name, "Import":"OK", "Public names":len(public),
                         "Matching names":", ".join(filtered[:30])})
        except Exception as exc:
            rows.append({"Module":module_name, "Import":"Unavailable",
                         "Public names":0, "Matching names":str(exc)[:250]})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("Module import success means the module can be imported; it does not mean the feature has been wired into this application.")

st.divider()
st.caption("Nautilus India AI · Local research workspace · Historical data may be incomplete or delayed · Live trading disabled")
