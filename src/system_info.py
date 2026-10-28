import platform
import sys
from pathlib import Path
import nautilus_trader

ROOT = Path(__file__).resolve().parents[1]

def snapshot():
    try:
        import streamlit
        st_version = streamlit.__version__
    except Exception:
        st_version = "unavailable"
    try:
        import pandas
        pd_version = pandas.__version__
    except Exception:
        pd_version = "unavailable"
    return {
        "NautilusTrader": getattr(nautilus_trader, "__version__", "unknown"),
        "Python": platform.python_version(),
        "OS": platform.platform(),
        "Streamlit": st_version,
        "Pandas": pd_version,
        "Project": str(ROOT),
        "Interpreter": sys.executable,
    }
