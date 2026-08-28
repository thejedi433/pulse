"""Configuration management for Pulse."""

import os
from pathlib import Path
from typing import TypedDict

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore  # pragma: no cover


class EndpointConfig(TypedDict):
    """Configuration for a single endpoint."""

    url: str
    interval: int
    timeout: int
    expected_status: int


class Config(TypedDict):
    """Full configuration structure."""

    endpoints: list[EndpointConfig]
    check_interval: int
    default_timeout: int


DEFAULT_CONFIG: Config = {
    "endpoints": [],
    "check_interval": 60,
    "default_timeout": 10,
}

CONFIG_DIR = Path.home() / ".config" / "pulse"
CONFIG_FILE = CONFIG_DIR / "config.toml"


def ensure_config_dir() -> None:
    """Ensure the configuration directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Config:
    """Load configuration from TOML file.
    
    Returns:
        Config: The loaded configuration, or defaults if file doesn't exist.
    
    Raises:
        tomllib.TOMLDecodeError: If the config file is malformed.
    """
    ensure_config_dir()
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_FILE, "rb") as f:
            data = tomllib.load(f)
        return Config(
            endpoints=data.get("endpoints", []),
            check_interval=data.get("check_interval", 60),
            default_timeout=data.get("default_timeout", 10),
        )
    except tomllib.TOMLDecodeError as e:
        raise tomllib.TOMLDecodeError(f"Invalid config file: {e}")


def save_config(config: Config) -> None:
    """Save configuration to TOML file.
    
    Args:
        config: The configuration to save.
    """
    ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        f.write("# Pulse Configuration\n")
        f.write(f'check_interval = {config["check_interval"]}\n')
        f.write(f'default_timeout = {config["default_timeout"]}\n\n')
        if config["endpoints"]:
            f.write("[[endpoints]]\n")
            for i, ep in enumerate(config["endpoints"]):
                if i > 0:
                    f.write("\n[[endpoints]]\n")
                f.write(f'url = "{ep["url"]}"\n')
                f.write(f'interval = {ep.get("interval", config["check_interval"])}\n')
                f.write(f'timeout = {ep.get("timeout", config["default_timeout"])}\n')
                f.write(f'expected_status = {ep.get("expected_status", 200)}\n')


def add_endpoint(url: str, interval: int | None = None, timeout: int | None = None, expected_status: int | None = None) -> None:
    """Add an endpoint to the configuration.
    
    Args:
        url: The URL to monitor.
        interval: Check interval in seconds (uses default if None).
        timeout: Request timeout in seconds (uses default if None).
        expected_status: Expected HTTP status code (uses 200 if None).
    """
    config = load_config()
    # Check if endpoint already exists
    for ep in config["endpoints"]:
        if ep["url"] == url:
            return  # Already exists
    
    new_endpoint: EndpointConfig = {
        "url": url,
        "interval": interval or config["check_interval"],
        "timeout": timeout or config["default_timeout"],
        "expected_status": expected_status if expected_status is not None else 200,
    }
    config["endpoints"].append(new_endpoint)
    save_config(config)


def remove_endpoint(url: str) -> bool:
    """Remove an endpoint from the configuration.
    
    Args:
        url: The URL to remove.
    
    Returns:
        bool: True if the endpoint was found and removed, False otherwise.
    """
    config = load_config()
    original_count = len(config["endpoints"])
    config["endpoints"] = [ep for ep in config["endpoints"] if ep["url"] != url]
    if len(config["endpoints"]) < original_count:
        save_config(config)
        return True
    return False


def get_endpoints() -> list[EndpointConfig]:
    """Get all configured endpoints.
    
    Returns:
        list[EndpointConfig]: List of endpoint configurations.
    """
    return load_config()["endpoints"]
