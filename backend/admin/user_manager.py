"""
User manager — CRUD for admin console users stored in SQLite.

Schema:
    admin_users (id, username, password_hash, role, created_at, last_login)
    admin_api_keys (id, user_id, key_prefix, key_hash, label, created_at, last_used)
    audit_log (id, username, action, detail, ip, ts)

The admin DB lives at DATABASE_DIR/admin.db (separate from devtrack.db).
"""
from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from backend.admin.auth import hash_password, verify_password


def _admin_db_path() -> Path:
    db_dir = os.environ.get("DATABASE_DIR") or (
        Path(os.environ.get("PROJECT_ROOT", ".")) / "Data" / "db"
    )
    return Path(db_dir) / "admin.db"


@contextmanager
def _conn():
    path = _admin_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS admin_users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role          TEXT NOT NULL DEFAULT 'viewer',
                created_at    TEXT NOT NULL DEFAULT (datetime('now')),
                last_login    TEXT
            );
            CREATE TABLE IF NOT EXISTS admin_api_keys (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES admin_users(id) ON DELETE CASCADE,
                key_prefix  TEXT NOT NULL,
                key_hash    TEXT NOT NULL,
                label       TEXT NOT NULL DEFAULT '',
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                last_used   TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                action   TEXT NOT NULL,
                detail   TEXT NOT NULL DEFAULT '',
                ip       TEXT NOT NULL DEFAULT '',
                ts       TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)


# ---------------------------------------------------------------------------
# User dataclass
# ---------------------------------------------------------------------------

@dataclass
class AdminUser:
    id: int
    username: str
    role: str
    created_at: str
    last_login: Optional[str]


@dataclass
class ApiKey:
    id: int
    user_id: int
    key_prefix: str
    label: str
    created_at: str
    last_used: Optional[str]


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------

def list_users() -> list[AdminUser]:
    with _conn() as con:
        rows = con.execute(
            "SELECT id, username, role, created_at, last_login FROM admin_users ORDER BY id"
        ).fetchall()
    return [AdminUser(**dict(r)) for r in rows]


def get_user(username: str) -> Optional[AdminUser]:
    with _conn() as con:
        row = con.execute(
            "SELECT id, username, role, created_at, last_login FROM admin_users WHERE username=?",
            (username,),
        ).fetchone()
    return AdminUser(**dict(row)) if row else None


def create_user(username: str, password: str, role: str = "viewer") -> AdminUser:
    hashed = hash_password(password)
    with _conn() as con:
        con.execute(
            "INSERT INTO admin_users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, hashed, role),
        )
    return get_user(username)  # type: ignore[return-value]


def update_password(username: str, new_password: str) -> bool:
    hashed = hash_password(new_password)
    with _conn() as con:
        cur = con.execute(
            "UPDATE admin_users SET password_hash=? WHERE username=?",
            (hashed, username),
        )
    return cur.rowcount > 0


def update_role(username: str, role: str) -> bool:
    with _conn() as con:
        cur = con.execute(
            "UPDATE admin_users SET role=? WHERE username=?",
            (role, username),
        )
    return cur.rowcount > 0


def delete_user(username: str) -> bool:
    with _conn() as con:
        cur = con.execute("DELETE FROM admin_users WHERE username=?", (username,))
    return cur.rowcount > 0


def touch_last_login(username: str) -> None:
    with _conn() as con:
        con.execute(
            "UPDATE admin_users SET last_login=datetime('now') WHERE username=?",
            (username,),
        )


def verify_user_password(username: str, password: str) -> bool:
    with _conn() as con:
        row = con.execute(
            "SELECT password_hash FROM admin_users WHERE username=?", (username,)
        ).fetchone()
    if not row:
        return False
    return verify_password(password, row["password_hash"])


def ensure_default_admin(username: str, password: str) -> None:
    """Create the initial admin account if no users exist yet."""
    with _conn() as con:
        count = con.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0]
    if count == 0:
        create_user(username, password, role="admin")


# ---------------------------------------------------------------------------
# API key management
# ---------------------------------------------------------------------------

def create_api_key(username: str, label: str = "") -> tuple[str, ApiKey]:
    """Returns (raw_key, ApiKey) — raw_key is shown once only."""
    user = get_user(username)
    if not user:
        raise ValueError(f"User not found: {username}")
    raw = secrets.token_urlsafe(32)
    prefix = raw[:8]
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    with _conn() as con:
        con.execute(
            "INSERT INTO admin_api_keys (user_id, key_prefix, key_hash, label) VALUES (?,?,?,?)",
            (user.id, prefix, key_hash, label),
        )
        row = con.execute(
            "SELECT id, user_id, key_prefix, label, created_at, last_used "
            "FROM admin_api_keys WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (user.id,),
        ).fetchone()
    return raw, ApiKey(**dict(row))


def list_api_keys(username: str) -> list[ApiKey]:
    user = get_user(username)
    if not user:
        return []
    with _conn() as con:
        rows = con.execute(
            "SELECT id, user_id, key_prefix, label, created_at, last_used "
            "FROM admin_api_keys WHERE user_id=? ORDER BY id",
            (user.id,),
        ).fetchall()
    return [ApiKey(**dict(r)) for r in rows]


def revoke_api_key(key_id: int) -> bool:
    with _conn() as con:
        cur = con.execute("DELETE FROM admin_api_keys WHERE id=?", (key_id,))
    return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def log_action(username: str, action: str, detail: str = "", ip: str = "") -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO audit_log (username, action, detail, ip) VALUES (?,?,?,?)",
            (username, action, detail, ip),
        )


def get_audit_log(limit: int = 100) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
