---
type: "Devlog Entry"
title: "OpenCode gets the full install surface"
date: 2026-07-16
timestamp: 2026-07-16T18:34:00
tags: [feature, cli, architecture]
description: "devlog install --ai opencode now ships custom commands into .opencode/commands/ and supports --global into ~/.config/opencode/ — driven by new capability fields on AgentConfig instead of key == 'claude' checks."
---

## What changed

OpenCode was one of the 24 undifferentiated `AGENTS.md` agents: `devlog install --ai opencode` injected the convention block and stopped there. It is now the second first-class integration after Claude Code:

- **Custom commands** — the four command templates (`/devlog-catchup`, `/devlog-write`, `/devlog-manicure`, `/devlog-upgrade`) install into `.opencode/commands/` on every opencode install, tracked in the manifest with the same hash-based customization detection.
- **`--global`** — `devlog install --ai opencode --global` injects the self-bootstrapping convention into `~/.config/opencode/AGENTS.md` and drops the commands into `~/.config/opencode/commands/`.
- **Thin local block** — a per-project install on top of a global opencode install now emits the thin pointer block, and the pointer text is agent-aware: it names `~/.config/opencode/AGENTS.md` and `devlog install --ai opencode --full`, not the claude paths.
- `devlog upgrade` resyncs *all* detected global installs, not just claude's; `devlog list` grew an Extras column showing which agents support commands/`--global`/hooks.

Hooks stay claude-only: opencode's extension mechanism is JS plugins, not settings.json command hooks, so `--with-hook` still errors for it — now with a capability-derived message instead of a hardcoded one.

## Why it matters

The interesting change isn't opencode itself — it's that the install pipeline no longer asks "is this claude?". `AgentConfig` gained three capability fields (`commands_dir`, `global_dir`, `supports_hooks`), and every `agent.key == "claude"` gate in install/uninstall/upgrade was replaced by a capability check. The third agent with markdown commands or a global config dir is now a three-line registry entry, not a code change. That matters because the command-format convergence is real: opencode consumed our claude command templates *verbatim* — same `description` frontmatter, same `$ARGUMENTS` placeholder — so the per-agent cost of shipping the authoring loop is approaching zero.

## How it works

The registry entry is the whole integration:

```python
_reg(AgentConfig(
    key="opencode",
    name="OpenCode",
    context_file="AGENTS.md",
    commands_dir=".opencode/commands",
    global_dir=".config/opencode",
))
```

`_install_claude_commands` became `_install_agent_commands(root_dir, commands_dir_rel, previous)` — the destination is a parameter; all the reconciliation logic (orphan removal, customization preservation, passthrough-on-missing-templates) carried over untouched. Global paths derive from `global_dir`: context at `~/{global_dir}/{context_file}`, commands at `~/{global_dir}/commands` — which happens to unify claude (`~/.claude/commands`) and opencode (`~/.config/opencode/commands`) under one rule. `generate_thin_convention()` takes `agent_key` and `global_context_path` so the pointer block names the right file. The legacy `~/CLAUDE.md` migration sweep is explicitly gated to claude — a sentinel block found at `~/AGENTS.md` isn't necessarily ours to delete.

End-to-end against a scratch `$HOME`:

```
Installing devlog convention — OpenCode
├── Injected convention into AGENTS.md
├── Installed slash command /devlog-catchup (.opencode/commands/devlog-catchup.md)
├── Installed slash command /devlog-manicure (.opencode/commands/devlog-manicure.md)
├── Installed slash command /devlog-upgrade (.opencode/commands/devlog-upgrade.md)
├── Installed slash command /devlog-write (.opencode/commands/devlog-write.md)
└── Manifest saved
```

14 new tests cover the opencode paths (local commands, global install/uninstall, thin block, `--with-hook` rejection, `--global` rejection for plain AGENTS.md agents); 190 pass total.

## What's next

- The other AGENTS.md agents with command directories (codex, cursor-agent, goose, …) are now each a registry-entry away — worth adding as their formats are verified against real docs, not assumed.
- An opencode plugin equivalent of the Stop hook is possible (`.opencode/plugin/` JS, session-idle events) but unbuilt; same build-only-if-coverage-data-demands-it bar as the hybrid hook thread.
- README and the `devlog-upgrade` command template were reworded from "the global Claude install" to agent-agnostic phrasing.

## Surprises

The opencode docs page was fetched twice because the first summary said `.opencode/commands/` (plural) while memory said `command` (singular) — a second fetch quoting exact strings confirmed the plural. Worth the paranoia: this string decides where files land in every user's repo. The reverse surprise was how little translation the templates needed — zero: opencode's command format is a strict subset match of what we already ship (markdown body + `description` + `$ARGUMENTS`), so "add opencode support" reduced to threading paths through functions that already existed.
