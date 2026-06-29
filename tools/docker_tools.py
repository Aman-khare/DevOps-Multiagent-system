"""
Docker CLI wrapper tools for ADK agents.
Each function is a tool that agents can invoke to interact with Docker.
"""

import subprocess
import json
import os


def list_containers(show_all: bool = True) -> str:
    """
    List all Docker containers with their status, names, and IDs.

    Args:
        show_all: If True, show all containers including stopped ones.

    Returns:
        JSON string with container information or error message.
    """
    try:
        cmd = ["docker", "ps", "--format", "{{json .}}"]
        if show_all:
            cmd.insert(2, "-a")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return json.dumps({"error": f"Docker command failed: {result.stderr.strip()}"})

        containers = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    containers.append(json.loads(line))
                except json.JSONDecodeError:
                    containers.append({"raw": line})

        return json.dumps({
            "container_count": len(containers),
            "containers": containers,
        }, indent=2)

    except FileNotFoundError:
        return json.dumps({"error": "Docker is not installed or not in PATH"})
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Docker command timed out after 30s"})
    except Exception as e:
        return json.dumps({"error": f"Unexpected error: {str(e)}"})


def get_container_logs(container_id: str, tail: int = 100) -> str:
    """
    Retrieve the last N lines of logs from a specific Docker container.

    Args:
        container_id: The container ID or name to get logs from.
        tail: Number of log lines to retrieve (default: 100).

    Returns:
        Container log output as a string, or error message.
    """
    try:
        result = subprocess.run(
            ["docker", "logs", "--tail", str(tail), container_id],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return json.dumps({"error": f"Failed to get logs: {result.stderr.strip()}"})

        # Combine stdout and stderr (Docker often writes to stderr)
        logs = result.stdout + result.stderr
        return json.dumps({
            "container_id": container_id,
            "lines_requested": tail,
            "logs": logs.strip(),
        }, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to retrieve logs: {str(e)}"})


def restart_container(container_id: str) -> str:
    """
    Restart a Docker container by its ID or name.

    Args:
        container_id: The container ID or name to restart.

    Returns:
        Success or error message.
    """
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"

    if dry_run:
        return json.dumps({
            "status": "dry_run",
            "message": f"[DRY RUN] Would restart container: {container_id}",
            "command": f"docker restart {container_id}",
        })

    try:
        result = subprocess.run(
            ["docker", "restart", container_id],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            return json.dumps({"error": f"Failed to restart: {result.stderr.strip()}"})

        return json.dumps({
            "status": "success",
            "message": f"Container {container_id} restarted successfully",
            "output": result.stdout.strip(),
        })

    except Exception as e:
        return json.dumps({"error": f"Restart failed: {str(e)}"})


def get_container_stats() -> str:
    """
    Get resource usage stats for all running Docker containers.
    Shows CPU %, memory usage, network I/O, and block I/O.

    Returns:
        JSON string with container resource statistics.
    """
    try:
        result = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return json.dumps({"error": f"Stats failed: {result.stderr.strip()}"})

        stats = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    stats.append(json.loads(line))
                except json.JSONDecodeError:
                    stats.append({"raw": line})

        return json.dumps({"stats": stats}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to get stats: {str(e)}"})


def prune_docker_system() -> str:
    """
    Remove all stopped containers, unused networks, dangling images,
    and build cache to free up disk space.

    Returns:
        Prune results showing space reclaimed, or error message.
    """
    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"

    if dry_run:
        return json.dumps({
            "status": "dry_run",
            "message": "[DRY RUN] Would run: docker system prune -f",
        })

    try:
        result = subprocess.run(
            ["docker", "system", "prune", "-f"],
            capture_output=True, text=True, timeout=120,
        )
        return json.dumps({
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout.strip(),
            "errors": result.stderr.strip() if result.stderr else None,
        })

    except Exception as e:
        return json.dumps({"error": f"Prune failed: {str(e)}"})


def get_docker_images() -> str:
    """
    List all Docker images on the host with their sizes.

    Returns:
        JSON string with image information.
    """
    try:
        result = subprocess.run(
            ["docker", "images", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return json.dumps({"error": f"Failed: {result.stderr.strip()}"})

        images = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                try:
                    images.append(json.loads(line))
                except json.JSONDecodeError:
                    images.append({"raw": line})

        return json.dumps({"image_count": len(images), "images": images}, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Failed to list images: {str(e)}"})
