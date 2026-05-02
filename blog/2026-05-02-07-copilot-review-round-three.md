---
title: "Round three: Copilot finds the failure modes I added by handling failure modes"
date: 2026-05-02
timestamp: 2026-05-02T13:06:58
tags: [bug-fix, infrastructure]
summary: "PR #11's Copilot review caught three defensive gaps in the manifest-hashing code from PR #11 itself — unhandled OSError, implicit encoding in tests, and orphan reconciliation that turns destructive when templates are missing. All three fixed; tests grew 102→104."
---

## What changed

PR #11 (the second Copilot-review pass — see entry [06](2026-05-02-06-copilot-review-round-two.md)) drew its own automated review. Three findings, all about edge cases in the *new* code from that PR:

1. **Unhandled `OSError` / `UnicodeDecodeError` reading the destination file.** The customization-detection path in `_install_claude_commands()` calls `dst.read_text(encoding="utf-8")` to hash the existing file. If that file is unreadable or contains invalid bytes, install raises and aborts mid-pass — a *new* failure mode introduced by the customization check. Fix: factored a `_safe_file_hash()` helper that returns `None` on failure. Callers fall through to overwriting from the template (the cautious-but-not-paralyzed default), and the same helper is used in the uninstall path.

2. **Tests didn't specify `encoding="utf-8"`.** Production code is consistent about it; the new tests in `TestSlashCommands` weren't. Mostly cosmetic on macOS/Linux but actually portable on Windows where `Path.read_text()` defaults to `cp1252`-or-similar. Updated the four affected lines.

3. **Orphan reconciliation runs even when `templates/commands/` is missing.** This was the scariest of the three. If the package is broken (incomplete checkout, packaging glitch), `_install_claude_commands()` produced an empty `records` list — and the orphan reconciliation walk then treated *every* previously-tracked command as an orphan and deleted the user's files. A reinstall on a broken install would silently destroy the user's `.claude/commands/`. Fix: when `src_dir.is_dir()` is false, return the previous records unchanged and skip the reconciliation entirely. The next valid install will pick up where it left off.

Two new tests pin the new defensive behavior:
- `test_install_passthrough_when_templates_missing` — monkeypatches `_templates_dir()` at a commandless dir, verifies no files get deleted and the manifest passes through unchanged.
- `test_reinstall_overwrites_unreadable_file` — writes invalid UTF-8 (`\xff\xfe…`) to an installed command file and verifies reinstall recovers by overwriting from the template instead of crashing.

102 → 104 tests, all green.

## Why it matters

The pattern across all three findings is the same: **defensive code that only works when the system is healthy is a regression, not a defense.** Each issue was introduced by the previous round's "make this safer" work:

- Customization detection (PR #11) added new I/O on every reinstall. That I/O can fail. Without try/except around it, the safety check became a new crash site.
- Manifest hashing (PR #11) added new fields to read in tests. Without explicit encoding, those reads pick up the platform default — fine on dev machines, latent bug on Windows users.
- Orphan reconciliation (PR #11) added a delete loop driven by "things in the previous manifest but not in the current build." The "current build" assumption silently included "the build is intact." When that assumption is false, the loop becomes a destruction loop.

Round one (PR #10) was the docs-and-binary-disagreed class. Round two (PR #11) was the schema-asymmetry class (`files` had hashes; `commands` didn't). Round three is the "your safety nets need their own safety nets" class. Each class is hard to spot from inside the change, easy to spot from a one-shot diff read by an external reviewer.

## How it works

The shape of each fix:

**Issue 1 — `_safe_file_hash()`:**
```python
def _safe_file_hash(path: Path) -> str | None:
    try:
        return Manifest._sha256(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return None
```

Both the install and uninstall hot paths now go through this helper. Callers treat `None` as "I can't be sure of the file's state" and fall back to whichever choice is conservative for their context — overwrite-from-template on install (we have a known-good source), preserve-the-file on uninstall (the user might want it).

**Issue 3 — early return on missing templates:**
```python
if not src_dir.is_dir():
    return list(previous), [], []
```

The list copy is intentional: callers expect `records` to be a fresh list they can append to. Returning `previous` directly would alias the prior manifest's list and risk later mutation.

A subtlety worth flagging: returning `previous` unchanged means a reinstall against a broken build leaves the manifest *exactly* as it was. That's the right call — the alternative ("we don't know, so empty everything out") would be worse than doing nothing. The user's next valid install picks up from a known-good state.

**Issue 2** was a four-line edit to the tests, no narrative needed.

## What's next

Two follow-ups this surfaced:

- **Apply the same defensive shape to the Stop hook helpers.** `_install_claude_stop_hook()` and `_uninstall_claude_stop_hook()` do their own file I/O without the same protections. The blast radius is smaller (one script, not three+), but the failure modes are identical. Worth a quick pass when next touching that code.
- **A test fixture for "broken package state."** I had to monkeypatch `_templates_dir()` to test the missing-`src_dir` case. If we expect more of these "what happens when the package is unhealthy" tests, a shared fixture (or a `--templates-dir` flag for testability) would reduce ceremony. Not blocking; flag for the next batch.

## Surprises

The orphan-reconciliation issue was the one I'd have been least likely to find through dogfooding. The other two have natural triggers — encoding issues show up on Windows, unreadable files show up if a hook half-writes a file. But "what happens when `_templates_dir()` exists but `commands/` doesn't?" requires a specific kind of broken state that real users almost never hit in clean conditions. It's the exact kind of bug that lives undisturbed for years until someone has a weird CI cache or a half-extracted wheel and watches their command files vanish on reinstall.

That's also what makes round-three Copilot reviews valuable in a different way than rounds one and two. The first two were "the binary contradicts the docs" / "the schema is asymmetric" — both visible from reading the code carefully. Round three was "consider this rare combination of failure conditions you didn't put in your test plan." That's adversarial review in the useful sense — not finding bugs you wrote, but finding bugs you'd never write a test for unprompted. Worth keeping the loop going for at least one more round on every meaningful PR.
