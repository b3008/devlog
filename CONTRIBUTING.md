# Contributing to devlog

## Dev setup

```bash
git clone https://github.com/b3008/devlog.git
cd devlog
uv sync --group dev
```

This installs the package in editable mode along with pytest and ruff.

## Running tests

```bash
uv run pytest           # run the full suite
uv run pytest -x        # stop on first failure
uv run pytest -k hook   # run only tests matching "hook"
```

## Linting

```bash
uv run ruff check .     # lint
uv run ruff check . --fix  # lint + auto-fix
```

CI runs both `ruff check` and `pytest` on every PR. Both must pass to merge.

## Workflow

1. **Fork and clone** the repo.
2. **Create a branch** from `main`. Name it after what it does: `fix/tag-discovery`, `feature/stop-hook`, etc.
3. **Make your changes.** Add or update tests for anything that touches behavior.
4. **Run `uv run ruff check .` and `uv run pytest`** before pushing.
5. **Open a PR** against `main`. Fill in the PR template — summary, test plan.
6. CI will run automatically. Once checks pass, the PR can be merged.

`main` is protected: no direct pushes, no force-pushes, all changes go through PRs.

## Commit messages

- Use imperative mood: *"Add tag discovery"*, not *"Added tag discovery"*.
- First line under 72 characters.
- If needed, add a blank line then a longer explanation.
- Reference issues with `#N` when applicable.

## Project layout

```
src/devlog_cli/
├── __init__.py          # CLI commands (init, install, uninstall, status, list, version)
├── agents.py            # Agent registry (name → context file mapping)
├── convention.py        # Convention renderer, tag discovery, entry scanning
├── manifest.py          # Install manifest (SHA-256 tracking, hooks)
└── templates/
    ├── _index.md        # Blog index template
    ├── config.yaml      # Default config template
    ├── learned.md       # Agent-maintained project notebook template
    └── hooks/
        └── stop.py      # Claude Code Stop hook script

tests/                   # pytest test suite
.github/workflows/ci.yml # CI pipeline
```

## Adding a new agent

1. Add the entry to `agents.py` — either a dedicated `AgentConfig` with its own context file, or append to the `AGENTS.md` loop.
2. If the agent supports hooks, extend the hook installer in `__init__.py`.
3. Add a test in `tests/test_agents.py`.

## Adding a new template

1. Drop the file in `src/devlog_cli/templates/`.
2. `pyproject.toml` already includes `templates/**/*` in package data.
3. Wire it into the appropriate command in `__init__.py`.
