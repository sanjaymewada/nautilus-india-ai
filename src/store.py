import sqlite3
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "control_center.sqlite3"

def connect():
    con = sqlite3.connect(DB, timeout=15)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ts TEXT NOT NULL, level TEXT NOT NULL,
          component TEXT NOT NULL, message TEXT NOT NULL,
          details TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS runs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          created_at TEXT NOT NULL, run_type TEXT NOT NULL,
          status TEXT NOT NULL, config_json TEXT NOT NULL DEFAULT '{}',
          result_json TEXT NOT NULL DEFAULT '{}', error TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS datasets (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          created_at TEXT NOT NULL, symbol TEXT NOT NULL,
          source TEXT NOT NULL, start_date TEXT, end_date TEXT,
          rows INTEGER NOT NULL, file_path TEXT NOT NULL
        );
        """)

def event(level, component, message, details=""):
    init_db()
    with connect() as con:
        con.execute(
            "INSERT INTO events(ts,level,component,message,details) VALUES(?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), level, component, message, str(details))
        )

def events(limit=250):
    init_db()
    with connect() as con:
        return [dict(r) for r in con.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (int(limit),)
        ).fetchall()]

def save_run(run_type, status, config, result=None, error=""):
    import json
    init_db()
    with connect() as con:
        cur = con.execute(
            "INSERT INTO runs(created_at,run_type,status,config_json,result_json,error) VALUES(?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), run_type, status,
             json.dumps(config, default=str), json.dumps(result or {}, default=str), error)
        )
        return cur.lastrowid

def runs(limit=100):
    init_db()
    with connect() as con:
        return [dict(r) for r in con.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (int(limit),)
        ).fetchall()]

def save_dataset(symbol, source, frame, file_path):
    init_db()
    with connect() as con:
        con.execute(
            "INSERT INTO datasets(created_at,symbol,source,start_date,end_date,rows,file_path) VALUES(?,?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), symbol, source,
             str(frame.index.min()), str(frame.index.max()), len(frame), str(file_path))
        )

def datasets():
    init_db()
    with connect() as con:
        return [dict(r) for r in con.execute(
            "SELECT * FROM datasets ORDER BY id DESC LIMIT 200"
        ).fetchall()]
