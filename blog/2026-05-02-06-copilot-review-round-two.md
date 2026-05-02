---
title: "Second pass on the Copilot review: config-aware templates + hashed command manifest"
date: 2026-05-02
timestamp: 2026-05-02T11:54:20
tags: [bug-fix, infrastructure, ux]
summary: "PR #8's Copilot review had nine comments — only the bootstrap gap got fixed in PR #10. The remaining six fell into three buckets: templates lying about config, the manifest losing track of orphans, and a stale Stop hook entry in this repo. All three are addressed; tests grew from 97 to 102."
---

## What changed

PR #8's automated Copilot review left nine comments. PR #10 closed the missing-scaffolding bug (entry [05](2026-05-02-05-copilot-review-preflight-fix.md) covers that) but the other six were still open. This session works through them.

The six grouped into three real fixes:

1. **Templates hardcoded `blog/` and `_index.md`.** All three slash commands now open with a "Resolve paths" preamble:

   > - `<blog_dir>` is the `blog_dir` value (default: `blog`).
   > - `<index_file>` is the `index_file` value (default: `_index.md`).

   Every later reference uses `<blog_dir>/<index_file>` with the literal default given parenthetically (e.g. `` `<blog_dir>/<index_file>` (e.g. `blog/_index.md`) ``). Projects that move their blog or rename the index now get correct behavior; projects on defaults still see something concrete.

2. **`/devlog-write` referenced "this project's CLAUDE.md".** That broke under `--global` installs, where there is no per-project CLAUDE.md. The bootstrap fallback now prioritizes the `devlog` CLI (`devlog init` if on PATH) and only falls back to a globally-loaded "First-time setup" subsection if the CLI isn't available. Step 3 also stops pointing at CLAUDE.md and points directly at `.devlog/config.yaml` — the source of truth either way.

3. **Manifest hygiene around slash commands.** Three related problems collapsed into one fix:
   - Reinstalls didn't reconcile the previous `manifest.commands` against the new template set, so a renamed/removed template would orphan the old file.
   - `commands` entries lacked a `sha256`, unlike `files` — so reinstall couldn't tell whether a user had customized a command body, and would happily overwrite or delete edits.
   - This repo's `claude.manifest.json` had `"hooks": []` even though `.claude/settings.json` actively pointed at `.devlog/hooks/stop.py` (the Stop hook has been firing on the manicure session and on this one). Uninstall would have left the hook behind.

   Fix: `commands` entries now carry a `sha256`. `_install_claude_commands()` takes the previous manifest, hashes everything before copying, preserves user-customized files, and removes orphans whose hash still matches the recorded install hash. `_uninstall_claude_command()` does the same — divergent hash means leave it alone. And one `devlog install --ai claude --with-hook` in this repo re-recorded the Stop hook in the manifest, closing the third item.

Tests grew from 97 to 102 — five new cases in `TestSlashCommands` covering hash recording, customization preservation on reinstall, customization preservation on uninstall, orphan removal, and orphan preservation when modified.

## Why it matters

The first two fixes are about not lying. The README and the templates were each making an implicit promise the binary couldn't keep:

- The convention block already documents that `blog_dir` and `index_file` are configurable. The slash commands ignored that and went straight to `blog/_index.md`. Any project that exercised the customization would silently get pointed at the wrong files.
- `/devlog-write`'s bootstrap leaned on a doc structure (a "First-time setup" subsection in this project's CLAUDE.md) that under `--global` doesn't live in the project at all.

Both are the same shape as the missing-scaffolding bug from earlier today — **the docs assume something the binary doesn't enforce**. Copilot caught all of these on a one-shot read of the diff because it reads both sides cold.

The third fix (manifest hygiene) is the more interesting one architecturally. The original commands manifest entry was deliberately minimal — name and path, nothing else. That looked clean at the time, but it traded clean shape for the ability to detect three failure modes that always come with installable artifacts:

- **Drift** (we said we installed X, the file on disk is Y).
- **Customization** (the user touched the file; we can't tell).
- **Orphans** (we used to install X, we don't anymore, the file is still there).

Adding the hash gives the manifest the resolution to answer all three. The pattern parallels `files`, which has always carried hashes for exactly this reason. The asymmetry between `files` and `commands` was the bug.

## How it works

The new install flow, per command:

```
1. Hash the template we're about to install: new_hash.
2. If a previous manifest exists and tracked this command:
     prev_hash = previous record's sha256
     If the file on disk hashes to current_hash:
       If current_hash != prev_hash AND current_hash != new_hash:
         user has customized → record current_hash, skip overwrite, warn.
3. Otherwise: copy the template, record new_hash.
```

After the per-command pass, a reconciliation walk over the previous manifest catches anything that's no longer in the new template set:

```
For each previous command not in new manifest:
  If hash on disk == prev_hash:
    delete the file (devlog owns it; no edits since install).
  Else:
    leave it alone (user customized it; we don't have permission to wipe).
```

Uninstall mirrors the customization check: divergent hash means the user wants the file, even if they originally got it from us.

`_install_claude_commands()` now returns `(records, preserved, removed_orphans)` — the install tree surfaces both:

```
├── Preserved customized slash command /devlog-catchup
│   (.claude/commands/devlog-catchup.md — local edits kept)
├── Removed orphaned slash command .claude/commands/devlog-zombie.md
```

The previous version's signature returned just `list[dict]`, so the change is mildly breaking for any external caller — but `_install_claude_commands` is private (underscore-prefixed) and only called from two places in `__init__.py`, so the blast radius is limited.

## What's next

A few related cleanups that didn't make this session:

- **Hook hashing.** `manifest.hooks` doesn't carry hashes for the script either. The Stop hook script is currently overwritten unconditionally by reinstall — same failure mode as commands had. Worth fixing with the same shape, but the surface is much smaller (one script today, not three).
- **CLI flag for `--without-commands`.** Still not built. Not blocking anything; revisit when someone asks.
- **`devlog doctor`.** The third Copilot finding (this repo's manifest was out of sync with reality) is the kind of thing a doctor command could detect automatically. Right now it took a human reading a JSON file to notice. Still premature — but the use case keeps getting clearer.

## Surprises

I expected the templates fix to be the boring one and the manifest fix to be the interesting one. It turned out the other way around.

The templates fix forced a small style decision: should the prompt say `<blog_dir>/<index_file>` (parametric, config-aware), or `blog/_index.md` (concrete, default-aware)? Both? I ended up with both — `<placeholder>` plus an `(e.g. `default`)` parenthetical — because either alone fails for a real audience. Pure placeholders read as alien; pure concrete defaults are exactly the bug Copilot reported. Hybrid worked, and the existing test assertion (`assert "blog/_index.md" in body`) still held without modification, which was an unintended but useful signal that the literal-default-in-parens form was right.

The manifest fix surfaced something subtler: the previous version's `commands` manifest is *user-visible*. The hash-bearing version is a strict superset of the older fields, so old manifests load fine — but now I have a one-time backwards-compat window where some users in the wild have hash-less command records. The code handles that correctly (it just doesn't try to detect customization on those entries — it overwrites unconditionally as before), but the next session that touches manifest schema is going to want to think about migrations more carefully than I did here. Flagging it in `learned.md`.
