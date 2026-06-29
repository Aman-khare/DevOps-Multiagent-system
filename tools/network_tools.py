"""
Network health check tools for ADK agents.
Provides HTTP endpoint checking and port scanning.
"""

import json
import socket
import httpx


def http_health_check(url: str, timeout: int = 10) -> str:
    """
    Perform an HTTP GET health check against a URL.

    Args:
        url: The full URL to check (e.g., http://localhost:8080/health).
        timeout: Request timeout in seconds (default: 10).

    Returns:
        JSON string with status code, response time, and health assessment.
    """
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)

        elapsed_ms = response.elapsed.total_seconds() * 1000
        is_healthy = 200 <= response.status_code < 400

        return json.dumps({
            "url": url,
            "status_code": response.status_code,
            "response_time_ms": round(elapsed_ms, 2),
            "is_healthy": is_healthy,
            "status": "healthy" if is_healthy else "unhealthy",
            "content_length": len(response.content),
        }, indent=2)

    except httpx.ConnectError:
        return json.dumps({
            "url": url,
            "status": "unreachable",
            "error": "Connection refused — service may be down",
        })
    except httpx.TimeoutException:
        return json.dumps({
            "url": url,
            "status": "timeout",
            "error": f"Request timed out after {timeout}s",
        })
    except Exception as e:
        return json.dumps({
            "url": url,
            "status": "error",
            "error": str(e),
        })


def check_port_open(host: str, port: int, timeout: int = 5) -> str:
    """
    Check if a TCP port is open and accepting connections on a host.

    Args:
        host: The hostname or IP address to check.
        port: The port number to test.
        timeout: Connection timeout in seconds (default: 5).

    Returns:
        JSON string indicating whether the port is open or closed.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()

        is_open = result == 0
        return json.dumps({
            "host": host,
            "port": port,
            "is_open": is_open,
            "status": "open" if is_open else "closed",
        }, indent=2)

    except socket.gaierror:
        return json.dumps({
            "host": host,
            "port": port,
            "status": "error",
            "error": f"Cannot resolve hostname: {host}",
        })
    except Exception as e:
        return json.dumps({
            "host": host,
            "port": port,
            "status": "error",
            "error": str(e),
        })
