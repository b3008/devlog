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


# learned.md is meant to be read in full at the start of a session, and it is the
# index once a project splits into .devlog/knowledge/ — either way it is the file
# that always gets loaded, so it is the one worth measuring.
#
# The real limit is ~25k tokens per read, not a byte count. Bytes are only a proxy,
# and a pessimistic one is required: learned.md is dense with identifiers, paths and
# code fragments (~2.5 bytes/token measured, against ~4 for prose), so 25k tokens can
# arrive at ~60KB. Warning at 100KB would stay silent through the whole window where
# reads are already truncating. Past ~256KB the read is refused outright.
BUDGET_BYTES = 60 * 1024
CEILING_BYTES = 256 * 1024


def _learned_state(cwd: str | None) -> tuple[int, bool] | None:
    """(size of .devlog/learned.md, whether .devlog/knowledge/ exists).

    None if there is no cwd or no learned.md. The second element decides which
    remedy to name: a project that has already split needs a different fix than
    one that has not.
    """
    if not cwd:
        return None
    devlog = Path(cwd) / ".devlog"
    try:
        size = (devlog / "learned.md").stat().st_size
    except OSError:
        return None
    try:
        has_knowledge = (devlog / "knowledge").is_dir()
    except OSError:
        has_knowledge = False
    return size, has_knowledge


def _size_warning(size: int, has_knowledge: bool = False) -> str | None:
    """Return a line to append to the reminder, or None when the file is healthy.

    Two tiers, because one flat warning reads the same at 61KB as at 400KB and
    those are different problems: over budget is housekeeping, over the read
    ceiling means the file is not reaching anyone at all.
    """
    if size < BUDGET_BYTES:
        return None
    kb = size // 1024
    # Name the remedy that actually applies. Telling a project that already has
    # knowledge/ to "archive closed threads" sends it back to a lever it has
    # mostly pulled; the index being large means a topic belongs in its own file.
    if has_knowledge:
        remedy = (
            "Move a topic's material out of the index into a .devlog/knowledge/ file, "
            "leaving a one-line hook behind, and delete Open threads that have closed."
        )
    else:
        remedy = (
            "Delete Open threads that have closed or archive them to .devlog/archive/; "
            "if the durable material is what's large, split it into .devlog/knowledge/ "
            "and leave a one-line hook per file behind in learned.md."
        )
    if size >= CEILING_BYTES:
        return (
            f"devlog: .devlog/learned.md is {kb}KB and NO LONGER LOADS — past "
            f"{CEILING_BYTES // 1024}KB the read fails silently, so treat any claim to "
            f"have read it as unverified. {remedy}"
        )
    return (
        f"devlog: .devlog/learned.md is {kb}KB, over its {BUDGET_BYTES // 1024}KB budget "
        "— reads of it return a TRUNCATED page, not the file, and truncation looks like "
        f"success (hard failure at {CEILING_BYTES // 1024}KB). {remedy}"
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

    reason = REMINDER
    try:
        state = _learned_state(payload.get("cwd"))
        if state is not None:
            warning = _size_warning(*state)
            if warning:
                reason = f"{reason}\n\n{warning}"
    except Exception:
        # Size reporting is best-effort; never break a turn over a stat call.
        pass

    json.dump({"decision": "block", "reason": reason}, sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
