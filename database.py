import sqlite3
import threading
import time

DB_NAME = "daq.db"
lock = threading.Lock()

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            start_time REAL,
            end_time REAL
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS measurements (
            timestamp REAL,
            run_id INTEGER,
            p1 REAL,
            p2 REAL,
            p3 REAL,
            pump_state INTEGER
        )
        """)
        conn.commit()

def insert_measurement(data):
    with lock:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("""
                INSERT INTO measurements VALUES (?, ?, ?, ?, ?, ?)
            """, data)
            conn.commit()

def create_run(name, description):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO runs (name, description, start_time)
            VALUES (?, ?, ?)
        """, (name, description, time.time()))
        conn.commit()
        return cur.lastrowid

def end_run(run_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            UPDATE runs SET end_time = ?
            WHERE id = ?
        """, (time.time(), run_id))
        conn.commit()

def get_runs():
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute("SELECT * FROM runs").fetchall()

def get_measurements(run_id):
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute("""
            SELECT timestamp, p1, p2, p3
            FROM measurements
            WHERE run_id = ?
            ORDER BY timestamp
        """, (run_id,)).fetchall()
