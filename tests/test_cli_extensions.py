"""Tests for CLI extensions: expected-status and JSON output."""

import argparse
import json
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

import pytest

from pulse.cli import (
    cmd_add,
    cmd_check,
    cmd_history,
    cmd_status,
    create_parser,
)


class TestExpectedStatusCLI:
    """Test --expected-status support in CLI."""

    def test_parser_check_accepts_expected_status(self):
        """Test that check command accepts --expected-status flag."""
        parser = create_parser()
        args = parser.parse_args(["check", "https://example.com", "--expected-status", "201"])
        assert args.expected_status == 201

    def test_parser_add_accepts_expected_status(self):
        """Test that add command accepts --expected-status flag."""
        parser = create_parser()
        args = parser.parse_args(["add", "https://example.com", "--expected-status", "201"])
        assert args.expected_status == 201

    def test_cmd_check_passes_expected_status_to_checker(self):
        """Test that cmd_check passes expected_status to check_endpoint."""
        with patch("pulse.cli.check_endpoint") as mock_check, \
             patch("pulse.cli.record_check"), \
             patch("pulse.cli.get_last_status", return_value=None), \
             patch("pulse.cli.log_alert"), \
             patch("pulse.cli.init_db"):

            mock_check.return_value = {
                "url": "https://example.com",
                "status_code": 201,
                "response_time": 0.1,
                "is_up": True,
                "error": None,
            }

            args = argparse.Namespace(
                url="https://example.com",
                timeout=10,
                expected_status=201,
            )

            with redirect_stdout(StringIO()):
                cmd_check(args)

            mock_check.assert_called_once_with(
                "https://example.com",
                timeout=10,
                expected_status=201,
            )

    def test_cmd_add_passes_expected_status_to_config(self):
        """Test that cmd_add passes expected_status to add_endpoint."""
        with patch("pulse.cli.add_endpoint") as mock_add:
            args = argparse.Namespace(
                url="https://example.com",
                interval=60,
                timeout=10,
                expected_status=201,
            )

            with redirect_stdout(StringIO()):
                cmd_add(args)

            mock_add.assert_called_once_with(
                "https://example.com",
                interval=60,
                timeout=10,
                expected_status=201,
            )

    def test_cmd_check_default_expected_status_is_200(self):
        """Test that check command defaults expected_status to 200."""
        parser = create_parser()
        args = parser.parse_args(["check", "https://example.com"])
        assert args.expected_status == 200

    def test_cmd_add_default_expected_status_is_200(self):
        """Test that add command defaults expected_status to 200."""
        parser = create_parser()
        args = parser.parse_args(["add", "https://example.com"])
        assert args.expected_status == 200


class TestJSONOutput:
    """Test --json output for scripting."""

    def test_parser_check_accepts_json(self):
        """Test that check command accepts --json flag."""
        parser = create_parser()
        args = parser.parse_args(["check", "https://example.com", "--json"])
        assert args.json is True

    def test_parser_status_accepts_json(self):
        """Test that status command accepts --json flag."""
        parser = create_parser()
        args = parser.parse_args(["status", "--json"])
        assert args.json is True

    def test_parser_history_accepts_json(self):
        """Test that history command accepts --json flag."""
        parser = create_parser()
        args = parser.parse_args(["history", "--json"])
        assert args.json is True

    def test_cmd_check_json_output(self):
        """Test that check command outputs valid JSON when --json used."""
        with patch("pulse.cli.check_endpoint") as mock_check, \
             patch("pulse.cli.record_check"), \
             patch("pulse.cli.get_last_status", return_value=None), \
             patch("pulse.cli.log_alert"), \
             patch("pulse.cli.init_db"):

            mock_check.return_value = {
                "url": "https://example.com",
                "status_code": 200,
                "response_time": 0.123,
                "is_up": True,
                "error": None,
            }

            args = argparse.Namespace(
                url="https://example.com",
                timeout=10,
                expected_status=200,
                json=True,
            )

            output = StringIO()
            with redirect_stdout(output):
                cmd_check(args)

            data = json.loads(output.getvalue())
            assert data["url"] == "https://example.com"
            assert data["status_code"] == 200
            assert data["is_up"] is True
            assert data["response_time"] == 0.123

    def test_cmd_status_json_output(self):
        """Test that status command outputs valid JSON when --json used."""
        with patch("pulse.cli.get_status") as mock_status, \
             patch("pulse.cli.init_db"):

            mock_status.return_value = {
                "https://example.com": {
                    "url": "https://example.com",
                    "is_up": True,
                    "last_check": "2026-01-01T12:00:00",
                    "total_checks": 10,
                    "up_checks": 9,
                    "uptime_percentage": 90.0,
                }
            }

            args = argparse.Namespace(url=None, json=True)

            output = StringIO()
            with redirect_stdout(output):
                cmd_status(args)

            data = json.loads(output.getvalue())
            assert "https://example.com" in data
            assert data["https://example.com"]["is_up"] is True
            assert data["https://example.com"]["uptime_percentage"] == 90.0

    def test_cmd_history_json_output(self):
        """Test that history command outputs valid JSON when --json used."""
        with patch("pulse.cli.get_history") as mock_history, \
             patch("pulse.cli.init_db"):

            mock_history.return_value = [
                {
                    "timestamp": "2026-01-01T12:00:00",
                    "url": "https://example.com",
                    "status_code": 200,
                    "response_time": 0.1,
                    "is_up": 1,
                    "error_message": None,
                }
            ]

            args = argparse.Namespace(url=None, limit=20, json=True)

            output = StringIO()
            with redirect_stdout(output):
                cmd_history(args)

            data = json.loads(output.getvalue())
            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["url"] == "https://example.com"
            assert data[0]["status_code"] == 200

    def test_cmd_check_json_down_status(self):
        """Test JSON output for failed check."""
        with patch("pulse.cli.check_endpoint") as mock_check, \
             patch("pulse.cli.record_check"), \
             patch("pulse.cli.get_last_status", return_value=None), \
             patch("pulse.cli.log_alert"), \
             patch("pulse.cli.init_db"):

            mock_check.return_value = {
                "url": "https://example.com",
                "status_code": 500,
                "response_time": 0.5,
                "is_up": False,
                "error": "Server error",
            }

            args = argparse.Namespace(
                url="https://example.com",
                timeout=10,
                expected_status=200,
                json=True,
            )

            output = StringIO()
            with redirect_stdout(output):
                result = cmd_check(args)

            assert result == 1
            data = json.loads(output.getvalue())
            assert data["is_up"] is False
            assert data["error"] == "Server error"

    def test_cmd_status_json_empty(self):
        """Test JSON output when no status data."""
        with patch("pulse.cli.get_status") as mock_status, \
             patch("pulse.cli.init_db"):

            mock_status.return_value = {}
            args = argparse.Namespace(url=None, json=True)

            output = StringIO()
            with redirect_stdout(output):
                cmd_status(args)

            data = json.loads(output.getvalue())
            assert data == {}

    def test_cmd_history_json_empty(self):
        """Test JSON output when no history."""
        with patch("pulse.cli.get_history") as mock_history, \
             patch("pulse.cli.init_db"):

            mock_history.return_value = []
            args = argparse.Namespace(url=None, limit=20, json=True)

            output = StringIO()
            with redirect_stdout(output):
                cmd_history(args)

            data = json.loads(output.getvalue())
            assert data == []
