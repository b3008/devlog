---
type: "Devlog Entry"
title: "Preserving a customization until the next release"
date: 2026-07-29
timestamp: 2026-07-29T15:20:00
tags: [bug-fix, cli, architecture]
description: "Chasing a missing --force flag turned up a silent data-loss bug: install protected a customized file once, then destroyed it on the next template change, because preserving adopted the user's hash as the baseline."
---

## What changed

Two things, one of which I went looking for and one of which I didn't.

**`devlog install --force`** overwrites locally-edited hooks and slash commands with the shipped templates. It reports what it discarded rather than folding it into the ordinary "Refreshed" line, and it never deletes — orphan reconciliation is deliberately left alone, because overwriting a stale file is recoverable from the template and deleting a customized one is not.

**The preservation baseline is fixed.** Manifest records now carry `source_sha256` — the hash of what devlog last actually *wrote* to a path — alongside the existing `sha256`, which is the hash of whatever ended up on disk. The customization check compares against the former.

## Surprises

I went in to add an escape hatch and found that my previous entry had misdiagnosed the thing it was describing.

The claim was that `install` compares the installed file against the shipped template, so any difference reads as a customization. That is not what the code does. It is a three-way comparison against the manifest's install-time hash *and* the new template, which means an untouched file whose template moved underneath it resyncs on its own. I had written the entry from the tool's output — `Preserved customized Stop hook script` — without reading the ten lines behind it. The output was accurate; my inference was not. Verifying it took two runs:

```
CASE A: file untouched, template changed   → Refreshed  ✓ already correct
CASE B: file locally edited                → Preserved  ✓ right default
```

So the real gap was narrower than advertised: preservation was working, and there was simply no way to say *"I know, overwrite it anyway."*

**Then the escape hatch exposed a much worse bug.** Testing `--force` end-to-end, the run reported `Refreshed` where I expected `Overwrote customized`. The reason is that a preserving install writes the *user's* hash into `sha256` — reasonably, since that field means "what is on disk". But that same field is the baseline for the next customization check. So the sequence is:

1. User edits the hook. Reinstall preserves it. ✓
2. The manifest now records the user's content as the install-time state.
3. The template ships a change.
4. Reinstall computes `current == recorded` → "not customized" → **overwrites the user's file** and reports `Refreshed`.

```
1. reinstall (preserve)         Preserved customized Stop hook script
2. template changed, reinstall  Refreshed existing Stop hook
   USER CUSTOMIZATION still present: 0
```

The customization survives exactly as long as nobody ships a new template. The protection quietly expires at the next release — which is both the moment it matters most and the moment nobody is watching. And because the check had *just* worked correctly a step earlier, the failure looks like success twice over.

## How it works

The bug is a single overloaded field. `sha256` was answering two different questions: *"what is on disk?"* (needed by uninstall, so it only deletes files it recognises) and *"what did devlog put there?"* (needed by install, to detect edits). Those coincide until the first preserve, and diverge permanently after it.

Splitting them is the whole fix. `source_sha256` updates only when devlog actually writes a file, and is carried forward untouched when preserving:

```python
baseline = prev.get("source_sha256") or prev.get("sha256")
customized = current_hash != baseline and current_hash != new_hash
```

The `or` is the migration story. The field is purely additive with a safe fallback, so manifests written before it existed keep behaving exactly as they used to and self-heal on the next install — there's a test pinning that path, since it's the one nobody would notice breaking.

Worth being precise about the remaining limit: this detects *"differs from what devlog wrote"*, which is the honest question. It still cannot read intent. A user edit and a hand-applied draft of a future template are the same event, and `--force` exists because only the human knows which one it was.

## What's next

`sha256` is still doing double duty for uninstall, which wants "is this file as I left it" and gets the right answer from the on-disk hash. That's correct today but it is the same overloading that caused this bug, so it is worth a second look before the next field is added.
