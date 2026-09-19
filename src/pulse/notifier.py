"""Telegram notifications for Pulse."""

import os
import requests
from typing import Optional


class TelegramNotifier:
    """Send alerts via Telegram when endpoints change state."""

    API_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self, token: str, chat_id: str):
        """Initialize Telegram notifier.

        Args:
            token: Telegram bot token
            chat_id: Telegram chat ID to send messages to
        """
        self.token = token
        self.chat_id = chat_id

    @property
    def is_configured(self) -> bool:
        """Check if this notifier is properly configured."""
        return bool(self.token and self.chat_id)
    
    def send_notification(self, message: str) -> bool:
        """Send a notification via Telegram (alias for send)."""
        return self.send(message)
    
    def send(self, message: str) -> bool:
        """Send a message via Telegram.

        Args:
            message: Text message to send

        Returns:
            bool: True if sent successfully, False otherwise
        """
        url = self.API_URL.format(token=self.token)
        payload = {"chat_id": self.chat_id, "text": message}

        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("ok", False)
        except requests.exceptions.RequestException:
            return False


def get_notifier_from_env() -> Optional[TelegramNotifier]:
    """Create a TelegramNotifier from environment variables if configured.

    Returns:
        TelegramNotifier if UPTIME_PING_TELEGRAM_TOKEN and
        UPTIME_PING_TELEGRAM_CHAT_ID are set, None otherwise
    """
    token = os.environ.get("UPTIME_PING_TELEGRAM_TOKEN")
    chat_id = os.environ.get("UPTIME_PING_TELEGRAM_CHAT_ID")

    if token and chat_id:
        return TelegramNotifier(token, chat_id)
    return None
