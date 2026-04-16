<div align="center">

```
  ██▀▄ █▀▀ █ █ █   ▄▀▄ ▄▀▀
  █  █ █▀  ▀▄▀ █   █ █ █ █
  ▀▀   ▀▀▀  ▀  ▀▀▀  ▀  ▀▀▀
```

### A development blog that writes itself — through the AI agent you already use.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Agents: 27](https://img.shields.io/badge/agents-27-9B59B6.svg)](#supported-agents)

</div>

---

Most developers don't keep a dev log — or they abandon one within a week. But
AI coding agents already sit in the loop where the work happens. `devlog`
teaches them, once per project, to narrate that work as they go.

The result: a time-ordered, portfolio-ready record of your project that
grows automatically, in the agent's own voice.

<br>

## Quickstart

Two commands. No install.

```bash
uvx --from git+https://github.com/b3008/devlog.git devlog init
uvx --from git+https://github.com/b3008/devlog.git devlog install --ai claude
```

Or install it as a `uv` tool for repeated use:

```bash
uv tool install git+https://github.com/b3008/devlog.git
devlog init && devlog install --ai claude
```

<br>

## What actually happens

`devlog install` drops a single, bracketed block into your agent's context
file — leaving whatever you already had intact:

```diff
  # My Project
  <existing CLAUDE.md content stays untouched>
+
+ <!-- DEVLOG:START - Do not edit this section manually -->
+ ## Development Blog (Automatic)
+ After every session where meaningful progress is made, create or
+ update a blog entry in `blog/`.
+ ...triggers, structure, voice, tags, media instructions...
+ <!-- DEVLOG:END -->
```

From then on, the agent writes entries like this without being asked:

```markdown
---
title: "Tag vocabulary now self-updates"
date: 2026-04-16
tags: [feature, cli, ux]
summary: "devlog install now folds tags from existing entries into the rendered vocabulary."
---

## What changed
...

## Why it matters
...

## How it works
...

## What's next
...
```

<br>

## Commands

| Command | What it does |
| --- | --- |
| `devlog init [--name NAME]` | Scaffold `.devlog/`, `blog/`, `blog/media/`, `blog/_index.md`, and `.devlog/learned.md`. |
| `devlog install --ai <key>` | Inject the convention into the agent's context file. Auto-runs `init` if needed. |
| `devlog uninstall --ai <key>` | Remove the convention section and manifest. |
| `devlog list` | List all supported agents. |
| `devlog status` | Show which agents currently have the convention active. |
| `devlog version` | Print version. |

<br>

## Adaptive convention

The convention isn't a frozen snapshot. Three lightweight mechanisms let it
grow with the project:

> **`.devlog/learned.md`** — a shared notebook the agent reads before writing
> and appends to when durable project knowledge surfaces (domain vocabulary,
> recurring themes, open threads). It lives outside the injected sentinel
> block, so accumulation is free and diffable. Humans can edit it too.

> **Self-updating tag vocabulary** — on each `devlog install`, entries in
> `blog/` are scanned and any tags found in their frontmatter are unioned
> into the rendered tag list. The agent is told it may introduce new tags
> when they genuinely fit; the next install folds them into the canonical
> vocabulary.

> **Self-tailoring config** — if the default triggers or voice don't match
> the project's domain (say, creative writing rather than a code project),
> the injected convention instructs the agent to propose edits to
> `config.yaml` and prompt the user to re-run install. The tool adapts to
> the project rather than the other way around.

Together these let the convention absorb what the project has actually been
doing — without anyone curating `config.yaml` by hand.

### Optional: runtime enforcement (Claude Code)

The convention asks the agent to self-check at the end of each turn, but
agents can interpret rules differently depending on whether the turn
produced an artifact. For Claude Code, opt into a Stop hook that injects a
one-shot reminder before the agent ends its turn:

```bash
devlog install --ai claude --with-hook
```

This drops a small script at `.devlog/hooks/stop.py` and merges a `Stop`
hook entry into `.claude/settings.json` (preserving any existing config).
Reinstalls are idempotent; `devlog uninstall --ai claude` removes the
hook entry, deletes the script, and leaves any unrelated settings
untouched.

### Is it working?

`devlog status` reports whether entries are actually being produced — not
just whether the sentinel block is present. If the install is more than a
day old and no entries have been written, it prints a warning with
remediation hints.

```
Blog: blog/ — 3 entries, most recent 2026-04-15

             Installed Conventions
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━┓
┃ Agent       ┃ Context File ┃ Status ┃ Installed  ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━┩
│ Claude Code │ CLAUDE.md    │ active │ 2026-04-10 │
└─────────────┴──────────────┴────────┴────────────┘
```

<br>

## Supported agents

Three agents have dedicated context files:

| Key | Agent | Context file |
| --- | --- | --- |
| `claude` | Claude Code | `CLAUDE.md` |
| `copilot` | GitHub Copilot | `.github/copilot-instructions.md` |
| `gemini` | Gemini CLI | `GEMINI.md` |

<details>
<summary><strong>24 more agents</strong> use the shared <code>AGENTS.md</code> standard — click to expand</summary>

<br>

`codex` · `cursor-agent` · `kimi` · `qwen` · `agy` · `trae` · `roo` ·
`bob` · `auggie` · `kilocode` · `windsurf` · `codebuddy` · `vibe` ·
`amp` · `kiro-cli` · `tabnine` · `goose` · `pi` · `opencode` ·
`forge` · `shai` · `iflow` · `junie` · `qodercli`

</details>

Run `devlog list` for the live registry.

<br>

## How it works

1. **`init`** drops a default `.devlog/config.yaml`, creates the blog
   skeleton, and scaffolds `.devlog/learned.md`.
2. **`install`** renders the config into a markdown block and writes it to
   the agent's context file between sentinel markers. Existing content is
   preserved; re-installing replaces only the section between the sentinels.
   A SHA-256 of the resulting file is saved to
   `.devlog/manifests/<agent>.manifest.json`.
3. **`uninstall`** strips the sentinel block and removes the manifest.

### Layout after install

```
your-project/
├── .devlog/
│   ├── config.yaml              # stable convention settings
│   ├── learned.md               # agent-maintained project notebook
│   └── manifests/
│       └── claude.manifest.json # install tracking
├── blog/
│   ├── _index.md
│   ├── 2026-04-16-first-entry.md
│   └── media/
└── CLAUDE.md                    # convention injected between sentinels
```

<br>

## Configuration

Edit `.devlog/config.yaml` to customize:

| Key | Purpose |
| --- | --- |
| `blog_dir` / `media_dir` / `index_file` | Where entries and media live. |
| `sections` | Headings each entry should have. |
| `voice` | Tone and audience guidelines baked into the convention. |
| `triggers` | When the agent should write an entry. |
| `tags` | Base tag vocabulary (auto-extended by discovery). |
| `frontmatter` | YAML frontmatter fields for each entry. |
| `media` | Screenshot/capture instructions. Set `enabled: false` to skip. |

Re-run `devlog install --ai <key>` after editing to regenerate the injected
section.

<br>

## License

MIT — see [LICENSE](LICENSE).
