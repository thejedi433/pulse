"""Tests for Pulse storage module."""

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from pulse.storage import (
    init_db,
    record_check,
    get_history,
    get_status,
    get_last_status,
    DB_FILE,
)


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory."""
    with patch.object(Path, 'home', return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clean_db(temp_data_dir):
    """Ensure clean database state for each test."""
    from pulse import storage
    storage.DATA_DIR = temp_data_dir / ".local" / "share" / "pulse"
    storage.DB_FILE = storage.DATA_DIR / "pulse.db"
    init_db()
    yield temp_data_dir / ".local" / "share" / "pulse" / "pulse.db"


@pytest.mark.usefixtures('clean_db')
def test_init_db(clean_db):
    """Test database initialization."""
    assert clean_db.exists()
    
    # Verify tables exist
    conn = sqlite3.connect(clean_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()
    
    assert "checks" in tables


def test_record_check(clean_db):
    """Test recording a check."""
    record_id = record_check(
        url="https://example.com",
        status_code=200,
        response_time=0.15,
        is_up=True,
    )
    
    assert record_id > 0
    
    history = get_history("https://example.com")
    assert len(history) == 1
    assert history[0]["status_code"] == 200
    assert history[0]["response_time"] == 0.15
    assert history[0]["is_up"] == 1


def test_record_check_down(clean_db):
    """Test recording a failed check."""
    record_check(
        url="https://example.com",
        status_code=500,
        response_time=1.2,
        is_up=False,
        error_message="Server error",
    )
    
    history = get_history("https://example.com")
    assert len(history) == 1
    assert history[0]["status_code"] == 500
    assert history[0]["is_up"] == 0
    assert history[0]["error_message"] == "Server error"


def test_record_check_error(clean_db):
    """Test recording a check with network error."""
    record_check(
        url="https://example.com",
        status_code=None,
        response_time=5.0,
        is_up=False,
        error_message="Connection refused",
    )
    
    history = get_history("https://example.com")
    assert len(history) == 1
    assert history[0]["status_code"] is None
    assert history[0]["error_message"] == "Connection refused"


def test_get_history_multiple(clean_db):
    """Test getting history with multiple records."""
    for i in range(5):
        record_check(
            url="https://example.com",
            status_code=200,
            response_time=0.1 + i * 0.01,
            is_up=True,
        )
    
    history = get_history("https://example.com", limit=3)
    assert len(history) == 3  # Limited to 3


def test_get_history_different_urls(clean_db):
    """Test history filtering by URL."""
    record_check("https://example.com", 200, 0.1, True)
    record_check("https://google.com", 200, 0.2, True)
    record_check("https://example.com", 200, 0.15, True)
    
    example_history = get_history("https://example.com")
    google_history = get_history("https://google.com")
    all_history = get_history()
    
    assert len(example_history) == 2
    assert len(google_history) == 1
    assert len(all_history) == 3


def test_get_status(clean_db):
    """Test getting status."""
    record_check("https://example.com", 200, 0.1, True)
    record_check("https://example.com", 200, 0.15, True)
    record_check("https://example.com", 500, 0.2, False)
    
    status = get_status("https://example.com")
    
    assert "https://example.com" in status
    assert status["https://example.com"]["total_checks"] == 3
    assert status["https://example.com"]["up_checks"] == 2
    assert status["https://example.com"]["uptime_percentage"] == pytest.approx(66.67, rel=1e-1)


def test_get_last_status(clean_db):
    """Test getting last status."""
    record_check("https://example.com", 200, 0.1, True)
    record_check("https://example.com", 500, 0.2, False)
    
    last = get_last_status("https://example.com")
    assert last is False  # Last check was down
    
    # No history
    no_history = get_last_status("https://nonexistent.com")
    assert no_history is None
