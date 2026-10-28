from datetime import date, datetime
from pathlib import Path
import json, sqlite3
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
RESEARCH = ROOT / "data" / "research"
MODEL_DIR = ROOT / "models" / "live"
DB = RESEARCH / "trade_journal.sqlite3"

st.set_page_config(page_title="AI Trader", page_icon="📈", layout="wide")
st.markdown("""
<style>
.stApp{background:#0b1120}.stApp header{background:#0b1120}
[data-testid=stSidebar]{background:#0d1526;border-right:1px solid #26344b}
.block-container{padding-top:1.2rem;max-width:1800px}
[data-testid=stMetric]{background:#111c2e;border:1px solid #26344b;padding:14px;border-radius:12px}
[data-testid=stMetricLabel]{color:#94a3b8}
[data-testid=stMetricValue]{color:#f8fafc}
h1,h2,h3{letter-spacing:-.02em}
</style>
""", unsafe_allow_html=True)

def json_file(p):
    try: return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception: return {}

def csv_files():
    d=ROOT/"data"
    return sorted(p for p in d.rglob("*.csv") if d.exists() and not any(x.startswith(".") for x in p.parts))

def read_csv(p):
    try: return pd.read_csv(p)
    except Exception: return pd.DataFrame()

def init_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS trades(
        id INTEGER PRIMARY KEY, trade_date TEXT, instrument TEXT, market_type TEXT,
        side TEXT, entry REAL, exit REAL, quantity REAL, stop REAL, target REAL,
        charges REAL DEFAULT 0, setup TEXT, notes TEXT, status TEXT, created_at TEXT)""")
        c.commit()

def trades():
    init_db()
    with sqlite3.connect(DB) as c: return pd.read_sql_query("SELECT * FROM trades ORDER BY trade_date DESC,id DESC", c)

def pnl(r):
    try:
        direction=1 if r["side"]=="BUY" else -1
        return (float(r["exit"])-float(r["entry"]))*float(r["quantity"])*direction-float(r["charges"] or 0)
    except (TypeError,ValueError): return None

def get_report():
    p=RESEARCH/"live_horizon_training_report.json"
    return json_file(p),p

def fetch_snapshot():
    import yfinance as yf
    symbols=[("RELIANCE.NS","RELIANCE"),("HDFCBANK.NS","HDFCBANK"),("ICICIBANK.NS","ICICIBANK"),
    ("SBIN.NS","SBIN"),("INFY.NS","INFY"),("TCS.NS","TCS"),("BHARTIARTL.NS","BHARTIARTL"),
    ("ITC.NS","ITC"),("LT.NS","LT"),("TATAMOTORS.NS","TATAMOTORS")]
    rows=[]
    for ticker,name in symbols:
        try:
            h=yf.Ticker(ticker).history(period="3mo",interval="1d",auto_adjust=True,timeout=10)
            if h.empty: continue
            c=h.Close.dropna()
            if c.empty: continue
            last=float(c.iloc[-1]); prev=float(c.iloc[-2]) if len(c)>1 else None
            sma5=float(c.rolling(5).mean().iloc[-1]) if len(c)>=5 else None
            sma20=float(c.rolling(20).mean().iloc[-1]) if len(c)>=20 else None
            bias="WAIT"
            if sma5 is not None and sma20 is not None:
                if last>sma5>sma20: bias="BULLISH TREND"
                elif last<sma5<sma20: bias="BEARISH TREND"
            rows.append({"Symbol":name,"Historical close":last,"Day change %":((last/prev)-1)*100 if prev else None,
            "SMA 5":sma5,"SMA 20":sma20,"Research trend":bias,"Data date":h.index[-1].strftime("%Y-%m-%d")})
        except Exception: pass
    return pd.DataFrame(rows)

with st.sidebar:
    st.markdown("# 📈 AI TRADER")
    st.caption("INDIA · DECISION TERMINAL")
    page=st.radio("NAVIGATION",["Overview","Scanner","Instrument Analysis","Options Lab","Trade Journal","Performance"],label_visibility="collapsed")
    st.divider()
    st.info("Research mode · Manual execution")
    st.caption("No broker connection. No orders placed.")

st.title("AI Trader")
st.caption("Actionable research · Manual order placement only")
report,report_path=get_report()
model_files=list(MODEL_DIR.glob("model_*m.joblib")) if MODEL_DIR.exists() else []

if page=="Overview":
    st.subheader("Market overview")
    a,b,c=st.columns(3)
    a.metric("NIFTY 50","—",help="Verified current quote source not configured.")
    b.metric("BANK NIFTY","—",help="Verified current quote source not configured.")
    c.metric("Market bias","WAIT",help="No verified live feed is configured.")
    st.divider()
    left,right=st.columns([1.5,1])
    with left:
        st.subheader("Best trade setup")
        st.warning("NO VERIFIED LIVE SIGNAL")
        st.write("A setup appears only when market data, strategy conditions and risk checks are verified.")
        x1,x2,x3,x4=st.columns(4)
        x1.metric("Entry","—"); x2.metric("Stop-loss","—"); x3.metric("Target","—"); x4.metric("Risk / reward","—")
        st.markdown("**Decision checklist**")
        st.write("• Verify data source and timestamp\n\n• Confirm setup conditions\n\n• Define invalidation and maximum risk\n\n• Respect WAIT when checks fail")
    with right:
        st.subheader("Readiness")
        st.metric("Live model artifacts",len(model_files))
        st.metric("Training report","Available" if report else "Not found")
        if not model_files: st.warning("No live model artifacts found; model-based live signals are unavailable.")
        st.caption("Internal workers and logs are intentionally hidden.")
    t=trades(); today=t[t.trade_date==date.today().isoformat()] if not t.empty else t
    closed=today[today.status=="CLOSED"] if not today.empty else today
    net=sum((pnl(r) or 0) for _,r in closed.iterrows()) if not closed.empty else 0
    st.divider(); st.subheader("Today's manual journal")
    p1,p2,p3=st.columns(3)
    p1.metric("Trades recorded",len(today))
    p2.metric("Net P&L",f"₹{net:,.2f}" if not closed.empty else "—")
    p3.metric("Win rate",f"{sum((pnl(r) or 0)>0 for _,r in closed.iterrows())/len(closed)*100:.1f}%" if not closed.empty else "—")
    st.caption("Journal results are user-entered, not broker-confirmed.")

elif page=="Scanner":
    st.subheader("Equity opportunity scanner")
    st.caption("Yahoo daily candles are historical/delayed—not a real-time intraday feed.")
    if st.button("Refresh historical snapshot",type="primary"):
        try:
            with st.spinner("Fetching historical snapshot…"): st.session_state.snapshot=fetch_snapshot()
            st.session_state.snapshot_at=datetime.now().strftime("%d %b %Y, %H:%M:%S")
        except Exception as e:
            st.error("Historical data could not be loaded. Check that yfinance is installed and internet is available.")
    snap=st.session_state.get("snapshot",pd.DataFrame())
    if not snap.empty:
        st.caption("Fetched at "+st.session_state.get("snapshot_at","")+" · Historical/delayed data")
        filt=st.selectbox("Trend filter",["ALL","BULLISH TREND","BEARISH TREND","WAIT"])
        view=snap if filt=="ALL" else snap[snap["Research trend"]==filt]
        st.dataframe(view,use_container_width=True,hide_index=True,column_config={
            "Historical close":st.column_config.NumberColumn(format="₹%.2f"),
            "Day change %":st.column_config.NumberColumn(format="%+.2f%%"),
            "SMA 5":st.column_config.NumberColumn(format="₹%.2f"),
            "SMA 20":st.column_config.NumberColumn(format="₹%.2f")})
        st.info("These are simple SMA research filters, not AI predictions or trade recommendations.")
    else: st.info("Click Refresh historical snapshot to load available daily history.")
    files=csv_files()
    if files:
        st.subheader("Local research data")
        selected=st.selectbox("CSV file",files,format_func=lambda p:str(p.relative_to(ROOT)))
        df=read_csv(selected); st.caption(f"{len(df):,} rows"); st.dataframe(df.tail(30),use_container_width=True,hide_index=True)

elif page=="Instrument Analysis":
    st.subheader("Instrument analysis")
    files=csv_files()
    if not files: st.info("No local CSV files found under data/. Use Scanner to fetch historical daily data.")
    else:
        p=st.selectbox("Data file",files,format_func=lambda p:str(p.relative_to(ROOT)))
        df=read_csv(p)
        lower={str(c).lower():c for c in df.columns}
        close=next((lower[k] for k in ["close","adj close","last","price"] if k in lower),None)
        dt=next((lower[k] for k in ["date","datetime","timestamp"] if k in lower),None)
        if close:
            chart=df.copy(); chart[close]=pd.to_numeric(chart[close],errors="coerce")
            if dt: chart[dt]=pd.to_datetime(chart[dt],errors="coerce"); chart=chart.set_index(dt)
            st.line_chart(chart[[close]].dropna(),height=330)
            st.metric("Latest available close",f"₹{float(df[close].dropna().iloc[-1]):,.2f}" if df[close].notna().any() else "—")
        else: st.warning("No recognized close/price column in this file.")
        st.dataframe(df.tail(50),use_container_width=True,hide_index=True)

elif page=="Options Lab":
    st.subheader("NIFTY / BANK NIFTY Options Lab")
    st.warning("OPTION CHAIN DATA NOT CONNECTED")
    st.write("No broker API or verified live option-chain feed is configured. No contract-specific signal will be invented.")
    a,b=st.columns(2)
    with a:
        underlying=st.selectbox("Underlying",["NIFTY","BANKNIFTY"])
        opt=st.selectbox("Option type",["CALL (CE)","PUT (PE)"])
        st.selectbox("Analysis",["Directional setup","Contract comparison","Risk review"])
    with b:
        st.text_input("Expiry",placeholder="Requires verified expiry data")
        st.number_input("Strike",min_value=0,step=50,value=0)
        st.number_input("Premium (₹)",min_value=0.0,step=0.05,value=0.0)
    st.info("Premium, bid/ask, OI, IV, Greeks, lot size and expiry must come from a reliable current source.")
    st.markdown("**Required checks**")
    st.write("• Current underlying and contract timestamp\n\n• Expiry, lot size and liquidity\n\n• Bid/ask spread and premium\n\n• Stop-loss, target and maximum loss\n\n• Underlying signal separated from contract risk")

elif page=="Trade Journal":
    st.subheader("Manual trade journal")
    st.caption("Record trades placed manually. This page never places orders.")
    with st.expander("＋ Add trade",expanded=True):
        with st.form("new_trade",clear_on_submit=True):
            a,b,c=st.columns(3)
            td=a.date_input("Trade date",value=date.today())
            instrument=b.text_input("Instrument",placeholder="RELIANCE / NIFTY")
            market=c.selectbox("Market type",["Equity intraday","Index option","Equity swing","Other"])
            a,b,c=st.columns(3)
            side=a.selectbox("Side",["BUY","SELL"]); entry=b.number_input("Entry price",min_value=0.0,step=0.05); qty=c.number_input("Quantity / lots",min_value=0.0,step=1.0)
            a,b,c=st.columns(3)
            stop=a.number_input("Stop-loss",min_value=0.0,step=0.05); target=b.number_input("Target",min_value=0.0,step=0.05); charges=c.number_input("Estimated charges ₹",min_value=0.0,step=1.0)
            setup=st.text_input("Setup"); notes=st.text_area("Notes / lesson")
            save=st.form_submit_button("Save trade",type="primary")
            if save:
                if not instrument.strip() or entry<=0 or qty<=0: st.error("Instrument, positive entry and quantity are required.")
                else:
                    init_db()
                    with sqlite3.connect(DB) as con:
                        con.execute("INSERT INTO trades(trade_date,instrument,market_type,side,entry,quantity,stop,target,charges,setup,notes,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (td.isoformat(),instrument.strip().upper(),market,side,entry,qty,stop or None,target or None,charges,setup,notes,"OPEN",datetime.now().isoformat(timespec="seconds")))
                        con.commit()
                    st.success("Saved to local journal."); st.rerun()
    t=trades()
    if t.empty: st.info("No trades recorded yet.")
    else:
        opened=t[t.status=="OPEN"]
        st.markdown("#### Open trades")
        if opened.empty: st.caption("No open journal entries.")
        else:
            st.dataframe(opened,use_container_width=True,hide_index=True)
            with st.form("close_trade"):
                tid=st.selectbox("Trade to close",opened.id.tolist(),format_func=lambda i:f"#{i} · {opened.loc[opened.id==i,'instrument'].iloc[0]}")
                exit_price=st.number_input("Exit price",min_value=0.0,step=0.05)
                final_charges=st.number_input("Total charges ₹",min_value=0.0,step=1.0)
                if st.form_submit_button("Record exit"):
                    if exit_price<=0: st.error("Enter a valid exit price.")
                    else:
                        with sqlite3.connect(DB) as con: con.execute("UPDATE trades SET exit=?,charges=?,status='CLOSED' WHERE id=?",(exit_price,final_charges,tid)); con.commit()
                        st.success("Exit recorded."); st.rerun()
        view=t.copy(); view["Net P&L ₹"]=view.apply(lambda r:pnl(r) if r.status=="CLOSED" else None,axis=1)
        st.markdown("#### Journal history"); st.dataframe(view,use_container_width=True,hide_index=True)

elif page=="Performance":
    st.subheader("Performance & learning")
    t=trades(); closed=t[t.status=="CLOSED"].copy() if not t.empty else pd.DataFrame()
    if closed.empty: st.info("Record closed trades in the manual journal to calculate performance.")
    else:
        closed["Net P&L ₹"]=closed.apply(pnl,axis=1); values=closed["Net P&L ₹"].fillna(0)
        a,b,c,d=st.columns(4)
        a.metric("Closed trades",len(closed)); b.metric("Net P&L",f"₹{values.sum():,.2f}")
        c.metric("Win rate",f"{(values>0).mean()*100:.1f}%"); d.metric("Average trade",f"₹{values.mean():,.2f}")
        st.markdown("#### P&L by trade")
        chart=closed.sort_values(["trade_date","id"]).copy(); chart["Trade #"]=range(1,len(chart)+1)
        st.bar_chart(chart.set_index("Trade #")["Net P&L ₹"])
        st.markdown("#### Strategy breakdown")
        st.dataframe(closed.groupby("setup",dropna=False)["Net P&L ₹"].agg(["count","sum","mean"]).reset_index(),use_container_width=True,hide_index=True)
    st.divider(); st.subheader("Model research status")
    if report:
        models=report.get("models",{})
        if isinstance(models,dict) and models:
            rows=[]
            for horizon,item in models.items():
                item=item if isinstance(item,dict) else {}
                m=item.get("metrics",{}) if isinstance(item.get("metrics",{}),dict) else {}
                rows.append({"Horizon":str(horizon)+"m","Status":item.get("status","UNKNOWN"),"Train rows":m.get("train_rows","—"),"Test rows":m.get("test_rows","—"),"Balanced accuracy":m.get("balanced_accuracy","—"),"Reason":item.get("reason","")})
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        else: st.json(report)
        st.caption("Research metrics are not proof of profitability.")
    else: st.info("No data/research/live_horizon_training_report.json found.")

st.divider()
st.caption("Research-first · Manual execution only · No broker orders are sent.")
