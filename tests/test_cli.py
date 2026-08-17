"""Tests for Pulse CLI module."""

import argparse
import io
import sys
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import Mock, patch

import pytest

from pulse.cli import (
    cmd_check,
    cmd_add,
    cmd_remove,
    cmd_history,
    cmd_status,
    cmd_monitor,
    create_parser,
)


@pytest.fixture
def mock_check_endpoint():
    """Mock the check_endpoint function."""
    with patch('pulse.cli.check_endpoint') as mock:
        mock.return_value = {
            "url": "https://example.com",
            "status_code": 200,
            "response_time": 0.1,
            "is_up": True,
            "error": None,
        }
        yield mock


@pytest.fixture
def mock_record_check():
    """Mock the record_check function."""
    with patch('pulse.cli.record_check') as mock:
        yield mock


@pytest.fixture
def mock_get_last_status():
    """Mock the get_last_status function."""
    with patch('pulse.cli.get_last_status') as mock:
        mock.return_value = None  # No previous status
        yield mock


@pytest.fixture
def mock_log_alert():
    """Mock the log_alert function."""
    with patch('pulse.cli.log_alert') as mock:
        mock.return_value = "[TEST] Alert message"
        yield mock


@pytest.fixture
def mock_init_db():
    """Mock the init_db function."""
    with patch('pulse.cli.init_db') as mock:
        yield mock


def test_cmd_check_success(
    mock_init_db,
    mock_check_endpoint,
    mock_record_check,
    mock_get_last_status,
    mock_log_alert,
):
    """Test the check command with successful check."""
    args = argparse.Namespace(url="https://example.com", timeout=None)
    
    with redirect_stdout(io.StringIO()) as stdout:
        result = cmd_check(args)
    
    output = stdout.getvalue()
    
    assert result == 0
    assert "✓" in output
    assert "UP" in output
    mock_check_endpoint.assert_called_once()
    mock_record_check.assert_called_once()
    mock_log_alert.assert_called_once()


def test_cmd_check_down(
    mock_init_db,
    mock_check_endpoint,
    mock_record_check,
    mock_get_last_status,
    mock_log_alert,
):
    """Test the check command with failed check."""
    mock_check_endpoint.return_value = {
        "url": "https://example.com",
        "status_code": 500,
        "response_time": 0.5,
        "is_up": False,
        "error": "Server error",
    }
    
    args = argparse.Namespace(url="https://example.com", timeout=None)
    
    with redirect_stdout(io.StringIO()) as stdout:
        result = cmd_check(args)
    
    output = stdout.getvalue()
    
    assert result == 1
    assert "✗" in output
    assert "DOWN" in output


def test_cmd_check_with_timeout(
    mock_init_db,
    mock_check_endpoint,
    mock_record_check,
    mock_get_last_status,
    mock_log_alert,
):
    """Test the check command with custom timeout."""
    args = argparse.Namespace(url="https://example.com", timeout=30)
    
    cmd_check(args)
    
    mock_check_endpoint.assert_called_once_with("https://example.com", timeout=30)


def test_cmd_add():
    """Test the add command."""
    with patch('pulse.cli.add_endpoint') as mock_add_endpoint:
        args = argparse.Namespace(url="https://example.com", interval=120, timeout=15)
        
        with redirect_stdout(io.StringIO()) as stdout:
            cmd_add(args)
        
        output = stdout.getvalue()
        
        mock_add_endpoint.assert_called_once_with(
            "https://example.com",
            interval=120,
            timeout=15,
        )
        assert "Added endpoint" in output


def test_cmd_remove_success():
    """Test the remove command with success."""
    with patch('pulse.cli.remove_endpoint') as mock_remove:
        mock_remove.return_value = True
        args = argparse.Namespace(url="https://example.com")
        
        with redirect_stdout(io.StringIO()) as stdout:
            cmd_remove(args)
        
        output = stdout.getvalue()
        assert "Removed endpoint" in output


def test_cmd_remove_not_found():
    """Test the remove command with non-existent endpoint."""
    with patch('pulse.cli.remove_endpoint') as mock_remove:
        mock_remove.return_value = False
        args = argparse.Namespace(url="https://example.com")
        
        with pytest.raises(SystemExit) as exc_info:
            cmd_remove(args)
        
        assert exc_info.value.code == 1


def test_create_parser():
    """Test parser creation and basic argument parsing."""
    parser = create_parser()
    
    # Test check command
    args = parser.parse_args(["check", "https://example.com"])
    assert args.command == "check"
    assert args.url == "https://example.com"
    
    # Test add command
    args = parser.parse_args(["add", "https://example.com"])
    assert args.command == "add"
    
    # Test monitor command
    args = parser.parse_args(["monitor"])
    assert args.command == "monitor"
    
    # Test history command
    args = parser.parse_args(["history"])
    assert args.command == "history"
    
    # Test status command
    args = parser.parse_args(["status"])
    assert args.command == "status"
    
    # Test remove command
    args = parser.parse_args(["remove", "https://example.com"])
    assert args.command == "remove"


def test_create_parser_with_options():
    """Test parser with optional arguments."""
    parser = create_parser()
    
    # Test check with timeout
    args = parser.parse_args(["check", "-t", "30", "https://example.com"])
    assert args.timeout == 30
    
    # Test add with interval and timeout
    args = parser.parse_args([
        "add", "-i", "120", "-t", "15", "https://example.com"
    ])
    assert args.interval == 120
    assert args.timeout == 15
    
    # Test history with limit and url
    args = parser.parse_args([
        "history", "-u", "https://example.com", "-n", "50"
    ])
    assert args.url == "https://example.com"
    assert args.limit == 50


def test_parser_help():
    """Test that help is displayed with --help flag."""
    parser = create_parser()
    
    with redirect_stdout(io.StringIO()) as stdout:
        with redirect_stderr(io.StringIO()) as stderr:
            try:
                parser.parse_args(["--help"])
            except SystemExit:
                pass  # argparse calls sys.exit(0) after printing help
    
    output = stdout.getvalue() + stderr.getvalue()
    assert "usage:" in output.lower()
    assert "pulse" in output.lower()
    assert "check" in output
    assert "monitor" in output
    assert "add" in output
    assert "remove" in output


@pytest.fixture
def mock_load_config():
    """Mock the load_config function."""
    with patch('pulse.cli.load_config') as mock:
        mock.return_value = {
            "check_interval": 60,
            "default_timeout": 10,
            "endpoints": [],
        }
        yield mock


@pytest.fixture
def mock_get_endpoints():
    """Mock the get_endpoints function."""
    with patch('pulse.cli.get_endpoints') as mock:
        mock.return_value = []
        yield mock


@pytest.fixture
def mock_get_status():
    """Mock the get_status function."""
    with patch('pulse.cli.get_status') as mock:
        mock.return_value = {}
        yield mock


@pytest.fixture
def mock_get_history():
    """Mock the get_history function."""
    with patch('pulse.cli.get_history') as mock:
        mock.return_value = []
        yield mock


def test_cmd_monitor_passes_expected_status(
    mock_init_db,
    mock_load_config,
    mock_get_endpoints,
    mock_check_endpoint,
    mock_record_check,
    mock_get_last_status,
    mock_log_alert,
):
    """Test that monitor command passes expected_status from endpoint config."""
    mock_get_endpoints.return_value = [
        {"url": "https://example.com", "timeout": 5, "expected_status": 201}
    ]
    mock_load_config.return_value = {
        "check_interval": 60,
        "default_timeout": 10,
        "endpoints": [],
    }
    # Raise KeyboardInterrupt after one check
    mock_check_endpoint.side_effect = KeyboardInterrupt
    
    args = argparse.Namespace()
    
    with redirect_stdout(io.StringIO()):
        cmd_monitor(args)
    
    mock_check_endpoint.assert_called_once_with(
        "https://example.com", timeout=5, expected_status=201
    )


def test_cmd_monitor_uses_default_expected_status(
    mock_init_db,
    mock_load_config,
    mock_get_endpoints,
    mock_check_endpoint,
    mock_record_check,
    mock_get_last_status,
    mock_log_alert,
):
    """Test that monitor defaults expected_status to 200 when not configured."""
    mock_get_endpoints.return_value = [
        {"url": "https://example.com", "timeout": 5}
    ]
    mock_load_config.return_value = {
        "check_interval": 60,
        "default_timeout": 10,
        "endpoints": [],
    }
    mock_check_endpoint.side_effect = KeyboardInterrupt
    
    args = argparse.Namespace()
    
    with redirect_stdout(io.StringIO()):
        cmd_monitor(args)
    
    mock_check_endpoint.assert_called_once_with(
        "https://example.com", timeout=5, expected_status=200
    )


def test_cmd_monitor_no_endpoints(
    mock_init_db,
    mock_get_endpoints,
):
    """Test that monitor exits when no endpoints configured."""
    mock_get_endpoints.return_value = []
    
    args = argparse.Namespace()
    
    with pytest.raises(SystemExit) as exc_info:
        with redirect_stdout(io.StringIO()) as stdout:
            cmd_monitor(args)
    
    assert exc_info.value.code == 1
    assert "No endpoints configured" in stdout.getvalue()


def test_cmd_history_no_data(mock_init_db, mock_get_history):
    """Test history command with no data."""
    mock_get_history.return_value = []
    
    args = argparse.Namespace(url=None, limit=20)
    
    with redirect_stdout(io.StringIO()) as stdout:
        cmd_history(args)
    
    assert "No check history" in stdout.getvalue()


def test_cmd_history_with_data(mock_init_db, mock_get_history):
    """Test history command with data."""
    mock_get_history.return_value = [
        {
            "timestamp": "2024-01-01T12:00:00.000000",
            "url": "https://example.com",
            "status_code": 200,
            "response_time": 0.1,
            "is_up": 1,
            "error_message": None,
        }
    ]
    
    args = argparse.Namespace(url=None, limit=20)
    
    with redirect_stdout(io.StringIO()) as stdout:
        cmd_history(args)
    
    output = stdout.getvalue()
    assert "https://example.com" in output
    assert "UP" in output
    assert "200" in output


def test_cmd_history_url_filter(mock_init_db, mock_get_history):
    """Test history command filters by URL."""
    mock_get_history.return_value = []
    
    args = argparse.Namespace(url="https://example.com", limit=50)
    
    with redirect_stdout(io.StringIO()):
        cmd_history(args)
    
    mock_get_history.assert_called_once_with("https://example.com", limit=50)


def test_cmd_status_no_data(mock_init_db, mock_get_status):
    """Test status command with no data."""
    mock_get_status.return_value = {}
    
    args = argparse.Namespace(url=None)
    
    with redirect_stdout(io.StringIO()):
        cmd_status(args)


def test_cmd_status_single_url(mock_init_db, mock_get_status):
    """Test status command for single URL."""
    mock_get_status.return_value = {
        "https://example.com": {
            "is_up": True,
            "last_check": "2024-01-01T12:00:00.000000",
            "total_checks": 10,
            "up_checks": 9,
            "uptime_percentage": 90.0,
        }
    }
    
    args = argparse.Namespace(url="https://example.com")
    
    with redirect_stdout(io.StringIO()) as stdout:
        cmd_status(args)
    
    output = stdout.getvalue()
    assert "✓" in output
    assert "UP" in output
    assert "90.0%" in output


def test_cmd_status_all_urls(mock_init_db, mock_get_status):
    """Test status command for all URLs."""
    mock_get_status.return_value = {
        "https://example.com": {
            "is_up": True,
            "last_check": "2024-01-01T12:00:00.000000",
            "total_checks": 10,
            "up_checks": 10,
            "uptime_percentage": 100.0,
        },
        "https://google.com": {
            "is_up": False,
            "last_check": "2024-01-01T12:00:00.000000",
            "total_checks": 10,
            "up_checks": 5,
            "uptime_percentage": 50.0,
        },
    }
    
    args = argparse.Namespace(url=None)
    
    with redirect_stdout(io.StringIO()) as stdout:
        cmd_status(args)
    
    output = stdout.getvalue()
    assert "https://example.com" in output
    assert "https://google.com" in output


def test_main_no_command():
    """Test main with no command prints help."""
    from pulse.cli import main
    
    with patch('sys.argv', ['pulse']):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0


def test_main_check_command(
    mock_init_db,
    mock_check_endpoint,
    mock_record_check,
    mock_get_last_status,
    mock_log_alert,
):
    """Test main dispatches check command."""
    from pulse.cli import main
    
    with patch('sys.argv', ['pulse', 'check', 'https://example.com']):
        with redirect_stdout(io.StringIO()):
            main()
    
    mock_check_endpoint.assert_called_once()
