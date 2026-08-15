"""SQLite storage for Pulse check history."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


DATA_DIR = Path.home() / ".local" / "share" / "pulse"
DB_FILE = DATA_DIR / "pulse.db"


def ensure_data_dir() -> None:
    """Ensure the data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """Get a database connection.
    
    Returns:
        sqlite3.Connection: Database connection.
    """
    ensure_data_dir()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize the database schema."""
    ensure_data_dir()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            status_code INTEGER,
            response_time REAL,
            is_up INTEGER NOT NULL,
            error_message TEXT
        )
    """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_checks_url ON checks(url)
    """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_checks_timestamp ON checks(timestamp)
    """
    )
    conn.commit()
    conn.close()


def record_check(
    url: str,
    status_code: int | None,
    response_time: float,
    is_up: bool,
    error_message: str | None = None,
) -> int:
    """Record a check result in the database.
    
    Args:
        url: The URL that was checked.
        status_code: HTTP status code (None if request failed).
        response_time: Response time in seconds.
        is_up: Whether the endpoint is considered up.
        error_message: Error message if the check failed.
    
    Returns:
        int: The ID of the inserted record.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO checks (url, timestamp, status_code, response_time, is_up, error_message)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            url,
            datetime.now().isoformat(),
            status_code,
            response_time,
            1 if is_up else 0,
            error_message,
        ),
    )
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    return record_id  # type: ignore


def get_history(url: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """Get check history.
    
    Args:
        url: Optional URL filter. If None, returns all checks.
        limit: Maximum number of records to return.
    
    Returns:
        list[dict]: List of check records.
    """
    conn = get_connection()
    cursor = conn.cursor()
    if url:
        cursor.execute(
            """
            SELECT * FROM checks WHERE url = ? ORDER BY timestamp DESC LIMIT ?
        """,
            (url, limit),
        )
    else:
        cursor.execute(
            """
            SELECT * FROM checks ORDER BY timestamp DESC LIMIT ?
        """,
            (limit,),
        )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_status(url: str | None = None) -> dict[str, Any]:
    """Get current status of endpoints.
    
    Args:
        url: Optional URL filter. If None, returns status for all URLs.
    
    Returns:
        dict: Status information including current state and uptime percentage.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    if url:
        cursor.execute(
            """
            SELECT url, 
                   COUNT(*) as total_checks,
                   SUM(is_up) as up_checks,
                   MAX(timestamp) as last_check,
                   (SELECT is_up FROM checks WHERE url = ? ORDER BY timestamp DESC LIMIT 1) as current_status
            FROM checks WHERE url = ?
            GROUP BY url
        """,
            (url, url),
        )
    else:
        cursor.execute(
            """
            SELECT url, 
                   COUNT(*) as total_checks,
                   SUM(is_up) as up_checks,
                   MAX(timestamp) as last_check,
                   (SELECT is_up FROM checks c2 WHERE c2.url = checks.url ORDER BY timestamp DESC LIMIT 1) as current_status
            FROM checks
            GROUP BY url
        """
        )
    
    rows = cursor.fetchall()
    conn.close()
    
    status = {}
    for row in rows:
        url = row["url"]
        total = row["total_checks"]
        up = row["up_checks"] or 0
        uptime = (up / total * 100) if total > 0 else 0
        status[url] = {
            "url": url,
            "is_up": bool(row["current_status"]),
            "last_check": row["last_check"],
            "total_checks": total,
            "up_checks": up,
            "uptime_percentage": round(uptime, 2),
        }
    return status


def get_last_status(url: str) -> bool | None:
    """Get the last known status for a URL.
    
    Args:
        url: The URL to check.
    
    Returns:
        bool | None: True if up, False if down, None if no history.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT is_up FROM checks WHERE url = ? ORDER BY timestamp DESC LIMIT 1
    """,
        (url,),
    )
    row = cursor.fetchone()
    conn.close()
    return bool(row["is_up"]) if row else None
