"""
Tests for agent construction and configuration.
These tests verify that agents are properly configured with the correct
tools, instructions, and sub-agent relationships.
"""

import pytest


def test_diagnostic_agent_has_tools():
    """Diagnostic agent should have log analysis tools."""
    from agents.diagnostic import diagnostic_agent
    assert diagnostic_agent.name == "DiagnosticAgent"
    tool_names = [t.__name__ for t in diagnostic_agent.tools]
    assert "get_container_logs" in tool_names
    assert "list_containers" in tool_names


def test_infrastructure_agent_has_tools():
    """Infrastructure agent should have system inspection tools."""
    from agents.infrastructure import infrastructure_agent
    assert infrastructure_agent.name == "InfrastructureAgent"
    tool_names = [t.__name__ for t in infrastructure_agent.tools]
    assert "get_container_stats" in tool_names
    assert "get_cpu_usage" in tool_names
    assert "get_disk_usage" in tool_names


def test_remediation_agent_has_tools():
    """Remediation agent should have fix execution tools."""
    from agents.remediation import remediation_agent
    assert remediation_agent.name == "RemediationAgent"
    tool_names = [t.__name__ for t in remediation_agent.tools]
    assert "restart_container" in tool_names
    assert "execute_safe_command" in tool_names


def test_verification_agent_has_tools():
    """Verification agent should have health check tools."""
    from agents.verification import verification_agent
    assert verification_agent.name == "VerificationAgent"
    tool_names = [t.__name__ for t in verification_agent.tools]
    assert "http_health_check" in tool_names
    assert "list_containers" in tool_names


def test_coordinator_has_sub_agents():
    """Coordinator should orchestrate all four sub-agents."""
    from agents.coordinator import build_coordinator_agent
    coordinator = build_coordinator_agent()
    assert coordinator.name == "CoordinatorAgent"
    sub_names = [a.name for a in coordinator.sub_agents]
    assert "DiagnosticAgent" in sub_names
    assert "InfrastructureAgent" in sub_names
    assert "RemediationAgent" in sub_names
    assert "VerificationAgent" in sub_names
