"""Tests for Pulse configuration module."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pulse.config import (
    add_endpoint,
    remove_endpoint,
    get_endpoints,
    load_config,
    save_config,
    Config,
    EndpointConfig,
    DEFAULT_CONFIG,
)


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory."""
    with patch.object(Path, 'home', return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clean_config(temp_config_dir):
    """Ensure clean config state for each test."""
    from pulse import config
    config.CONFIG_FILE = temp_config_dir / ".config" / "pulse" / "config.toml"
    config.CONFIG_DIR = temp_config_dir / ".config" / "pulse"
    yield


def test_load_config_default(clean_config):
    """Test loading default config when file doesn't exist."""
    config = load_config()
    assert config["endpoints"] == []
    assert config["check_interval"] == 60
    assert config["default_timeout"] == 10


def test_add_endpoint(clean_config):
    """Test adding an endpoint."""
    add_endpoint("https://example.com", interval=120, timeout=15)
    endpoints = get_endpoints()
    
    assert len(endpoints) == 1
    assert endpoints[0]["url"] == "https://example.com"
    assert endpoints[0]["interval"] == 120
    assert endpoints[0]["timeout"] == 15


def test_add_endpoint_duplicate(clean_config):
    """Test that duplicate endpoints are not added."""
    add_endpoint("https://example.com")
    add_endpoint("https://example.com")
    endpoints = get_endpoints()
    
    assert len(endpoints) == 1


def test_remove_endpoint(clean_config):
    """Test removing an endpoint."""
    add_endpoint("https://example.com")
    add_endpoint("https://google.com")
    
    result = remove_endpoint("https://example.com")
    assert result is True
    
    endpoints = get_endpoints()
    assert len(endpoints) == 1
    assert endpoints[0]["url"] == "https://google.com"


def test_remove_endpoint_not_found(clean_config):
    """Test removing a non-existent endpoint."""
    result = remove_endpoint("https://nonexistent.com")
    assert result is False


def test_save_and_load_config(clean_config):
    """Test saving and loading a custom config."""
    config: Config = {
        "endpoints": [
            {
                "url": "https://test.com",
                "interval": 30,
                "timeout": 5,
                "expected_status": 200,
            }
        ],
        "check_interval": 45,
        "default_timeout": 8,
    }
    save_config(config)
    
    loaded = load_config()
    assert loaded["check_interval"] == 45
    assert loaded["default_timeout"] == 8
    assert len(loaded["endpoints"]) == 1
    assert loaded["endpoints"][0]["url"] == "https://test.com"
    assert loaded["endpoints"][0]["interval"] == 30


def test_load_config_invalid_toml(clean_config):
    """Test loading config with invalid TOML raises error."""
    from pulse import config
    
    # Create an invalid TOML file - unterminated string
    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.CONFIG_FILE, "w") as f:
        f.write('key = "unterminated string\n')
    
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore
    with pytest.raises(tomllib.TOMLDecodeError):
        load_config()
