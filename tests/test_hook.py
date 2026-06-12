"""Tests for the Claude Code Stop hook script logic."""
from __future__ import annotations

import json
import os
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
        # Structured channel: exit 0 + {"decision": "block"} JSON. Exit 2
        # would also block, but renders as a red "Stop hook error" box.
        code, stdout = _run_hook({"stop_hook_active": False, "session_id": "test"})
        assert code == 0
        output = json.loads(stdout)
        assert output["decision"] == "block"
        assert "devlog" in output["reason"]
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


class TestGlobalDefersToLocal:
    """The globally-installed hook instance (~/.devlog/hooks/stop.py) stays
    quiet when the project registers its own devlog Stop hook, so only one
    reminder fires per stop."""

    def _setup(self, tmp_path: Path) -> tuple[Path, Path]:
        home = tmp_path / "home"
        hook_dir = home / ".devlog" / "hooks"
        hook_dir.mkdir(parents=True)
        (hook_dir / "stop.py").write_bytes(HOOK_SCRIPT.read_bytes())
        project = tmp_path / "project"
        project.mkdir()
        return home, project

    def _run_global_hook(self, home: Path, payload: dict) -> tuple[int, str]:
        result = subprocess.run(
            [sys.executable, str(home / ".devlog" / "hooks" / "stop.py")],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env={**os.environ, "HOME": str(home)},
        )
        return result.returncode, result.stdout

    def _register_local_hook(self, project: Path) -> None:
        claude_dir = project / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text(
            json.dumps({
                "hooks": {
                    "Stop": [{
                        "hooks": [{
                            "type": "command",
                            "command": 'python3 "$CLAUDE_PROJECT_DIR/.devlog/hooks/stop.py"',
                        }]
                    }]
                }
            }),
            encoding="utf-8",
        )

    def test_defers_when_local_hook_registered(self, tmp_path: Path):
        home, project = self._setup(tmp_path)
        self._register_local_hook(project)
        code, stdout = self._run_global_hook(
            home, {"stop_hook_active": False, "cwd": str(project)}
        )
        assert code == 0
        assert stdout == ""

    def test_fires_without_local_hook(self, tmp_path: Path):
        home, project = self._setup(tmp_path)
        code, stdout = self._run_global_hook(
            home, {"stop_hook_active": False, "cwd": str(project)}
        )
        assert code == 0
        assert json.loads(stdout)["decision"] == "block"

    def test_fires_with_unparseable_settings(self, tmp_path: Path):
        home, project = self._setup(tmp_path)
        claude_dir = project / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text("{not json", encoding="utf-8")
        code, stdout = self._run_global_hook(
            home, {"stop_hook_active": False, "cwd": str(project)}
        )
        assert code == 0
        assert json.loads(stdout)["decision"] == "block"

    def test_local_instance_never_defers(self, tmp_path: Path):
        # The template path is not ~/.devlog/hooks/stop.py, so this runs as a
        # local instance — it must fire even when settings register a local hook.
        home, project = self._setup(tmp_path)
        self._register_local_hook(project)
        result = subprocess.run(
            [sys.executable, str(HOOK_SCRIPT)],
            input=json.dumps({"stop_hook_active": False, "cwd": str(project)}),
            capture_output=True,
            text=True,
            env={**os.environ, "HOME": str(home)},
        )
        assert result.returncode == 0
        assert json.loads(result.stdout)["decision"] == "block"
