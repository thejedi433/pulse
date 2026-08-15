"""Tests for Pulse monitor module."""

import urllib.error
from unittest.mock import Mock, patch

import pytest

from pulse.monitor import check_endpoint


def test_check_endpoint_success():
    """Test successful endpoint check."""
    with patch('pulse.monitor.urllib.request.urlopen') as mock_urlopen:
        mock_response = Mock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response
        
        result = check_endpoint("https://example.com", timeout=10)
        
        assert result["url"] == "https://example.com"
        assert result["status_code"] == 200
        assert result["is_up"] is True
        assert result["error"] is None
        assert result["response_time"] > 0


def test_check_endpoint_201_status():
    """Test successful check with 201 status."""
    with patch('pulse.monitor.urllib.request.urlopen') as mock_urlopen:
        mock_response = Mock()
        mock_response.status = 201
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response
        
        result = check_endpoint("https://example.com/create", timeout=10)
        
        assert result["status_code"] == 201
        assert result["is_up"] is True


def test_check_endpoint_404_not_found():
    """Test check with 404 status."""
    with patch('pulse.monitor.urllib.request.urlopen') as mock_urlopen:
        mock_error = urllib.error.HTTPError(
            url="https://example.com",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )
        mock_urlopen.side_effect = mock_error
        
        result = check_endpoint("https://example.com/missing", timeout=10)
        
        assert result["status_code"] == 404
        assert result["is_up"] is False
        assert "404" in result["error"]


def test_check_endpoint_500_server_error():
    """Test check with 500 status."""
    with patch('pulse.monitor.urllib.request.urlopen') as mock_urlopen:
        mock_error = urllib.error.HTTPError(
            url="https://example.com",
            code=500,
            msg="Internal Server Error",
            hdrs={},
            fp=None,
        )
        mock_urlopen.side_effect = mock_error
        
        result = check_endpoint("https://example.com/error", timeout=10)
        
        assert result["status_code"] == 500
        assert result["is_up"] is False


def test_check_endpoint_timeout():
    """Test check with timeout."""
    with patch('pulse.monitor.urllib.request.urlopen') as mock_urlopen:
        mock_urlopen.side_effect = TimeoutError("Request timed out")
        
        result = check_endpoint("https://slow.example.com", timeout=1)
        
        assert result["status_code"] is None
        assert result["is_up"] is False
        assert "timed out" in result["error"].lower()


def test_check_endpoint_connection_refused():
    """Test check with connection refused."""
    with patch('pulse.monitor.urllib.request.urlopen') as mock_urlopen:
        mock_error = urllib.error.URLError("Connection refused")
        mock_urlopen.side_effect = mock_error
        
        result = check_endpoint("https://localhost:9999", timeout=1)
        
        assert result["status_code"] is None
        assert result["is_up"] is False
        assert "Connection refused" in result["error"]


def test_check_endpoint_invalid_url_no_scheme():
    """Test check with invalid URL (no scheme)."""
    result = check_endpoint("example.com", timeout=1)
    
    assert result["status_code"] is None
    assert result["is_up"] is False
    assert result["error"] == "Invalid URL"


def test_check_endpoint_invalid_url_empty():
    """Test check with empty URL."""
    result = check_endpoint("", timeout=1)
    
    assert result["status_code"] is None
    assert result["is_up"] is False


def test_check_endpoint_dns_failure():
    """Test check with DNS failure."""
    with patch('pulse.monitor.urllib.request.urlopen') as mock_urlopen:
        mock_error = urllib.error.URLError("Name or service not known")
        mock_urlopen.side_effect = mock_error
        
        result = check_endpoint("https://nonexistent.invalid.domain", timeout=1)
        
        assert result["status_code"] is None
        assert result["is_up"] is False
        assert "Name or service not known" in result["error"]


def test_check_endpoint_response_time():
    """Test that response time is recorded."""
    with patch('pulse.monitor.urllib.request.urlopen') as mock_urlopen:
        mock_response = Mock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response
        
        result = check_endpoint("https://example.com", timeout=10)
        
        # Response time should be positive and small
        assert result["response_time"] > 0
        assert result["response_time"] < 1  # Should be very fast with mock
