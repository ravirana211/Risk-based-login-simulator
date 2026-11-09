"""SQLite storage: users, login events, step-up challenges and sessions."""
from __future__ import annotations

import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username     TEXT PRIMARY KEY,
    pw_hash      TEXT NOT NULL,
    totp_secret  TEXT NOT NULL,   -- encrypt at rest in production
    totp_last_step INTEGER NOT NULL DEFAULT -1,  -- last accepted TOTP time step (replay guard)
    created_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS login_events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,   -- naive UTC ISO-8601
    username     TEXT NOT NULL,
    ip           TEXT NOT NULL,
    asn          INTEGER NOT NULL,
    asn_type     TEXT NOT NULL,
    country      TEXT NOT NULL,
    city         TEXT NOT NULL,
    lat          REAL NOT NULL,
    lon          REAL NOT NULL,
    device_id    TEXT NOT NULL,
    headless     INTEGER NOT NULL,
    password_ok  INTEGER NOT NULL,
    score        REAL NOT NULL,
    reasons      TEXT NOT NULL,
    decision     TEXT NOT NULL,   -- allow | step_up | block | signup
    outcome      TEXT NOT NULL,   -- success | bad_password | blocked | pending | challenge_failed | challenge_expired
    sim_label    TEXT             -- optional ground truth sent by the attacker console
);
CREATE INDEX IF NOT EXISTS ix_events_user ON login_events(username, ts);
CREATE TABLE IF NOT EXISTS challenges (
    id            TEXT PRIMARY KEY,
    event_id      INTEGER NOT NULL REFERENCES login_events(id),
    username      TEXT NOT NULL,
    expires_at    TEXT NOT NULL,
    attempts_left INTEGER NOT NULL,
    status        TEXT NOT NULL   -- open | passed | failed | expired
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash   TEXT PRIMARY KEY,
    username     TEXT NOT NULL,
    device_id    TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    expires_at   TEXT NOT NULL
);
"""


class Database:
    """Thin wrapper around one SQLite connection, serialised with a lock."""

    def __init__(self, path: str):
        self.conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)
        self.lock = threading.RLock()

    def one(self, sql: str, args: tuple = ()) -> sqlite3.Row | None:
        with self.lock:
            return self.conn.execute(sql, args).fetchone()

    def all(self, sql: str, args: tuple = ()) -> list[sqlite3.Row]:
        with self.lock:
            return self.conn.execute(sql, args).fetchall()

    def run(self, sql: str, args: tuple = ()) -> int:
        with self.lock:
            return self.conn.execute(sql, args).lastrowid
