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
