"""
Incident lifecycle models.
Tracks the full journey of an alert from detection through resolution.
"""

from enum import Enum
from typing import Optional
from datetime import datetime, UTC
from pydantic import BaseModel, Field


class IncidentStatus(str, Enum):
    """Lifecycle states of an incident."""
    DETECTED = "detected"
    DIAGNOSING = "diagnosing"
    REMEDIATING = "remediating"
    VERIFYING = "verifying"
    RESOLVED = "resolved"
    FAILED = "failed"
    ROLLBACK = "rollback"


class AgentTraceEntry(BaseModel):
    """A single step in the agent's chain-of-thought trace."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent_name: str = Field(..., description="Name of the agent that performed this step")
    action: str = Field(..., description="What the agent did (e.g., 'called tool', 'reasoning')")
    tool_name: Optional[str] = Field(default=None, description="Tool that was invoked, if any")
    tool_input: Optional[str] = Field(default=None, description="Input passed to the tool")
    tool_output: Optional[str] = Field(default=None, description="Output returned by the tool")
    reasoning: Optional[str] = Field(default=None, description="Agent's reasoning or thought process")
    status: str = Field(default="success", description="success or error")


class Incident(BaseModel):
    """Full incident record from detection to resolution."""
    id: str = Field(..., description="Unique incident ID")
    alert_type: str = Field(..., description="Category of the triggering alert")
    severity: str = Field(default="warning", description="Severity level")
    service: str = Field(default="unknown", description="Affected service name")
    container_id: Optional[str] = Field(default=None)
    host: Optional[str] = Field(default=None)
    message: str = Field(..., description="Original alert message")
    status: IncidentStatus = Field(default=IncidentStatus.DETECTED)
    agent_trace: list[AgentTraceEntry] = Field(default_factory=list)
    root_cause: Optional[str] = Field(default=None, description="Identified root cause")
    resolution: Optional[str] = Field(default=None, description="How the issue was fixed")
    postmortem: Optional[str] = Field(default=None, description="Auto-generated post-mortem markdown")
    commands_executed: list[str] = Field(default_factory=list, description="All commands run during remediation")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = Field(default=None)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def add_trace(
        self,
        agent_name: str,
        action: str,
        tool_name: str | None = None,
        tool_input: str | None = None,
        tool_output: str | None = None,
        reasoning: str | None = None,
        status: str = "success",
    ) -> AgentTraceEntry:
        """Add a new trace entry to the incident timeline."""
        entry = AgentTraceEntry(
            agent_name=agent_name,
            action=action,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            reasoning=reasoning,
            status=status,
        )
        self.agent_trace.append(entry)
        self.updated_at = datetime.now(UTC)
        return entry
