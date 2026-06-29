"""
Tests for the alert ingestion API endpoint.
"""

import pytest
from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def test_receive_alert_success():
    """Test that a valid alert is accepted and creates an incident."""
    response = client.post("/api/v1/alerts", json={
        "alert_type": "container_crash",
        "severity": "critical",
        "service": "web-app",
        "container_id": "test-container-123",
        "message": "Container exited with OOMKilled status",
        "source": "test",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert "incident_id" in data
    assert data["incident_id"].startswith("INC-")


def test_receive_alert_minimal():
    """Test that a minimal alert (only message) is accepted."""
    response = client.post("/api/v1/alerts", json={
        "message": "Something went wrong",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"


def test_receive_alert_missing_message():
    """Test that an alert without a message is rejected."""
    response = client.post("/api/v1/alerts", json={
        "alert_type": "container_crash",
        "severity": "critical",
    })
    assert response.status_code == 422  # Validation error


def test_simulate_alert():
    """Test the simulation endpoint creates a test incident."""
    response = client.post("/api/v1/alerts/simulate")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert "incident_id" in data


def test_list_incidents():
    """Test listing incidents after creating one."""
    # Create an incident first
    client.post("/api/v1/alerts", json={
        "message": "Test incident for listing",
        "severity": "info",
    })

    response = client.get("/api/v1/incidents")
    assert response.status_code == 200
    data = response.json()
    assert "incidents" in data
    assert "total" in data


def test_get_incident_not_found():
    """Test that requesting a non-existent incident returns 404."""
    response = client.get("/api/v1/incidents/NONEXISTENT-ID")
    assert response.status_code == 404


def test_dashboard_page():
    """Test that the dashboard HTML page loads."""
    response = client.get("/")
    assert response.status_code == 200
    assert "DevOps AI Architect" in response.text
