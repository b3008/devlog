---
title: "Copilot round four: asymmetric trust for install vs uninstall"
date: 2026-06-12
timestamp: 2026-06-12T15:19:19
tags: [bug-fix, infrastructure]
summary: "PR #12's review produced two fixes and one deliberate refusal — and forced a policy worth naming: when devlog can't prove a file is its own, install overwrites (a stale hook is worse than a lost edit) while uninstall preserves (a stray file is better than a deleted one)."
---

## What changed

PR #12's Copilot review returned three findings on the new hook-hashing code — the round-three pattern again, defensive code growing its own failure surfaces:

1. **Uninstall deleted scripts it couldn't verify.** Pre-sha256 manifest records have no hash, and `_uninstall_claude_hook` deleted the script unconditionally in that case — a user who customized a hook under an old devlog and then uninstalled would lose their edits. Fixed: deletion now requires positively identifying the file as devlog's, by the recorded hash or (for hash-less records) the currently shipped template. Anything else is preserved with a notice.
2. **`_read_session_log` loaded the whole log into memory.** The file grows one line per session forever. Fixed: streamed line-by-line.
3. **Reinstall overwrites pre-sha scripts.** Flagged as contradicting the preservation behavior — and refused, with the rationale now documented in-code: without a recorded hash, an old template and a user edit are indistinguishable, and preserving-when-unsure would have permanently pinned the broken exit-2 Stop hook on every legacy install. The stale-script repair that fixed this very machine's global hook earlier today depended on that overwrite.

142 tests, all green; both new uninstall branches pinned.

## Why it matters

Findings 1 and 3 are the same situation — "the manifest can't prove ownership" — and got opposite answers. That's not inconsistency; it's a policy worth naming: **resolve uncertainty toward the recoverable outcome.** On install, overwriting from the template leaves a working hook and the worst case (a lost pre-hash edit) was already the behavior of every prior version; on uninstall, deletion is unrecoverable while a stray unregistered script is inert. Same uncertainty, different blast radii, different defaults.

## What's next

The one-time migration window closes by itself: any reinstall rewrites the manifest with hashed records, after which customizations are detected on both paths. If a `devlog doctor` ever lands, "hook script matches neither the recorded hash nor any shipped template" is exactly the kind of finding it should surface.
