"""
System resource monitoring tools for ADK agents.
Provides CPU, memory, and disk usage information.
"""

import json
import psutil
import platform


def get_disk_usage(path: str = "/") -> str:
    """
    Check disk space usage on the specified mount point.

    Args:
        path: The filesystem path to check (default: root).

    Returns:
        JSON string with total, used, free space and usage percentage.
    """
    try:
        # On Windows, default to C: drive
        if platform.system() == "Windows" and path == "/":
            path = "C:\\"

        usage = psutil.disk_usage(path)
        return json.dumps({
            "path": path,
            "total_gb": round(usage.total / (1024 ** 3), 2),
            "used_gb": round(usage.used / (1024 ** 3), 2),
            "free_gb": round(usage.free / (1024 ** 3), 2),
            "percent_used": usage.percent,
            "status": "critical" if usage.percent > 90 else "warning" if usage.percent > 75 else "healthy",
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Disk usage check failed: {str(e)}"})


def get_memory_usage() -> str:
    """
    Check system RAM usage including total, available, used, and percentage.

    Returns:
        JSON string with memory utilization data.
    """
    try:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return json.dumps({
            "ram": {
                "total_gb": round(mem.total / (1024 ** 3), 2),
                "available_gb": round(mem.available / (1024 ** 3), 2),
                "used_gb": round(mem.used / (1024 ** 3), 2),
                "percent_used": mem.percent,
                "status": "critical" if mem.percent > 90 else "warning" if mem.percent > 75 else "healthy",
            },
            "swap": {
                "total_gb": round(swap.total / (1024 ** 3), 2),
                "used_gb": round(swap.used / (1024 ** 3), 2),
                "percent_used": swap.percent,
            },
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Memory check failed: {str(e)}"})


def get_cpu_usage() -> str:
    """
    Check CPU usage including per-core utilization and load averages.

    Returns:
        JSON string with CPU utilization data.
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        overall = psutil.cpu_percent(interval=0)

        result = {
            "overall_percent": overall,
            "core_count": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "per_core_percent": cpu_percent,
            "status": "critical" if overall > 90 else "warning" if overall > 75 else "healthy",
        }

        # Load average is not available on Windows
        if platform.system() != "Windows":
            load1, load5, load15 = psutil.getloadavg()
            result["load_average"] = {
                "1min": round(load1, 2),
                "5min": round(load5, 2),
                "15min": round(load15, 2),
            }

        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"CPU check failed: {str(e)}"})
