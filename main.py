"""
DevOps AI Architect - FastAPI application entrypoint.
Serves the API, WebSocket, and frontend dashboard.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.alerts import router as alerts_router
from api.incidents import router as incidents_router
from api.websocket import router as ws_router
from models.database import get_db, reset_db

BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")


def _cors_origins() -> list[str]:
    origins = os.getenv("CORS_ORIGINS", "*")
    return [origin.strip() for origin in origins.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle events."""
    db = await get_db()
    print("[OK] Database initialized")
    print(f"[CONFIG] DRY_RUN mode: {os.getenv('DRY_RUN', 'true')}")
    print(f"[CONFIG] Agent pipeline enabled: {os.getenv('AGENT_PIPELINE_ENABLED', 'auto')}")
    print(f"[CONFIG] Google API key configured: {'yes' if os.getenv('GOOGLE_API_KEY') else 'no'}")
    print("[START] DevOps AI Architect is running at http://localhost:8000")
    yield
    await db.close()
    await reset_db()
    print("[STOP] Database closed. Goodbye!")


app = FastAPI(
    title="DevOps AI Architect",
    description="Autonomous multi-agent AI system for DevOps incident diagnosis and remediation.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(alerts_router)
app.include_router(incidents_router)
app.include_router(ws_router)


@app.get("/health", summary="Health check")
async def health_check():
    """Simple readiness check for local, Docker, and load balancer probes."""
    await get_db()
    return {"status": "ok", "service": "devops-ai-architect"}


@app.get("/", summary="Dashboard")
async def dashboard(request: Request):
    """Main dashboard page showing live incidents and agent activity."""
    db = await get_db()
    incidents = await db.list_incidents(limit=20)
    return templates.TemplateResponse(request, "dashboard.html", {
        "incidents": incidents,
        "active_count": sum(1 for i in incidents if i["status"] not in ("resolved", "failed")),
        "resolved_count": sum(1 for i in incidents if i["status"] == "resolved"),
        "failed_count": sum(1 for i in incidents if i["status"] == "failed"),
    })


@app.get("/incident/{incident_id}", summary="Incident Detail")
async def incident_detail(request: Request, incident_id: str):
    """Detailed view of a single incident with agent trace timeline."""
    db = await get_db()
    incident = await db.get_incident(incident_id)
    if not incident:
        return templates.TemplateResponse(request, "dashboard.html", {
            "incidents": [],
            "active_count": 0,
            "resolved_count": 0,
            "failed_count": 0,
            "error": f"Incident {incident_id} not found",
        })

    audit_logs = await db.get_audit_logs(incident_id)
    return templates.TemplateResponse(request, "incident_detail.html", {
        "incident": incident,
        "audit_logs": audit_logs,
    })


@app.get("/postmortem/{incident_id}", summary="Post-Mortem Report")
async def postmortem(request: Request, incident_id: str):
    """Auto-generated post-mortem report for a resolved incident."""
    db = await get_db()
    incident = await db.get_incident(incident_id)
    if not incident:
        return templates.TemplateResponse(request, "dashboard.html", {
            "incidents": [],
            "active_count": 0,
            "resolved_count": 0,
            "failed_count": 0,
            "error": f"Incident {incident_id} not found",
        })

    return templates.TemplateResponse(request, "postmortem.html", {
        "incident": incident,
    })