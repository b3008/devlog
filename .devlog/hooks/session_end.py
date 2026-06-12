#!/usr/bin/env python3
"""
devlog SessionEnd hook for Claude Code.

Appends one JSON line per session end to .devlog/sessions.jsonl in the
project the session ran in. This is devlog's coverage signal: sessions
that produce no blog entry are otherwise invisible, so `devlog status`
cannot tell "no sessions happened" apart from "sessions happened and
the convention didn't fire".

Best-effort by design: it only writes when the project already has a
.devlog/ directory, never creates one, and never blocks anything —
all failure paths exit 0.

When installed globally (~/.devlog/hooks/session_end.py) it defers to a
project-local devlog SessionEnd hook if one is registered in the
project's .claude/settings.json, so each session is recorded once.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _is_global_instance(script_path: Path) -> bool:
    """True when this copy is the globally-installed hook (~/.devlog/hooks/)."""
    try:
        return (
            script_path.resolve()
            == (Path.home() / ".devlog" / "hooks" / "session_end.py").resolve()
        )
    except OSError:
        return False


def _local_hook_registered(project_dir: Path) -> bool:
    """Detect a project-local devlog SessionEnd hook in the project settings."""
    settings_path = project_dir / ".claude" / "settings.json"
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(settings, dict):
        return False
    for entry in (settings.get("hooks") or {}).get("SessionEnd", []) or []:
        if not isinstance(entry, dict):
            continue
        for h in entry.get("hooks", []) or []:
            if not isinstance(h, dict):
                continue
            command = h.get("command", "")
            if (
                h.get("type") == "command"
                and ".devlog/hooks/session_end.py" in command
                and "$CLAUDE_PROJECT_DIR" in command
            ):
                return True
    return False


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    project = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd")
    if not project:
        sys.exit(0)
    project_dir = Path(project)
    devlog_dir = project_dir / ".devlog"
    if not devlog_dir.is_dir():
        # Not a devlog project — nothing to record.
        sys.exit(0)

    try:
        if _is_global_instance(Path(__file__)) and _local_hook_registered(project_dir):
            # The project's own hook records this session; avoid double lines.
            sys.exit(0)
    except Exception:
        pass

    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session_id": payload.get("session_id"),
        "reason": payload.get("reason"),
    }
    try:
        with (devlog_dir / "sessions.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass
    sys.exit(0)


if __name__ == "__main__":
    main()
