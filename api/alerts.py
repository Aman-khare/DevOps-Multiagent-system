"""
Alert ingestion endpoint.
Receives webhook alerts, creates incidents, and triggers the AI agent pipeline.
"""

import os
import traceback
import uuid
from datetime import datetime, UTC

from fastapi import APIRouter, BackgroundTasks, Security, HTTPException, Depends
from fastapi.security import APIKeyHeader
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.coordinator import build_coordinator_agent
from api.websocket import manager
from models.alert import AlertPayload
from models.database import get_db

router = APIRouter(prefix="/api/v1", tags=["alerts"])

webhook_header = APIKeyHeader(name="X-Webhook-Secret", auto_error=False)

async def verify_webhook_secret(api_key_header: str = Security(webhook_header)):
    expected_secret = os.getenv("WEBHOOK_SECRET")
    
    # If no secret is configured, warn but allow (for local testing without breaking existing setups)
    if not expected_secret:
        return True
        
    if api_key_header != expected_secret:
        raise HTTPException(status_code=403, detail="Could not validate webhook secret")
    return True



def _truthy(value: str | None) -> bool:
    return value is not None and value.lower() in {"1", "true", "yes", "on"}


def _has_real_google_key() -> bool:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    return bool(api_key and api_key != "your_google_api_key_here")


def is_agent_pipeline_enabled() -> bool:
    """Return whether incoming alerts should trigger the ADK pipeline."""
    if os.getenv("APP_ENV", "").lower() == "test":
        return False

    configured = os.getenv("AGENT_PIPELINE_ENABLED")
    if configured is not None:
        return _truthy(configured)

    return _has_real_google_key()


async def _run_agent_pipeline(incident_id: str, alert_data: dict):
    """
    Background task: runs the full multi-agent pipeline for an incident.
    Updates the database and broadcasts WebSocket events as agents work.
    """
    db = await get_db()

    try:
        # Mark incident as actively being diagnosed
        await db.update_incident(incident_id, {"status": "diagnosing"})
        await manager.send_incident_update(incident_id, "diagnosing")
        await manager.send_agent_update(
            incident_id, "CoordinatorAgent", "Starting incident analysis", "running"
        )

        # Initialize the ADK Coordinator and the session context
        # We use an InMemorySessionService to maintain conversation state across agent delegations
        coordinator = build_coordinator_agent()
        session_service = InMemorySessionService()
        runner = Runner(
            agent=coordinator,
            app_name="devops_ai_architect",
            session_service=session_service,
        )

        # Create an isolated session for this specific incident run
        session = await session_service.create_session(
            app_name="devops_ai_architect",
            user_id="system",
        )

        # Construct the initial prompt containing all alert context
        # This acts as the entry point for the Coordinator Agent
        alert_prompt = f"""
INCOMING ALERT - Incident ID: {incident_id}

Alert Type: {alert_data.get('alert_type', 'unknown')}
Severity: {alert_data.get('severity', 'warning')}
Service: {alert_data.get('service', 'unknown')}
Container ID: {alert_data.get('container_id', 'N/A')}
Host: {alert_data.get('host', 'N/A')}
Message: {alert_data.get('message', 'No message')}
Metadata: {alert_data.get('metadata', {})}
Timestamp: {alert_data.get('timestamp', datetime.now(UTC).isoformat())}

Please diagnose this issue, apply a fix, and verify the resolution.
Follow your full workflow: Diagnose -> Assess Infrastructure -> Remediate -> Verify.
"""

        agent_trace = []
        final_response = ""

        user_message = types.Content(
            role="user",
            parts=[types.Part(text=alert_prompt)],
        )

        # Execute the agent runner asynchronously.
        # This yields events in real-time as the Coordinator delegates to sub-agents,
        # sub-agents use tools, and results are returned.
        async for event in runner.run_async(
            user_id="system",
            session_id=session.id,
            new_message=user_message,
        ):
            if hasattr(event, "author") and event.author:
                agent_name = event.author

                if hasattr(event, "content") and event.content:
                    for part in event.content.parts:
                        # Handle text responses (reasoning and communication between agents)
                        if hasattr(part, "text") and part.text:
                            trace_entry = {
                                "timestamp": datetime.now(UTC).isoformat(),
                                "agent_name": agent_name,
                                "action": "response",
                                "reasoning": part.text[:500],
                                "status": "success",
                            }
                            agent_trace.append(trace_entry)
                            final_response = part.text

                            # Broadcast the agent's current activity to the UI
                            await manager.send_agent_update(
                                incident_id,
                                agent_name,
                                "Analyzing..." if "Diagnostic" in agent_name
                                else "Inspecting..." if "Infrastructure" in agent_name
                                else "Fixing..." if "Remediation" in agent_name
                                else "Verifying..." if "Verification" in agent_name
                                else "Coordinating...",
                                "running",
                                part.text[:200],
                            )

                        # Handle tool invocations (e.g. running a shell command, fetching logs)
                        if hasattr(part, "function_call") and part.function_call:
                            fc = part.function_call
                            trace_entry = {
                                "timestamp": datetime.now(UTC).isoformat(),
                                "agent_name": agent_name,
                                "action": "tool_call",
                                "tool_name": fc.name,
                                "tool_input": str(fc.args)[:300],
                                "status": "success",
                            }
                            agent_trace.append(trace_entry)

                            # Notify the UI that a specific tool is being executed
                            await manager.send_agent_update(
                                incident_id,
                                agent_name,
                                f"Calling tool: {fc.name}",
                                "running",
                                str(fc.args)[:200],
                            )

                        # Handle tool results returning to the agent
                        if hasattr(part, "function_response") and part.function_response:
                            fr = part.function_response
                            trace_entry = {
                                "timestamp": datetime.now(UTC).isoformat(),
                                "agent_name": agent_name,
                                "action": "tool_response",
                                "tool_name": fr.name if hasattr(fr, "name") else "unknown",
                                "tool_output": str(fr.response)[:500] if hasattr(fr, "response") else "",
                                "status": "success",
                            }
                            agent_trace.append(trace_entry)

        # The pipeline has finished. Determine the final state based on the Coordinator's last message.
        response_lower = final_response.lower()
        if "resolved" in response_lower or "success" in response_lower:
            final_status = "resolved"
        elif "failed" in response_lower or "rollback" in response_lower:
            final_status = "failed"
        else:
            final_status = "resolved"  # Default to resolved if ambiguous but execution completed

        # Save the full execution trace and postmortem to the database
        await db.update_incident(incident_id, {
            "status": final_status,
            "agent_trace": agent_trace,
            "postmortem": final_response,
            "resolution": final_response[:500] if final_response else None,
            "resolved_at": datetime.now(UTC).isoformat() if final_status == "resolved" else None,
        })

        # Broadcast the final incident resolution to the UI
        await manager.send_incident_update(incident_id, final_status, {
            "postmortem": final_response[:300] if final_response else "",
        })
        await manager.send_agent_update(
            incident_id, "CoordinatorAgent", f"Incident {final_status}", "completed"
        )

    except Exception as e:
        # Handle unexpected failures during the agent pipeline execution
        error_msg = f"Agent pipeline error: {str(e)}\n{traceback.format_exc()}"
        await db.update_incident(incident_id, {
            "status": "failed",
            "postmortem": error_msg,
        })
        await manager.send_incident_update(incident_id, "failed", {"error": str(e)})
        await manager.send_agent_update(
            incident_id, "CoordinatorAgent", f"Pipeline failed: {str(e)}", "error"
        )


@router.post("/alerts", summary="Receive an alert webhook", dependencies=[Depends(verify_webhook_secret)])
async def receive_alert(alert: AlertPayload, background_tasks: BackgroundTasks):
    """
    Receive an incoming alert from a monitoring tool or manual simulation.
    Creates a new incident and starts the AI agent pipeline when configured.
    """
    incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"

    db = await get_db()
    alert_dict = alert.model_dump()
    alert_dict["timestamp"] = alert_dict["timestamp"].isoformat()

    incident_data = {
        "id": incident_id,
        "alert_type": alert.alert_type.value,
        "severity": alert.severity.value,
        "service": alert.service,
        "container_id": alert.container_id,
        "host": alert.host,
        "message": alert.message,
        "status": "detected",
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    await db.create_incident(incident_data)

    await manager.send_incident_update(incident_id, "detected", incident_data)

    if is_agent_pipeline_enabled():
        background_tasks.add_task(_run_agent_pipeline, incident_id, alert_dict)
        pipeline_message = "Agent pipeline launched."
    else:
        pipeline_message = "Agent pipeline disabled until GOOGLE_API_KEY is configured or AGENT_PIPELINE_ENABLED=true."

    return {
        "status": "accepted",
        "incident_id": incident_id,
        "pipeline_enabled": is_agent_pipeline_enabled(),
        "message": f"Alert received. Incident {incident_id} created. {pipeline_message}",
    }


@router.post("/alerts/simulate", summary="Simulate a test alert", dependencies=[Depends(verify_webhook_secret)])
async def simulate_alert(background_tasks: BackgroundTasks):
    """
    Simulate a container crash alert for testing the dashboard and API flow.
    """
    test_alert = AlertPayload(
        alert_type="container_crash",
        severity="critical",
        service="test-web-app",
        container_id="test-container-123",
        host="localhost",
        message="Container exited with code 137 (OOMKilled). Restart policy: on-failure. Restart count: 5.",
        source="simulation",
        metadata={"exit_code": 137, "restart_count": 5, "image": "nginx:latest"},
    )
    return await receive_alert(test_alert, background_tasks)