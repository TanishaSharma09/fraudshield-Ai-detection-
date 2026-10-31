"""FraudShield AI - Database Connection Manager.

Provides thread-safe SQLite connection factory, WAL mode configuration,
foreign key enforcement, and structured query execution utilities.
"""

import sqlite3
from contextlib import contextmanager
from typing import Any, Generator, Sequence
from backend.core.config import settings


def create_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Creates and configures an SQLite database connection with WAL mode and foreign keys enabled."""
    target_path = str(db_path or settings.DATABASE_PATH)
    conn = sqlite3.connect(
        target_path,
        check_same_thread=False,
        timeout=15.0,
    )
    # Enable dict-like column access
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high-throughput concurrent reads and writes
    conn.execute("PRAGMA journal_mode = WAL;")
    # Explicitly enforce foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON;")
    # Synchronous NORMAL for optimal balance between safety and performance in WAL mode
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


@contextmanager
def get_db_connection(db_path: str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite connections with automatic commit and rollback."""
    conn = create_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query_all(sql: str, params: Sequence[Any] | tuple = (), db_path: str | None = None) -> list[dict[str, Any]]:
    """Executes a read query and returns all matching rows as dictionaries."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def query_one(sql: str, params: Sequence[Any] | tuple = (), db_path: str | None = None) -> dict[str, Any] | None:
    """Executes a read query and returns the first matching row as a dictionary."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        row = cursor.fetchone()
        return dict(row) if row else None


def execute_stmt(sql: str, params: Sequence[Any] | tuple = (), db_path: str | None = None) -> int:
    """Executes an INSERT/UPDATE/DELETE statement and returns the last row ID or affected row count."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        return cursor.lastrowid or cursor.rowcount


def execute_many(sql: str, seq_of_params: Sequence[Sequence[Any]], db_path: str | None = None) -> int:
    """Executes a bulk parameterized statement across multiple records."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.executemany(sql, seq_of_params)
        return cursor.rowcount


def execute_script(sql_script: str, db_path: str | None = None) -> None:
    """Executes a multi-statement SQL script (such as DDL migrations)."""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.executescript(sql_script)
