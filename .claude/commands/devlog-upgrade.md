---
description: Upgrade the devlog tool to the latest version from GitHub, then resync this repo's convention to it. Pass --check to preview, or --tool-only / --project-only to scope.
---

Upgrade devlog to the latest version and resync this project's convention to it. This drives the `devlog upgrade` CLI command, which works in two layers: it upgrades the installed `devlog` tool from GitHub, then re-runs `devlog install` for every agent configured in this repo (and the global Claude install, if one is detected) so the freshly shipped convention, hooks, and slash commands are what land on disk.

Arguments (may be empty): $ARGUMENTS

Forward only these recognized flags through to `devlog upgrade`; ignore anything else:

- `--check` — preview only; make no changes.
- `--tool-only` — upgrade the binary but skip resyncing this repo.
- `--project-only` — skip the tool upgrade; only resync this repo to the already-installed tool.

(`--project-only` and `--tool-only` are mutually exclusive — the CLI rejects both together.)

## Preflight — locate the devlog binary

Run `command -v devlog` to check whether the `devlog` CLI is on PATH.

- **Found** — use `devlog` for every command below.
- **Not found** — devlog isn't installed as a persistent binary, so there's nothing to upgrade through. Don't guess at a package manager. Tell the user, and suggest a persistent install they can run themselves:
  ```
  uv tool install --force git+https://github.com/b3008/devlog.git
  ```
  After that they can re-run `/devlog-upgrade`. Stop here.

## Step 1 — Preview the plan

Run the upgrade in preview mode first, forwarding any recognized flags from `$ARGUMENTS`:

```
devlog upgrade --check <forwarded flags>
```

Read its output. Install-method-aware, it reports:

- whether the tool can self-upgrade and the exact command it would run (e.g. `uv tool upgrade devlog`), **or** a warning that it can't — because devlog is running from a source checkout, an ephemeral `uvx` invocation, or an unrecognized install; and
- which agents it would resync (per-project agents recorded in `.devlog/manifests/`, plus `claude (global)` if a global install is detected).

Relay the plan to the user in a line or two.

## Step 2 — Apply (unless the user only wanted a preview)

- **If the user passed `--check`** — stop after Step 1. The preview *is* the deliverable; mutate nothing.

- **If the preview shows a self-upgradeable tool** (it printed an upgrade command, not a warning) — run the real upgrade, forwarding the same flags:
  ```
  devlog upgrade <forwarded flags>
  ```
  Stream its output. It upgrades the tool, prints the `old → new` version delta (or "already on the latest"), then resyncs each agent **through the freshly installed binary** so the new templates are what get written.

- **If the preview warns it can't self-upgrade** — don't run the bare `devlog upgrade`; it would only reprint the manual instruction and exit. Handle the case the warning names:
  - **Source checkout** (devlog is running from a `git` clone — e.g. you're inside the devlog repo itself): the upgrade is a `git pull`, not a package bump. Offer to run `git pull` in the checkout; if the working tree is dirty, confirm with the user first. Once it's pulled, run `devlog upgrade --project-only` to resync this repo to the updated source.
  - **Ephemeral `uvx`**: nothing persistent exists to upgrade — each `uvx` run already fetches the latest. Suggest a persistent install if they want `/devlog-upgrade` to manage it: `uv tool install --force git+https://github.com/b3008/devlog.git`.
  - **Unrecognized install**: relay the manual command the CLI printed, verbatim.

## Step 3 — Report back

Summarize the outcome:

- the version delta (`X.Y.Z → A.B.C`, or "already on the latest");
- which agents were resynced, and any that failed;
- or, if nothing in this repo was resyncable, that the tool was upgraded but the user should run `devlog install --ai <agent>` here first to start tracking it.

If `devlog upgrade` exited non-zero, surface the failure (and any fallback command it printed) from the streamed output — don't report success.
