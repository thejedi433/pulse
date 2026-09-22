"""Tests for Pulse alerting module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from pulse.alerts import log_alert, format_status_message


@pytest.fixture
def temp_alerts_dir(tmp_path):
    """Create a temporary alerts directory."""
    with patch.object(Path, 'home', return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clean_alerts(temp_alerts_dir):
    """Ensure clean alerts state for each test."""
    from pulse import alerts
    alerts.ALERTS_DIR = temp_alerts_dir / ".local" / "share" / "pulse"
    alerts.ALERTS_FILE = alerts.ALERTS_DIR / "alerts.log"
    yield temp_alerts_dir / ".local" / "share" / "pulse" / "alerts.log"


@pytest.mark.usefixtures('clean_alerts')
def test_log_alert_initial_up(clean_alerts):
    """Test logging initial UP status."""
    from pulse.alerts import ALERTS_FILE
    message = log_alert("https://example.com", None, True)
    
    assert "INITIAL" in message
    assert "UP" in message
    assert "https://example.com" in message
    assert clean_alerts.exists()
    
    # Verify file content
    with open(clean_alerts) as f:
        content = f.read()
    assert "INITIAL" in content
    assert "UP" in content


def test_log_alert_initial_down(clean_alerts):
    """Test logging initial DOWN status."""
    message = log_alert("https://example.com", None, False)
    
    assert "INITIAL" in message
    assert "DOWN" in message
    assert "https://example.com" in message


def test_log_alert_state_change_up_to_down(clean_alerts):
    """Test logging state change from UP to DOWN."""
    message = log_alert("https://example.com", True, False)
    
    assert "STATE CHANGE" in message
    assert "UP" in message
    assert "DOWN" in message
    assert "https://example.com" in message


def test_log_alert_state_change_down_to_up(clean_alerts):
    """Test logging state change from DOWN to UP."""
    message = log_alert("https://example.com", False, True)
    
    assert "STATE CHANGE" in message
    assert "DOWN" in message
    assert "UP" in message


@pytest.mark.usefixtures('clean_alerts')
def test_log_alert_no_change(clean_alerts):
    """Test that no alert is logged when status doesn't change."""
    message = log_alert("https://example.com", True, True)
    
    assert message == ""
    
    # File should not be created or should be empty
    if clean_alerts.exists():
        with open(clean_alerts) as f:
            content = f.read().strip()
        assert content == ""


@pytest.mark.usefixtures('clean_alerts')
def test_log_alert_multiple_alerts(clean_alerts):
    """Test logging multiple alerts."""
    log_alert("https://example.com", None, True)
    log_alert("https://google.com", None, True)
    log_alert("https://example.com", True, False)
    
    with open(clean_alerts) as f:
        lines = f.readlines()
    
    assert len(lines) == 3
    assert "INITIAL" in lines[0]
    assert "INITIAL" in lines[1]
    assert "STATE CHANGE" in lines[2]


def test_format_status_message_up():
    """Test formatting UP status message."""
    message = format_status_message(
        "https://example.com",
        is_up=True,
        response_time=0.123,
        status_code=200,
    )
    
    assert "✓" in message
    assert "UP" in message
    assert "status=200" in message
    assert "time=123ms" in message
    assert "https://example.com" in message


def test_format_status_message_down():
    """Test formatting DOWN status message."""
    message = format_status_message(
        "https://example.com",
        is_up=False,
        response_time=1.5,
        status_code=500,
    )
    
    assert "✗" in message
    assert "DOWN" in message
    assert "status=500" in message
    assert "time=1500ms" in message


def test_format_status_message_no_status_code():
    """Test formatting message with no status code (network error)."""
    message = format_status_message(
        "https://example.com",
        is_up=False,
        response_time=0.5,
        status_code=None,
    )
    
    assert "✗" in message
    assert "DOWN" in message
    assert "status=N/A" in message


@pytest.mark.usefixtures('clean_alerts')
def test_log_alert_with_notifier(clean_alerts):
    """Test log_alert sends notification when notifier is provided."""
    from unittest.mock import MagicMock
    
    notifier = MagicMock()
    notifier.is_configured = True
    
    message = log_alert("https://example.com", None, True, notifier=notifier)
    
    assert "INITIAL" in message
    notifier.send_notification.assert_called_once_with(message)


def test_log_alert_notifier_not_configured(clean_alerts):
    """Test log_alert skips notification when notifier not configured."""
    from unittest.mock import MagicMock
    
    notifier = MagicMock()
    notifier.is_configured = False
    
    message = log_alert("https://example.com", None, True, notifier=notifier)
    
    assert "INITIAL" in message
    notifier.send_notification.assert_not_called()
