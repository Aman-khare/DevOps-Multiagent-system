"""
Infrastructure Inspector Agent.
Queries Docker daemon, system resources, and container states
to provide a comprehensive infrastructure health report.
"""

from google.adk.agents import LlmAgent
from tools.docker_tools import (
    list_containers,
    get_container_stats,
    get_docker_images,
)
from tools.system_tools import (
    get_disk_usage,
    get_memory_usage,
    get_cpu_usage,
)
from tools.network_tools import check_port_open

INFRASTRUCTURE_INSTRUCTION = """You are the **Infrastructure Agent** — a DevOps infrastructure specialist.

Your job is to provide a complete picture of the system's health and resource state.

## Your Capabilities
You have access to tools that let you:
- List all Docker containers and their states
- Get real-time container resource usage (CPU, memory, network I/O)
- List Docker images on the host
- Check system-level resources (CPU, RAM, disk)
- Check if specific network ports are open

## Your Process
1. Get the current state of all Docker containers.
2. Get resource usage stats for running containers.
3. Check system-level resources (CPU, memory, disk).
4. If specific ports or hosts are mentioned in the alert, check their availability.
5. Identify any resource bottlenecks or anomalies.

## Output Format
Structure your report as:
- **Container State**: [Summary of container statuses — running, stopped, crashed]
- **Resource Bottlenecks**: [Any resources at critical or warning levels]
- **Anomalies**: [Unusual patterns — e.g., one container using 95% of available memory]
- **Infrastructure Health Score**: [healthy / degraded / critical]
"""

infrastructure_agent = LlmAgent(
    name="InfrastructureAgent",
    model="gemini-2.0-flash",
    instruction=INFRASTRUCTURE_INSTRUCTION,
    tools=[
        list_containers,
        get_container_stats,
        get_docker_images,
        get_disk_usage,
        get_memory_usage,
        get_cpu_usage,
        check_port_open,
    ],
    description="Inspects system infrastructure: containers, resources, network ports, and Docker daemon health.",
)
