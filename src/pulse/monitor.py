"""HTTP monitoring logic for Pulse."""

import time
import urllib.request
import urllib.error
from urllib.parse import urlparse
from typing import Any


def check_endpoint(
    url: str, timeout: int = 10, expected_status: int = 200
) -> dict[str, Any]:
    """Check a single endpoint.
    
    Args:
        url: The URL to check.
        timeout: Request timeout in seconds.
        expected_status: Expected HTTP status code (2xx by default).
    
    Returns:
        dict: Check result with keys: url, status_code, response_time, is_up, error
    """
    start_time = time.time()
    result: dict[str, Any] = {
        "url": url,
        "status_code": None,
        "response_time": 0.0,
        "is_up": False,
        "error": None,
    }
    
    # Validate URL
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            result["error"] = "Invalid URL"
            result["response_time"] = time.time() - start_time
            return result
    except Exception as e:
        result["error"] = f"URL parse error: {e}"
        result["response_time"] = time.time() - start_time
        return result
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PulseMonitor/0.1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            result["status_code"] = response.status
            result["response_time"] = time.time() - start_time
            # Check if status code matches expected
            if result["status_code"] == expected_status:
                result["is_up"] = True
            else:
                result["error"] = f"Unexpected status code: {result['status_code']}"
    except urllib.error.HTTPError as e:
        result["status_code"] = e.code
        result["response_time"] = time.time() - start_time
        result["error"] = f"HTTP error: {e.code}"
    except urllib.error.URLError as e:
        result["response_time"] = time.time() - start_time
        result["error"] = f"URL error: {e.reason}"
    except TimeoutError:
        result["response_time"] = time.time() - start_time
        result["error"] = "Request timed out"
    except Exception as e:
        result["response_time"] = time.time() - start_time
        result["error"] = f"Unexpected error: {e}"
    
    return result
