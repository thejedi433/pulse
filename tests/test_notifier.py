"""Tests for Telegram notifier."""

import os
from unittest.mock import patch, MagicMock

from pulse.notifier import TelegramNotifier, get_notifier_from_env


class TestTelegramNotifier:
    """Test TelegramNotifier class."""

    def test_init_sets_token_and_chat_id(self):
        """Test initialization sets token and chat_id."""
        notifier = TelegramNotifier("test_token", "test_chat")
        assert notifier.token == "test_token"
        assert notifier.chat_id == "test_chat"

    def test_is_configured_true(self):
        """Test is_configured returns True when both token and chat_id are set."""
        notifier = TelegramNotifier("token", "chat")
        assert notifier.is_configured is True

    def test_is_configured_false_empty_token(self):
        """Test is_configured returns False when token is empty."""
        notifier = TelegramNotifier("", "chat")
        assert notifier.is_configured is False

    def test_is_configured_false_empty_chat_id(self):
        """Test is_configured returns False when chat_id is empty."""
        notifier = TelegramNotifier("token", "")
        assert notifier.is_configured is False

    def test_is_configured_false_both_empty(self):
        """Test is_configured returns False when both are empty."""
        notifier = TelegramNotifier("", "")
        assert notifier.is_configured is False

    @patch("pulse.notifier.requests.post")
    def test_send_success(self, mock_post):
        """Test successful message send."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        notifier = TelegramNotifier("token", "chat")
        result = notifier.send("test message")

        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "token" in call_args[0][0]
        assert call_args[1]["json"]["chat_id"] == "chat"
        assert call_args[1]["json"]["text"] == "test message"

    @patch("pulse.notifier.requests.post")
    def test_send_failure_not_ok(self, mock_post):
        """Test send returns False when Telegram returns ok=False."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": False}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        notifier = TelegramNotifier("token", "chat")
        result = notifier.send("test message")

        assert result is False

    @patch("pulse.notifier.requests.post")
    def test_send_http_error(self, mock_post):
        """Test send returns False on HTTP error."""
        import requests
        mock_post.side_effect = requests.exceptions.RequestException("error")

        notifier = TelegramNotifier("token", "chat")
        result = notifier.send("test message")

        assert result is False

    @patch("pulse.notifier.requests.post")
    def test_send_notification_alias(self, mock_post):
        """Test send_notification is an alias for send."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        notifier = TelegramNotifier("token", "chat")
        result = notifier.send_notification("test message")

        assert result is True

    @patch("pulse.notifier.requests.post")
    def test_send_timeout(self, mock_post):
        """Test send handles timeout gracefully."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("timeout")

        notifier = TelegramNotifier("token", "chat")
        result = notifier.send("test message")

        assert result is False

    @patch("pulse.notifier.requests.post")
    def test_send_connection_error(self, mock_post):
        """Test send handles connection error gracefully."""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("connection failed")

        notifier = TelegramNotifier("token", "chat")
        result = notifier.send("test message")

        assert result is False


class TestGetNotifierFromEnv:
    """Test get_notifier_from_env function."""

    @patch.dict(os.environ, {
        "UPTIME_PING_TELEGRAM_TOKEN": "env_token",
        "UPTIME_PING_TELEGRAM_CHAT_ID": "env_chat"
    })
    def test_get_notifier_from_env_both_set(self):
        """Test returns notifier when both env vars are set."""
        notifier = get_notifier_from_env()
        assert notifier is not None
        assert notifier.token == "env_token"
        assert notifier.chat_id == "env_chat"

    @patch.dict(os.environ, {
        "UPTIME_PING_TELEGRAM_TOKEN": "",
        "UPTIME_PING_TELEGRAM_CHAT_ID": "env_chat"
    })
    def test_get_notifier_from_env_empty_token(self):
        """Test returns None when token is empty."""
        notifier = get_notifier_from_env()
        assert notifier is None

    @patch.dict(os.environ, {
        "UPTIME_PING_TELEGRAM_TOKEN": "env_token",
        "UPTIME_PING_TELEGRAM_CHAT_ID": ""
    })
    def test_get_notifier_from_env_empty_chat_id(self):
        """Test returns None when chat_id is empty."""
        notifier = get_notifier_from_env()
        assert notifier is None

    @patch.dict(os.environ, {}, clear=True)
    def test_get_notifier_from_env_neither_set(self):
        """Test returns None when neither env var is set."""
        notifier = get_notifier_from_env()
        assert notifier is None

    @patch.dict(os.environ, {"UPTIME_PING_TELEGRAM_TOKEN": "token"}, clear=True)
    def test_get_notifier_from_env_only_token(self):
        """Test returns None when only token is set."""
        notifier = get_notifier_from_env()
        assert notifier is None

    @patch.dict(os.environ, {"UPTIME_PING_TELEGRAM_CHAT_ID": "chat"}, clear=True)
    def test_get_notifier_from_env_only_chat_id(self):
        """Test returns None when only chat_id is set."""
        notifier = get_notifier_from_env()
        assert notifier is None
