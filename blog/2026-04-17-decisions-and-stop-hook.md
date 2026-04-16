---
title: "Catching decision-only turns: convention rewording + Claude Code Stop hook"
date: 2026-04-17
tags: [architecture, feature, cli]
summary: "Two text changes plus an opt-in runtime hook close the gap where agents skipped writing entries because no artifact was produced."
---

## What changed

Three additions, derived from a project where the convention was correctly
installed yet still failed to fire when the session ended on a real
architectural decision (no code written, just *"let's keep that module
separate"*).

- **Wording (F1).** The opener changed from *"non-trivial work was
  produced"* to *"non-trivial progress was made"*, with a follow-on
  sentence: *"Progress includes decisions reached in discussion — not
  only code or files produced."* "Produced" was cueing agents toward
  artifact-shaped output and quietly excluding decisions.
- **Triggers (F2).** *"Architecture decision made"* became *"Architecture
  or scope decision reached (even if no code changed yet)"*, and a new
  paragraph after the triggers list spells out that a turn ending on a
  decision counts on its own — implementation can be a separate entry
  later. Updated in both `convention.py` defaults and the
  `templates/config.yaml` shipped to new projects.
- **Stop hook (F5).** New opt-in `devlog install --ai claude --with-hook`
  copies a small `stop.py` script into `.devlog/hooks/` and registers it
  as a `Stop` hook in `.claude/settings.json`. When the agent tries to
  end its turn, the hook injects a one-shot reminder asking it to check
  whether anything in the session warrants an entry. Idempotent on
  reinstall, cleanly removed by `uninstall`, and preserves any unrelated
  settings the user already had.

## Why it matters

The previous round (E4/E2/E5) hardened the convention's wording and
visibility, but assumed the agent would self-trigger on the right turns.
The case study showed a third failure mode that wording alone couldn't
catch: an agent acting *correctly* by its reading of a slightly imprecise
rule. Tightening the rule (F1, F2) is necessary but not sufficient — for
sessions where the agent's interpretation differs from the user's intent,
runtime enforcement (F5) is the only durable answer.

The hook is opt-in for a reason. It mutates `.claude/settings.json`,
which is a file the user owns and may share via git. Defaulting to
side-effect-free installs keeps trust high; the install command's tail
prints a one-line tip surfacing the option for users who want it.

## How it works

The hook script is deliberately uninteresting:

```python
if payload.get("stop_hook_active"):
    sys.exit(0)
json.dump({"decision": "block", "reason": REMINDER}, sys.stdout)
sys.exit(2)
```

`stop_hook_active` is Claude Code's loop-prevention signal: it's true on
the agent's *second* stop attempt within a turn. So the hook blocks once
per turn, surfaces the reminder, then gets out of the way. It does not
inspect the transcript or guess whether work happened — that judgment is
the agent's, informed by CLAUDE.md.

Settings.json merging is structural rather than textual:

1. Read existing `.claude/settings.json` (parse JSON, refuse to proceed
   on parse error rather than corrupting the user's file).
2. `setdefault` into `hooks.Stop`, strip any prior devlog entry (matched
   by the script path appearing in any command), append a fresh one.
3. Write back with stable indentation.

Identification on reinstall and uninstall is by the substring
`.devlog/hooks/stop.py` in the command. No magic markers, no JSON
comments, just a stable path that no unrelated hook would happen to
contain. The manifest gains a `hooks` array recording everything needed
for clean removal: event type, settings file path, script path, command
string.

The command itself uses `$CLAUDE_PROJECT_DIR` so it resolves correctly
regardless of cwd:

```json
"command": "python3 \"$CLAUDE_PROJECT_DIR/.devlog/hooks/stop.py\""
```

## What's next

The reminder text is a first cut and will probably need tuning once we
see how agents respond to it in practice — too soft and they'll skip
anyway; too forceful and they'll write entries for trivial turns. The
loop-prevention contract makes the hook safe to iterate on: change the
script, no settings rewrite needed.

Open questions for later iterations:

- Whether to extend hook support beyond Claude Code (Codex CLI, Gemini,
  etc., as their hook stories solidify).
- Whether `devlog status` should detect stale-but-installed hooks (script
  missing, settings entry orphaned) and offer to re-link them.
- Whether the decision-only entry skeleton (F3 from the case-study notes)
  is needed, or whether the existing "skip sections that don't apply"
  guidance is enough now that the wording is friendlier to decisions.
