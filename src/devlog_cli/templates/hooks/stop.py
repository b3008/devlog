#!/usr/bin/env python3
"""
devlog Stop hook for Claude Code.

Fires when the agent is about to end a turn. Reads the hook input JSON
from stdin; if this is the first stop of the turn (stop_hook_active is
false), it blocks the stop once and injects a reminder to check whether
the turn warrants a development blog entry. On the agent's next stop
attempt, stop_hook_active is true and the hook exits cleanly.

This is a deterministic, single-shot reminder. It does not inspect the
transcript or guess whether work happened — that judgment is left to the
agent, informed by the convention text in CLAUDE.md.
"""
from __future__ import annotations

import json
import sys


REMINDER = (
    "devlog reminder: before ending this turn, check whether anything in "
    "this session hit a trigger from CLAUDE.md's 'When to write an entry' "
    "list \u2014 including architectural or scope decisions reached without "
    "code changes. If yes, write or update the blog entry in blog/ now, "
    "then end the turn. If nothing in this turn qualifies, just stop again "
    "and this hook will let you through."
)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # Malformed input — don't block the agent over hook plumbing.
        sys.exit(0)

    if payload.get("stop_hook_active"):
        # Already reminded once this turn; let the stop through.
        sys.exit(0)

    json.dump({"decision": "block", "reason": REMINDER}, sys.stdout)
    sys.exit(2)


if __name__ == "__main__":
    main()
