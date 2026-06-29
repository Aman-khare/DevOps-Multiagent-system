"""
Tests for the ADK tool functions.
"""

import json
import os
import pytest

from tools.command_runner import execute_safe_command, _is_command_safe
from tools.system_tools import get_disk_usage, get_memory_usage, get_cpu_usage
from tools.network_tools import http_health_check, check_port_open


class TestCommandRunner:
    """Tests for the sandboxed command executor."""

    def test_blocklist_rm_rf(self):
        """Dangerous rm -rf / should be blocked."""
        is_safe, reason = _is_command_safe("rm -rf /")
        assert not is_safe

    def test_blocklist_drop_database(self):
        """DROP DATABASE should be blocked."""
        is_safe, reason = _is_command_safe("psql -c 'DROP DATABASE production'")
        assert not is_safe

    def test_blocklist_shutdown(self):
        """shutdown command should be blocked."""
        is_safe, reason = _is_command_safe("shutdown -h now")
        assert not is_safe

    def test_blocklist_fork_bomb(self):
        """Fork bomb should be blocked."""
        is_safe, reason = _is_command_safe(":(){ :|:& };:")
        assert not is_safe

    def test_safe_command_allowed(self):
        """Safe commands should pass validation."""
        is_safe, reason = _is_command_safe("docker ps -a")
        assert is_safe

    def test_safe_command_docker_logs(self):
        """docker logs should be safe."""
        is_safe, reason = _is_command_safe("docker logs --tail 100 my-container")
        assert is_safe

    def test_dry_run_mode(self):
        """Commands should return dry_run status when DRY_RUN=true."""
        os.environ["DRY_RUN"] = "true"
        result = json.loads(execute_safe_command("echo hello"))
        assert result["status"] == "dry_run"

    def test_blocked_command_execution(self):
        """Blocked commands should never execute, even with DRY_RUN=false."""
        os.environ["DRY_RUN"] = "false"
        result = json.loads(execute_safe_command("rm -rf /"))
        assert result["status"] == "blocked"
        os.environ["DRY_RUN"] = "true"  # Reset


class TestSystemTools:
    """Tests for system resource monitoring tools."""

    def test_disk_usage_returns_json(self):
        result = json.loads(get_disk_usage())
        assert "total_gb" in result
        assert "percent_used" in result
        assert "status" in result

    def test_memory_usage_returns_json(self):
        result = json.loads(get_memory_usage())
        assert "ram" in result
        assert "total_gb" in result["ram"]
        assert "status" in result["ram"]

    def test_cpu_usage_returns_json(self):
        result = json.loads(get_cpu_usage())
        assert "overall_percent" in result
        assert "core_count" in result
        assert "status" in result


class TestNetworkTools:
    """Tests for network health check tools."""

    def test_health_check_invalid_url(self):
        """Health check against invalid URL should return error."""
        result = json.loads(http_health_check("http://localhost:99999"))
        assert result["status"] in ("unreachable", "error")

    def test_check_port_closed(self):
        """Checking a likely-closed port should return closed."""
        result = json.loads(check_port_open("localhost", 59999, timeout=2))
        assert result["is_open"] is False

    def test_check_port_invalid_host(self):
        """Checking an invalid hostname should return error."""
        result = json.loads(check_port_open("this-host-does-not-exist.invalid", 80, timeout=2))
        assert result["status"] == "error"
