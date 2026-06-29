"""
WebSocket manager for broadcasting real-time agent activity to the dashboard.
"""

import json
from datetime import datetime, UTC
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts messages."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a disconnected WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        # Clean up dead connections
        for conn in dead_connections:
            self.disconnect(conn)

    async def send_agent_update(
        self,
        incident_id: str,
        agent_name: str,
        action: str,
        status: str = "running",
        details: str = "",
    ):
        """Broadcast an agent activity update to all connected dashboards."""
        await self.broadcast({
            "type": "agent_update",
            "incident_id": incident_id,
            "agent_name": agent_name,
            "action": action,
            "status": status,
            "details": details,
            "timestamp": datetime.now(UTC).isoformat(),
        })

    async def send_incident_update(self, incident_id: str, incident_status: str, data: dict = None):
        """Broadcast an incident status change."""
        await self.broadcast({
            "type": "incident_update",
            "incident_id": incident_id,
            "status": incident_status,
            "data": data or {},
            "timestamp": datetime.now(UTC).isoformat(),
        })


# Global connection manager singleton
manager = ConnectionManager()


@router.websocket("/ws/incidents")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, listen for client messages (heartbeat)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
