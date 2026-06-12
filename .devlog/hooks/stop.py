#!/usr/bin/env python3
"""
devlog Stop hook for Claude Code.

Fires when the agent is about to end a turn. Reads the hook input JSON
from stdin; if this is the first stop of the turn (stop_hook_active is
false), it blocks the stop once and injects a reminder to check whether
the turn warrants a development blog entry. On the agent's next stop
attempt, stop_hook_active is true and the hook exits cleanly.

Blocking uses Claude Code's structured channel: {"decision": "block"}
JSON on stdout with exit code 0. Exit code 2 also blocks, but renders
as a red "Stop hook error" in the UI — wrong for a deliberate,
designed-in reminder.

This is a deterministic, single-shot reminder. It does not inspect the
transcript or guess whether work happened — that judgment is left to the
agent, informed by the convention text in CLAUDE.md.

When installed globally (~/.devlog/hooks/stop.py) it defers to a
project-local devlog hook if one is registered in the project's
.claude/settings.json, so only one reminder fires per stop.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REMINDER = (
    "devlog: check this turn against CLAUDE.md's 'When to write an entry' "
    "triggers \u2014 decisions count, not only code. If any apply, write or "
    "update the entry in blog/ before stopping. Otherwise stop again to pass."
)


def _is_global_instance(script_path: Path) -> bool:
    """True when this copy is the globally-installed hook (~/.devlog/hooks/)."""
    try:
        return script_path.resolve() == (Path.home() / ".devlog" / "hooks" / "stop.py").resolve()
    except OSError:
        return False


def _local_devlog_hook_registered(cwd: str | None) -> bool:
    """Detect a project-local devlog Stop hook in <cwd>/.claude/settings.json.

    When both the global and a per-project hook are installed, both fire on
    every stop and the agent gets two reminders. The global instance defers
    to the more specific one."""
    if not cwd:
        return False
    settings_path = Path(cwd) / ".claude" / "settings.json"
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(settings, dict):
        return False
    for entry in (settings.get("hooks") or {}).get("Stop", []) or []:
        if not isinstance(entry, dict):
            continue
        for h in entry.get("hooks", []) or []:
            if not isinstance(h, dict):
                continue
            command = h.get("command", "")
            if (
                h.get("type") == "command"
                and ".devlog/hooks/stop.py" in command
                and "$CLAUDE_PROJECT_DIR" in command
            ):
                return True
    return False


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # Malformed input — don't block the agent over hook plumbing.
        sys.exit(0)

    if payload.get("stop_hook_active"):
        # Already reminded once this turn; let the stop through.
        sys.exit(0)

    try:
        if _is_global_instance(Path(__file__)) and _local_devlog_hook_registered(payload.get("cwd")):
            # The project's own hook will deliver the reminder; stay quiet.
            sys.exit(0)
    except Exception:
        # Defer-detection is best-effort; on any surprise, fall through and fire.
        pass

    json.dump({"decision": "block", "reason": REMINDER}, sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
