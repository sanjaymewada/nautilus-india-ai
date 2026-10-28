# Nautilus India AI

Local research dashboard for Indian NSE/BSE cash-equity research. Live order placement is disabled.

## Environment
Use the existing Python environment:
```bash
source ~/equityai/.venv/bin/activate
cd ~/nautilus-india-ai
streamlit run app.py
```

## Current foundation
- Streamlit control-center UI
- SQLite event, dataset and run registries
- On-demand historical OHLCV retrieval using yfinance
- Basic OHLCV data-quality checks and Parquet persistence
- Research configuration and experiment records
- Runtime/API visibility

## Not yet implemented
- NautilusTrader BacktestEngine strategy execution and result reconciliation
- Continuous market-data feed
- Background worker queue and live event transport
- Paper execution, portfolio accounting and enforced risk checks
- AI training, walk-forward validation and strategy promotion

Do not treat saved configurations as executed backtests or proposed risk limits as active enforcement.
