"""
Sandboxed shell command executor with blocklist safety.
All commands are validated against dangerous patterns before execution,
and every execution is kept in an in-memory audit history.
"""

import json
import os
import re
import subprocess
from datetime import datetime, UTC


COMMAND_BLOCKLIST = [
    r"\brm\s+-[A-Za-z]*r[A-Za-z]*f[A-Za-z]*\s+/(?:\s|$|\*)",
    r"\brm\s+-[A-Za-z]*f[A-Za-z]*r[A-Za-z]*\s+/(?:\s|$|\*)",
    r"\brm\s+-[A-Za-z]*r[A-Za-z]*f[A-Za-z]*\s+~(?:\s|$|/)",
    r"\brm\s+-[A-Za-z]*f[A-Za-z]*r[A-Za-z]*\s+~(?:\s|$|/)",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r"\bDROP\s+DATABASE\b",
    r"\bDROP\s+TABLE\b",
    r"\bDELETE\s+FROM\b(?!.*\bWHERE\b)",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\binit\s+0\b",
    r"\bsystemctl\s+stop\b",
    r"\bkill\s+-9\s+1\b",
    r":\s*\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;?\s*:",
    r"\bchmod\s+-R\s+777\s+/(?:\s|$)",
    r"\bchown\s+-R\b.*\s+/(?:\s|$)",
    r"\bcurl\b.*\|\s*(?:sudo\s+)?(?:bash|sh)\b",
    r"\bwget\b.*\|\s*(?:sudo\s+)?(?:bash|sh)\b",
]

_COMPILED_BLOCKLIST = [re.compile(pattern, re.IGNORECASE) for pattern in COMMAND_BLOCKLIST]
_execution_history: list[dict] = []


def _is_command_safe(command: str) -> tuple[bool, str]:
    """Check a command against the blocklist. Returns (is_safe, reason)."""
    normalized = " ".join(command.strip().split())
    for pattern in _COMPILED_BLOCKLIST:
        if pattern.search(normalized):
            return False, f"Blocked by safety rule: {pattern.pattern}"
    return True, "Command passed safety check"


def execute_safe_command(command: str, timeout: int = 30) -> str:
    """
    Execute a shell command after validating it against the safety blocklist.
    Respects the DRY_RUN environment variable.
    """
    is_safe, reason = _is_command_safe(command)
    if not is_safe:
        result = {
            "status": "blocked",
            "command": command,
            "reason": reason,
            "message": "This command was blocked by the safety system.",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        _execution_history.append(result)
        return json.dumps(result, indent=2)

    dry_run = os.getenv("DRY_RUN", "true").lower() == "true"
    if dry_run:
        result = {
            "status": "dry_run",
            "command": command,
            "message": f"[DRY RUN] Would execute: {command}",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        _execution_history.append(result)
        return json.dumps(result, indent=2)

    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        result = {
            "status": "success" if proc.returncode == 0 else "error",
            "command": command,
            "return_code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "timestamp": datetime.now(UTC).isoformat(),
        }
        _execution_history.append(result)
        return json.dumps(result, indent=2)

    except subprocess.TimeoutExpired:
        result = {
            "status": "timeout",
            "command": command,
            "message": f"Command timed out after {timeout}s",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        _execution_history.append(result)
        return json.dumps(result, indent=2)

    except Exception as e:
        result = {
            "status": "error",
            "command": command,
            "message": f"Execution failed: {str(e)}",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        _execution_history.append(result)
        return json.dumps(result, indent=2)


def get_execution_history() -> str:
    """Return the in-memory command execution history as JSON."""
    return json.dumps({
        "total_commands": len(_execution_history),
        "history": _execution_history,
    }, indent=2)