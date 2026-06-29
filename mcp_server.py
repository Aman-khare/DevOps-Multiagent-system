"""
MCP Server for DevOps AI Architect tools.

Exposes Docker, Network, and System diagnostic tools via the Model Context Protocol,
allowing any MCP-compatible agent (e.g., Claude Desktop, Cursor) to manage
infrastructure through a standardised interface.

Run:
    mcp run mcp_server.py          (stdio mode)
    mcp dev mcp_server.py          (dev inspector)
"""

from mcp.server.fastmcp import FastMCP
import tools.docker_tools as docker_tools
import tools.system_tools as system_tools
import tools.network_tools as network_tools
import tools.command_runner as command_runner

# ---------------------------------------------------------------------------
# MCP server instance
# ---------------------------------------------------------------------------
mcp = FastMCP("DevOps AI Architect")

# ---------------------------------------------------------------------------
# Docker Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def list_containers(show_all: bool = True) -> str:
    """List all Docker containers with their status, names, and IDs."""
    return docker_tools.list_containers(show_all)


@mcp.tool()
def get_container_logs(container_id: str, tail: int = 100) -> str:
    """Retrieve the last N lines of logs from a specific Docker container."""
    return docker_tools.get_container_logs(container_id, tail)


@mcp.tool()
def restart_container(container_id: str) -> str:
    """Restart a Docker container by its ID or name. Respects DRY_RUN mode."""
    return docker_tools.restart_container(container_id)


@mcp.tool()
def get_container_stats() -> str:
    """Get resource usage stats (CPU, memory, network I/O) for all running containers."""
    return docker_tools.get_container_stats()


@mcp.tool()
def prune_docker_system() -> str:
    """Remove stopped containers, unused networks, dangling images, and build cache."""
    return docker_tools.prune_docker_system()


@mcp.tool()
def get_docker_images() -> str:
    """List all Docker images on the host with their sizes."""
    return docker_tools.get_docker_images()


# ---------------------------------------------------------------------------
# System Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def get_disk_usage(path: str = "/") -> str:
    """Check disk space usage for a specific path. Defaults to root (or C:\\ on Windows)."""
    return system_tools.get_disk_usage(path)


@mcp.tool()
def get_memory_usage() -> str:
    """Check system RAM and swap usage with health status thresholds."""
    return system_tools.get_memory_usage()


@mcp.tool()
def get_cpu_usage() -> str:
    """Check system CPU usage including per-core utilisation."""
    return system_tools.get_cpu_usage()


@mcp.tool()
def execute_safe_command(command: str, timeout: int = 30) -> str:
    """Execute a shell command after validating it against a safety blocklist. Respects DRY_RUN mode."""
    return command_runner.execute_safe_command(command, timeout)


# ---------------------------------------------------------------------------
# Network Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def http_health_check(url: str, timeout: int = 10) -> str:
    """Perform an HTTP GET health check against a URL and return status code + response time."""
    return network_tools.http_health_check(url, timeout)


@mcp.tool()
def check_port_open(host: str, port: int, timeout: int = 5) -> str:
    """Check if a specific TCP port is open on a host."""
    return network_tools.check_port_open(host, port, timeout)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()
