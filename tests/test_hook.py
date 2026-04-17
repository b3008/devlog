"""Tests for the Claude Code Stop hook script logic."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK_SCRIPT = Path(__file__).parent.parent / "src" / "devlog_cli" / "templates" / "hooks" / "stop.py"


def _run_hook(payload: dict) -> tuple[int, str]:
    """Run the hook script with the given JSON payload on stdin."""
    result = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout


class TestStopHook:
    def test_first_stop_blocks(self):
        code, stdout = _run_hook({"stop_hook_active": False, "session_id": "test"})
        assert code == 2
        output = json.loads(stdout)
        assert output["decision"] == "block"
        assert "devlog reminder" in output["reason"]
        assert "trigger" in output["reason"]

    def test_second_stop_allows(self):
        code, stdout = _run_hook({"stop_hook_active": True, "session_id": "test"})
        assert code == 0
        assert stdout == ""

    def test_malformed_input_allows(self):
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT)],
            input="not json",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_empty_input_allows(self):
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT)],
            input="",
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_reminder_mentions_decisions(self):
        _, stdout = _run_hook({"stop_hook_active": False})
        output = json.loads(stdout)
        assert "decision" in output["reason"].lower()
