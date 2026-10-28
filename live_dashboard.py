import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
LIVE = ROOT / "data" / "live"
MODELS = ROOT / "models" / "live"
SRC = ROOT / "src" / "live"

st.set_page_config(
    page_title="India Equity AI",
    page_icon="📈",
    layout="wide",
)

st.title("📈 India Equity AI — Control Dashboard")
st.caption("NSE / BSE • Cash Equity • Manual trading only")
st.info(
    "Project status dashboard. Predictions and market status appear "
    "only when the corresponding runtime components are connected."
)

def read_jsonl(name):
    path = LIVE / name
    if not path.exists():
        return []
    rows = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return rows

def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

def find_value(obj, *keys, default="—"):
    for key in keys:
        if isinstance(obj, dict) and obj.get(key) is not None:
            return obj[key]
    return default

predictions = read_jsonl("predictions.jsonl")
candles = read_jsonl("candles.jsonl")
features = read_jsonl("features.jsonl")
outcomes = read_jsonl("outcomes.jsonl")

latest = predictions[-1] if predictions else {}
symbol = find_value(latest, "symbol")
price = find_value(latest, "close", "reference_price")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest symbol", symbol)
c2.metric("Recorded candles", len(candles))
c3.metric("Prediction records", len(predictions))
c4.metric("Resolved outcomes", len(outcomes))

st.divider()
st.subheader("🔮 Multi-timeframe prediction board")

horizons = [1, 5, 15, 30, 60, 240]
pred_map = latest.get("predictions", {}) if isinstance(latest, dict) else {}

def get_prediction(h):
    if isinstance(pred_map, dict):
        return pred_map.get(str(h), pred_map.get(h, {}))
    if isinstance(pred_map, list):
        for item in pred_map:
            if item.get("horizon_minutes") == h:
                return item
    return {}

cols = st.columns(3)
for i, h in enumerate(horizons):
    p = get_prediction(h)
    with cols[i % 3]:
        st.markdown(f"**{h} minute{'s' if h != 1 else ''}**")
        st.metric(
            "Direction",
            str(find_value(p, "direction", default="NO DATA")),
            help="Model output, not a guaranteed market move.",
        )
        confidence = p.get("confidence")
        st.write(
            f"Confidence: {float(confidence):.1%}"
            if isinstance(confidence, (int, float))
            else "Confidence: —"
        )
        st.caption(f"Status: {find_value(p, 'status', default='NO PREDICTION')}")

st.divider()
left, right = st.columns(2)

with left:
    st.subheader("🧠 Model readiness")
    model_rows = []
    for h in horizons:
        metadata = read_json(MODELS / f"model_{h}m.json")
        artifact = MODELS / f"model_{h}m.joblib"
        model_rows.append({
            "Horizon": f"{h}m",
            "Artifact": "Present" if artifact.is_file() else "Missing",
            "Version": metadata.get("version", "—"),
            "Status": metadata.get("status", "NOT TRAINED"),
            "Balanced accuracy": metadata.get("metrics", {}).get(
                "balanced_accuracy", "—"
            ),
        })
    st.dataframe(pd.DataFrame(model_rows), use_container_width=True, hide_index=True)

with right:
    st.subheader("📡 Component inventory")
    components = [
        ("Market feed interface", "src/live/market_feed.py", "Interface only; source not connected"),
        ("Candle aggregator", "src/live/candle_aggregator.py", "Implemented; runtime not confirmed"),
        ("Feature engine", "src/live/feature_engine.py", "Six horizons; runtime not confirmed"),
        ("Prediction engine", "src/live/prediction_engine.py", "Implemented; model wiring pending"),
        ("Event store", "src/live/event_store.py", "Implemented; runtime not confirmed"),
        ("Outcome tracker", "src/live/outcome_tracker.py", "Implemented; runtime not confirmed"),
        ("Telegram alerts", "src/live/telegram_alerts.py", "Credentials/runtime not confirmed"),
        ("Historical bootstrap", "src/live/historical_bootstrap.py", "Dataset generation module"),
        ("Model trainer", "src/live/model_trainer.py", "Training module"),
        ("Promotion guard", "src/live/model_promotion.py", "Review guard; promotion not automatic"),
    ]
    component_rows = []
    for label, relative, note in components:
        component_rows.append({
            "Component": label,
            "File": "Present" if (ROOT / relative).is_file() else "Missing",
            "Integration": note,
        })
    st.dataframe(
        pd.DataFrame(component_rows),
        use_container_width=True,
        hide_index=True,
    )

st.divider()
st.subheader("📊 Recorded market data")

if candles:
    candle_df = pd.DataFrame(candles)
    if "close" in candle_df.columns:
        candle_df["close"] = pd.to_numeric(candle_df["close"], errors="coerce")
        if "timestamp" in candle_df.columns:
            candle_df = candle_df.set_index("timestamp")
        st.line_chart(candle_df["close"].dropna())
    st.dataframe(candle_df.tail(20), use_container_width=True)
else:
    st.warning("No candle records yet. The market feed and live pipeline are not confirmed running.")

st.subheader("🎯 Prediction history")
if predictions:
    history_rows = []
    for record in predictions[-100:]:
        pmap = record.get("predictions", {})
        if isinstance(pmap, list):
            items = pmap
        elif isinstance(pmap, dict):
            items = list(pmap.values())
        else:
            items = []
        for p in items:
            history_rows.append({
                "Symbol": record.get("symbol", "—"),
                "Recorded at": record.get("generated_at", record.get("timestamp", "—")),
                "Horizon": p.get("horizon_minutes", "—"),
                "Direction": p.get("direction", "—"),
                "Confidence": p.get("confidence", "—"),
                "Status": p.get("status", "—"),
            })
    if history_rows:
        st.dataframe(
            pd.DataFrame(history_rows).tail(100),
            use_container_width=True,
            hide_index=True,
        )
else:
    st.write("No predictions recorded yet.")

st.subheader("🎓 Learning / outcomes")
if outcomes:
    st.dataframe(pd.DataFrame(outcomes[-100:]), use_container_width=True, hide_index=True)
else:
    st.write("No resolved outcomes recorded yet.")

st.caption(
    "This dashboard reads local JSONL and model metadata files. "
    "It does not start a market feed, train models, place orders, "
    "or prove prediction accuracy by itself."
)
