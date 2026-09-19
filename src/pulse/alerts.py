"""Alerting system for Pulse."""

import os
from datetime import datetime
from pathlib import Path

from .notifier import TelegramNotifier


ALERTS_DIR = Path.home() / ".local" / "share" / "pulse"
ALERTS_FILE = ALERTS_DIR / "alerts.log"


def ensure_alerts_dir() -> None:
    """Ensure the alerts directory exists."""
    ALERTS_DIR.mkdir(parents=True, exist_ok=True)


def log_alert(
    url: str,
    old_status: bool | None,
    new_status: bool,
    notifier: TelegramNotifier | None = None,
    response_time: float = 0.0,
    status_code: int | None = None,
) -> str:
    """Log a state change alert.
    
    Args:
        url: The endpoint URL.
        old_status: Previous status (None if first check).
        new_status: Current status.
        notifier: Optional Telegram notifier.
        response_time: Response time in seconds (for Telegram).
        status_code: HTTP status code (for Telegram).
    
    Returns:
        str: The alert message.
    """
    ensure_alerts_dir()
    
    timestamp = datetime.now().isoformat()
    if old_status is None:
        message = f"[{timestamp}] INITIAL: {url} is {'UP' if new_status else 'DOWN'}"
    elif old_status != new_status:
        status_str = "UP" if new_status else "DOWN"
        prev_str = "UP" if old_status else "DOWN"
        message = f"[{timestamp}] STATE CHANGE: {url} went from {prev_str} to {status_str}"
    else:
        message = ""  # No state change, no alert needed
    
    if message:
        with open(ALERTS_FILE, "a") as f:
            f.write(message + "\n")
        print(message)
        
        # Send Telegram notification if notifier is available
        if notifier and notifier.is_configured:
            notifier.send_notification(message)
    
    return message


def format_status_message(url: str, is_up: bool, response_time: float, status_code: int | None) -> str:
    """Format a status message for display.
    
    Args:
        url: The endpoint URL.
        is_up: Whether the endpoint is up.
        response_time: Response time in seconds.
        status_code: HTTP status code.
    
    Returns:
        str: Formatted status message.
    """
    status_icon = "✓" if is_up else "✗"
    status_text = "UP" if is_up else "DOWN"
    code_str = str(status_code) if status_code else "N/A"
    time_ms = int(response_time * 1000)
    return f"{status_icon} {url}: {status_text} (status={code_str}, time={time_ms}ms)"
