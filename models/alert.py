"""
Alert payload schemas for incoming webhook data.
Supports both custom JSON alerts and Prometheus AlertManager format.
"""

from enum import Enum
from typing import Optional
from datetime import datetime, UTC
from pydantic import BaseModel, ConfigDict, Field


class AlertType(str, Enum):
    """Categories of DevOps alerts the system can handle."""
    CONTAINER_CRASH = "container_crash"
    CONTAINER_OOM = "container_oom"
    IMAGE_PULL_FAILURE = "image_pull_failure"
    PORT_CONFLICT = "port_conflict"
    DISK_FULL = "disk_full"
    HIGH_CPU = "high_cpu"
    HIGH_MEMORY = "high_memory"
    SERVICE_DOWN = "service_down"
    NETWORK_ERROR = "network_error"
    DEPLOYMENT_FAILURE = "deployment_failure"
    CUSTOM = "custom"


class Severity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertPayload(BaseModel):
    """
    Schema for incoming alert payloads.
    Accepts custom JSON format or Prometheus AlertManager webhooks.
    """
    alert_type: AlertType = Field(
        default=AlertType.CUSTOM,
        description="The category of the alert"
    )
    severity: Severity = Field(
        default=Severity.WARNING,
        description="Severity level of the alert"
    )
    service: str = Field(
        default="unknown",
        description="Name of the affected service"
    )
    container_id: Optional[str] = Field(
        default=None,
        description="Docker container ID if applicable"
    )
    host: Optional[str] = Field(
        default=None,
        description="Hostname or IP of the affected machine"
    )
    message: str = Field(
        ...,
        description="Human-readable error message or description"
    )
    source: str = Field(
        default="manual",
        description="Source of the alert (prometheus, datadog, manual, etc.)"
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Additional key-value metadata from the alert"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the alert was generated"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "alert_type": "container_crash",
                "severity": "critical",
                "service": "web-app",
                "container_id": "abc123def456",
                "host": "prod-server-01",
                "message": "Container exited with OOMKilled status",
                "source": "manual",
                "metadata": {"exit_code": 137, "restart_count": 5},
            }
        }
    )
