"""
Incident history and detail endpoints.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException

from models.database import get_db

router = APIRouter(prefix="/api/v1", tags=["incidents"])


@router.get("/incidents", summary="List all incidents")
async def list_incidents(limit: int = 50, status: Optional[str] = None):
    """
    List all incidents, optionally filtered by status.
    Returns incidents ordered by creation time (newest first).
    """
    db = await get_db()
    incidents = await db.list_incidents(limit=limit, status=status)
    return {
        "total": len(incidents),
        "incidents": incidents,
    }


@router.get("/incidents/{incident_id}", summary="Get incident details")
async def get_incident(incident_id: str):
    """
    Get full details for a specific incident, including the agent trace log,
    audit trail, and post-mortem report.
    """
    db = await get_db()
    incident = await db.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    # Also fetch audit logs for this incident
    audit_logs = await db.get_audit_logs(incident_id)

    return {
        "incident": incident,
        "audit_logs": audit_logs,
    }
