import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path('data/finance.db')


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(
        '''
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT,
            salary REAL,
            extra_income REAL,
            investment_returns REAL,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT,
            date TEXT,
            description TEXT,
            amount REAL,
            category TEXT,
            source TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            type TEXT,
            invested_amount REAL,
            current_value REAL,
            date TEXT,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            target_amount REAL,
            current_amount REAL,
            deadline TEXT,
            status TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT,
            content TEXT,
            weekly_plan TEXT,
            monthly_plan TEXT,
            annual_plan TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS milestones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id INTEGER,
            description TEXT,
            completed INTEGER,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS health_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            month TEXT,
            score INTEGER,
            label TEXT,
            details TEXT,
            created_at TEXT
        );
        '''
    )
    conn.commit()
    conn.close()


def now_iso():
    return datetime.utcnow().isoformat()


def to_dicts(rows):
    return [dict(r) for r in rows]
