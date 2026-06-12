---
title: "Trimming the Stop hook reminder, deferring the smarter-hook idea"
date: 2026-05-31
timestamp: 2026-05-31T19:09:50
tags: [ux, infrastructure, refactor]
summary: "The Stop hook's reminder text shrunk from ~52 to ~30 words after the user pointed out that every turn surfaces a red 'Stop hook error' box. The smarter-hook proposal (mutation-gated blocking) was considered and deferred — keep the deterministic single-shot design, just stop being verbose inside it."
---

## What changed

The `REMINDER` constant in `.devlog/hooks/stop.py` (and its template at `src/devlog_cli/templates/hooks/stop.py`) was rewritten from:

> devlog reminder: before ending this turn, check whether anything in this session hit a trigger from CLAUDE.md's 'When to write an entry' list — including architectural or scope decisions reached without code changes. If yes, write or update the blog entry in blog/ now, then end the turn. If nothing in this turn qualifies, just stop again and this hook will let you through.

to:

> devlog: check this turn against CLAUDE.md's 'When to write an entry' triggers — decisions count, not only code. If any apply, write or update the entry in blog/ before stopping. Otherwise stop again to pass.

Same semantics: trigger reference, decisions-count clause, write-or-update path, otherwise-stop-again behavior. `tests/test_hook.py` lost its `"devlog reminder"` substring assertion (which the trimmed prefix `"devlog:"` no longer satisfies) and now just asserts `"devlog"`; 5/5 hook tests still pass.

No behavior change. The hook still always blocks the first stop, still passes the second, still ignores its own crashes.

## Why it matters

The user opened the session by surfacing a UX pain point: every turn — including read-only `/devlog-catchup`, including pure Q&A — ends with a red **Stop hook error** box in Claude Code's UI. That framing comes from Claude Code's hook protocol: exit code 2 is the only channel a hook has to say "do not stop, show this to the agent", and the UI doesn't distinguish "deliberate soft-block" from "hook exploded". So a deterministic, designed-in reminder reads as an error.

> **Update 2026-06-12**: The premise above is wrong, verified against the hooks docs. Exit code 2 is *not* the only blocking channel — `{"decision": "block", "reason": ...}` JSON with exit **0** blocks the stop without the red error styling. The red box this entry works around was self-inflicted by the script mixing the two protocols (JSON on stdout + exit 2). See [2026-06-12-01-assessment-expanded](2026-06-12-01-assessment-expanded.md); the fix ships with that session's PR.

Over many turns that trains the user to treat the red box as wallpaper — which is exactly the failure mode the hook was designed to prevent.

The trim alone doesn't fix the false-positive rate, but it reduces the cost per false positive. A shorter reminder is faster to scan and dismiss, less visually loud, and stops burying the actual signal ("did this turn warrant an entry?") under boilerplate about how the hook works.

## How it works

No mechanism changed. Two surfaces edited:

- `.devlog/hooks/stop.py` — the installed copy in this self-dogfooding repo.
- `src/devlog_cli/templates/hooks/stop.py` — the template that ships to every install.

Both kept in sync by hand. (Open follow-up from [round-three](2026-05-02-07-copilot-review-round-three.md): `manifest.hooks` still doesn't carry a `sha256` on the hook script, so a user who customized the reminder locally would lose it on the next `devlog install`. Same drift/customization/overwrite failure mode that `commands` had until [round-two](2026-05-02-06-copilot-review-round-two.md) fixed it. Not in scope this session.)

## What's next

The architectural call worth recording: we explicitly considered **making the hook smarter** — scan the transcript on stdin for mutating tool calls in this turn, loud-block only when Edit/Write/non-trivial Bash happened, silent advisory via `hookSpecificOutput.additionalContext` otherwise. That would actually cut the false-positive rate, not just the per-event cost. The user chose to keep the current always-block design and only trim the text.

Reasons that decision is defensible:

- The convention explicitly counts decision-only turns as triggers ("architectural or scope decisions reached without code changes"). A mutation-gated hook can't detect those, so the silent-advisory branch would have to carry the load for that case — and a silent advisory is, by construction, ignorable.
- The hook's original design virtue was being **deterministic and dumb**. Adding transcript inspection is the first step toward the hook itself having bugs it needs reviews to catch — exactly the failure pattern [round three](2026-05-02-07-copilot-review-round-three.md) was about.
- Cheaper fix first: if the trim alone makes the noise tolerable, the smarter-hook work is dead weight.

The deferred work isn't dead though. If the trim doesn't change the wallpaper effect (real signal: does the user stop ignoring the red box?), the next step is the hybrid — mutation-gated loud block + silent advisory on no-mutation turns. Flagged for `learned.md`.

## Surprises

The interesting thing about the discussion was that the user kept asking *why is it called a Stop hook error?* — which I initially treated as a Claude Code framing quirk to explain away. It turned out to be the load-bearing question: once you accept that the UI will always render exit-2 as an error, the whole conversation collapses to "stop using exit 2 when you don't need to" — which is the mutation-gated proposal. The trim is the version of that answer that doesn't require any new code paths, and the user picked it. That's the right call for this stage of the project, but the framing question itself was sharper than the implementation question.
