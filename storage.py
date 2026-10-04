"""
Storage SQLite per i risultati degli esperimenti.
Schema minimale ma ricco: permette query future per bank/task/seed.
"""
import sqlite3
import json
from datetime import datetime


SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    timestamp_local TEXT,
    task_name TEXT NOT NULL,
    n_train INTEGER,
    n_test INTEGER,
    noise_std REAL,
    seed INTEGER,
    bank TEXT,
    readout TEXT,
    mse_train REAL,
    mse_test REAL,
    r2 REAL,
    inference_time_us REAL,
    train_time_s REAL,
    n_effective_params INTEGER,
    overall_kpi REAL,
    extra_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_task ON experiments(task_name);
CREATE INDEX IF NOT EXISTS idx_bank ON experiments(bank);
CREATE INDEX IF NOT EXISTS idx_kpi ON experiments(overall_kpi);
"""


def _ensure_local_timestamp_column(conn):
    cur = conn.execute("PRAGMA table_info(experiments)")
    cols = {row[1] for row in cur.fetchall()}
    if "timestamp_local" not in cols:
        conn.execute("ALTER TABLE experiments ADD COLUMN timestamp_local TEXT")
        conn.commit()


def init_db(path="results.db"):
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    _ensure_local_timestamp_column(conn)
    conn.commit()
    return conn


def insert_result(conn, r):
    now_utc = datetime.utcnow().isoformat()
    now_local = datetime.now().isoformat(timespec="seconds")
    conn.execute("""
        INSERT INTO experiments
        (timestamp, timestamp_local,
         task_name, n_train, n_test, noise_std, seed, bank, readout,
         mse_train, mse_test, r2, inference_time_us, train_time_s,
         n_effective_params, overall_kpi, extra_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        now_utc, now_local,
        r.get("task"), r.get("n_train"), r.get("n_test"), r.get("noise_std", 0.0),
        r.get("seed"), r.get("bank"), r.get("readout"),
        r.get("mse_train"), r.get("mse_test"), r.get("r2"),
        r.get("inference_time_us"), r.get("train_time_s"),
        r.get("n_effective_params"), r.get("overall_kpi"),
        json.dumps(r.get("extra", {})),
    ))
    conn.commit()


def query_top(conn, task_name=None, limit=20):
    cur = conn.cursor()
    if task_name:
        cur.execute("""SELECT bank, readout, task_name,
                       AVG(mse_test), AVG(overall_kpi), COUNT(*)
                       FROM experiments WHERE task_name=?
                       GROUP BY bank, readout
                       ORDER BY AVG(overall_kpi) DESC LIMIT ?""",
                    (task_name, limit))
    else:
        cur.execute("""SELECT bank, readout, task_name,
                       AVG(mse_test), AVG(overall_kpi), COUNT(*)
                       FROM experiments
                       GROUP BY bank, readout, task_name
                       ORDER BY AVG(overall_kpi) DESC LIMIT ?""",
                    (limit,))
    return cur.fetchall()
