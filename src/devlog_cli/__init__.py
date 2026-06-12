"""
devlog — Installable development blog convention for AI coding agents.

Scaffolds a blog directory and injects blogging instructions into
agent context files (CLAUDE.md, AGENTS.md, etc.) so AI assistants
automatically maintain a development blog.

Usage:
    uvx --from git+https://github.com/b3008/devlog.git devlog init
    uvx --from git+https://github.com/b3008/devlog.git devlog install --ai claude
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from devlog_cli._version import __version__
from devlog_cli.agents import AGENTS, AgentConfig, get_agent
from devlog_cli.convention import (
    _SENTINEL_START_MARKER,
    build_index,
    discover_tags,
    generate_convention,
    generate_thin_convention,
    inject_convention,
    load_config,
    remove_convention,
    scan_entries,
    sentinel_version,
)
from devlog_cli.manifest import Manifest

LOGO = """\
[bold cyan]  ██▀▄ █▀▀ █ █ █   ▄▀▄ ▄▀▀[/]
[bold cyan]  █  █ █▀  ▀▄▀ █   █ █ █ █[/]
[bold cyan]  ▀▀   ▀▀▀  ▀  ▀▀▀  ▀  ▀▀▀[/]"""

app = typer.Typer(
    name="devlog",
    help="Development blog convention installer for AI coding agents.",
    no_args_is_help=True,
)
console = Console()


# ── Init command ─────────────────────────────────────────────────────────


@app.command()
def init(
    project_name: Optional[str] = typer.Option(
        None, "--name", "-n", help="Project name for the blog index title."
    ),
) -> None:
    """Initialize the blog directory structure and devlog config."""
    project_root = Path.cwd()
    if not project_name:
        project_name = project_root.name

    tree = Tree(f"[bold green]Initializing devlog[/bold green] — {project_name}")

    # .devlog/ config directory
    devlog_dir = project_root / ".devlog"
    devlog_dir.mkdir(exist_ok=True)

    # Copy default config if it doesn't exist
    config_path = devlog_dir / "config.yaml"
    if not config_path.exists():
        src = _templates_dir() / "config.yaml"
        shutil.copy2(src, config_path)
        tree.add("[green]Created .devlog/config.yaml[/green]")
    else:
        tree.add("[dim].devlog/config.yaml already exists[/dim]")

    # Load config (may have been customized)
    config = load_config(project_root)
    blog_dir = project_root / config["blog_dir"]
    media_dir = project_root / config["media_dir"]

    # blog/ directory
    blog_dir.mkdir(exist_ok=True)
    tree.add(f"[green]Created {config['blog_dir']}/[/green]")

    # blog/media/ directory
    media_dir.mkdir(parents=True, exist_ok=True)
    tree.add(f"[green]Created {config['media_dir']}/[/green]")

    # blog/_index.md
    index_file = blog_dir / config.get("index_file", "_index.md")
    if not index_file.exists():
        template = (_templates_dir() / "_index.md").read_text(encoding="utf-8")
        content = template.replace("{project_name}", project_name)
        index_file.write_text(content, encoding="utf-8")
        tree.add(f"[green]Created {config['blog_dir']}/{index_file.name}[/green]")
    else:
        tree.add(f"[dim]{config['blog_dir']}/{index_file.name} already exists[/dim]")

    # .devlog/learned.md — agent-maintained project knowledge
    learned_path = devlog_dir / "learned.md"
    if not learned_path.exists():
        src = _templates_dir() / "learned.md"
        shutil.copy2(src, learned_path)
        tree.add("[green]Created .devlog/learned.md[/green]")
    else:
        tree.add("[dim].devlog/learned.md already exists[/dim]")

    console.print()
    console.print(tree)
    console.print()
    console.print(Panel(
        f"[bold]Blog directory:[/bold] {config['blog_dir']}/\n"
        f"[bold]Config:[/bold]         .devlog/config.yaml\n"
        f"\n"
        f"[bold]Next:[/bold] Run [cyan]devlog install --ai claude[/cyan] to inject the convention\n"
        f"      into your agent's context file.",
        title="[bold green]devlog initialized[/bold green]",
        border_style="green",
    ))


# ── Install command ──────────────────────────────────────────────────────


@app.command()
def install(
    ai: str = typer.Option(..., "--ai", help="AI agent key (e.g. claude, copilot, gemini)."),
    with_hook: bool = typer.Option(
        False,
        "--with-hook",
        help="(claude only) Also install a Stop hook that reminds the agent to check for blog-worthy turns.",
    ),
    global_: bool = typer.Option(
        False,
        "--global",
        help="(claude only) Install into ~/.claude/ so the convention applies to every project.",
    ),
    full: bool = typer.Option(
        False,
        "--full",
        help="Inject the full convention even when a global install is detected "
        "(useful for repos shared with collaborators who lack the global install).",
    ),
) -> None:
    """Inject the blog convention into an agent's context file."""
    try:
        agent = get_agent(ai)
    except KeyError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    if (with_hook or global_) and ai != "claude":
        flag = "--global" if global_ else "--with-hook"
        console.print(f"[red]{flag} is only supported for the 'claude' agent right now (got {ai!r}).[/red]")
        raise typer.Exit(1)

    if global_:
        _install_global(agent, with_hook=with_hook)
    else:
        _install_local(agent, with_hook=with_hook, full=full)


def _install_local(agent: AgentConfig, *, with_hook: bool, full: bool = False) -> None:
    """Per-project install: inject convention into the project's context file."""
    project_root = Path.cwd()

    # Check if devlog is initialized
    config_path = project_root / ".devlog" / "config.yaml"
    if not config_path.exists():
        console.print("[yellow]devlog not initialized. Running init first...[/yellow]")
        console.print()
        init(project_name=None)
        console.print()

    # Check for existing manifest
    manifest_path = project_root / ".devlog" / "manifests" / f"{agent.key}.manifest.json"
    if manifest_path.exists():
        console.print(f"[yellow]{agent.name} convention already installed. Reinstalling...[/yellow]")

    config = load_config(project_root)

    # Ensure learned.md exists (covers upgrades from pre-learned.md installs)
    learned_path = project_root / ".devlog" / "learned.md"
    if not learned_path.exists():
        shutil.copy2(_templates_dir() / "learned.md", learned_path)

    # Fold tags discovered in existing entries into the rendered vocabulary
    base_tags = set(config["tags"])
    discovered = set(discover_tags(project_root, config))
    new_tags = sorted(discovered - base_tags)
    if discovered:
        config["tags"] = sorted(base_tags | discovered)

    # When the full convention is already injected globally, drop a thin
    # pointer block instead of duplicating ~1.5k tokens in every session.
    thin = agent.key == "claude" and not full and _global_install_detected(agent)
    convention_text = (
        generate_thin_convention(config) if thin else generate_convention(config)
    )
    manifest = Manifest(agent_key=agent.key, project_root=project_root, version=__version__)
    previous_manifest = Manifest.load(manifest_path, project_root) if manifest_path.exists() else None

    tree = Tree(f"[bold green]Installing devlog convention[/bold green] — {agent.name}")
    if thin:
        tree.add(
            "[green]Global install detected — using the thin project block[/green] "
            "([dim]re-run with --full for the standalone convention[/dim])"
        )
    if new_tags:
        tree.add(f"[green]Discovered {len(new_tags)} new tag(s) from entries: {', '.join(new_tags)}[/green]")

    # Inject into context file
    ctx_path = project_root / agent.context_file
    if ctx_path.exists():
        existing = ctx_path.read_text(encoding="utf-8")
        new_content = inject_convention(existing, convention_text)
    else:
        new_content = inject_convention("", convention_text)

    ctx_path.parent.mkdir(parents=True, exist_ok=True)
    ctx_path.write_text(new_content, encoding="utf-8")
    manifest.files[agent.context_file] = Manifest._sha256(new_content)
    tree.add(f"[green]Injected convention into {agent.context_file}[/green]")

    # Install Claude Code slash commands (default-on for claude installs).
    if agent.key == "claude":
        prev_commands = previous_manifest.commands if previous_manifest else []
        records, preserved, orphans = _install_claude_commands(project_root, prev_commands)
        for cmd_record in records:
            manifest.commands.append(cmd_record)
            if cmd_record["name"] in preserved:
                tree.add(
                    f"[yellow]Preserved customized slash command[/yellow] "
                    f"[cyan]/{cmd_record['name']}[/cyan] "
                    f"([dim]{cmd_record['path']} \u2014 local edits kept[/dim])"
                )
            else:
                tree.add(
                    f"[green]Installed slash command[/green] "
                    f"[cyan]/{cmd_record['name']}[/cyan] "
                    f"([dim]{cmd_record['path']}[/dim])"
                )
        for rel in orphans:
            tree.add(f"[yellow]Removed orphaned slash command[/yellow] [dim]{rel}[/dim]")

    # Install the Claude Code hooks \u2014 when requested, or carried forward
    # from a previous install.
    if agent.key == "claude":
        _install_claude_hooks(project_root, previous_manifest, with_hook, tree, manifest)

    manifest.save()
    tree.add("[dim]Manifest saved[/dim]")

    console.print()
    console.print(tree)
    console.print()
    console.print(
        f"[green]Done.[/green] {agent.name} will now maintain a development blog "
        f"in [cyan]{config['blog_dir']}/[/cyan]."
    )
    if not manifest.hooks and agent.key == "claude":
        console.print(
            "[dim]Tip: re-run with [cyan]--with-hook[/cyan] to also install a Claude Code "
            "Stop hook that nudges the agent before each turn ends.[/dim]"
        )


def _install_global(agent: AgentConfig, *, with_hook: bool) -> None:
    """Global install: inject convention into ~/.claude/CLAUDE.md so it applies to every project."""
    from devlog_cli.convention import DEFAULT_CONFIG

    home = Path.home()
    config = dict(DEFAULT_CONFIG)
    convention_text = generate_convention(config, global_mode=True)

    manifest = Manifest(agent_key=agent.key, project_root=home, version=__version__)
    previous_manifest = (
        Manifest.load(manifest.manifest_path, home) if manifest.manifest_path.exists() else None
    )

    # Check for existing global manifest
    if previous_manifest is not None:
        console.print(f"[yellow]{agent.name} global convention already installed. Reinstalling...[/yellow]")

    tree = Tree(f"[bold green]Installing devlog convention (global)[/bold green] — {agent.name}")

    # Inject into ~/.claude/CLAUDE.md
    ctx_rel = f"{GLOBAL_CONTEXT_DIR_REL}/{agent.context_file}"
    ctx_path = home / ctx_rel
    if ctx_path.exists():
        existing = ctx_path.read_text(encoding="utf-8")
        new_content = inject_convention(existing, convention_text)
    else:
        new_content = inject_convention("", convention_text)

    ctx_path.parent.mkdir(parents=True, exist_ok=True)
    ctx_path.write_text(new_content, encoding="utf-8")
    manifest.files[ctx_rel] = Manifest._sha256(new_content)
    tree.add(f"[green]Injected convention into ~/{ctx_rel}[/green]")

    # Migrate away from the legacy global location (~/CLAUDE.md). Earlier
    # versions wrote the convention there, where it loads via ancestor
    # traversal rather than as true user memory — and double-injects once
    # the new location exists.
    legacy_path = home / agent.context_file
    if legacy_path != ctx_path and legacy_path.exists():
        try:
            legacy_content = legacy_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            legacy_content = None
        if legacy_content and _SENTINEL_START_MARKER in legacy_content:
            cleaned = remove_convention(legacy_content)
            if cleaned.strip():
                legacy_path.write_text(cleaned, encoding="utf-8")
                tree.add(
                    f"[yellow]Migrated: removed convention from legacy ~/{agent.context_file}[/yellow]"
                )
            else:
                legacy_path.unlink()
                tree.add(
                    f"[yellow]Migrated: removed legacy ~/{agent.context_file} (was devlog-only)[/yellow]"
                )

    # Install Claude Code slash commands globally (default-on for claude installs).
    if agent.key == "claude":
        prev_commands = previous_manifest.commands if previous_manifest else []
        records, preserved, orphans = _install_claude_commands(home, prev_commands)
        for cmd_record in records:
            manifest.commands.append(cmd_record)
            if cmd_record["name"] in preserved:
                tree.add(
                    f"[yellow]Preserved customized global slash command[/yellow] "
                    f"[cyan]/{cmd_record['name']}[/cyan] "
                    f"([dim]~/{cmd_record['path']} — local edits kept[/dim])"
                )
            else:
                tree.add(
                    f"[green]Installed global slash command[/green] "
                    f"[cyan]/{cmd_record['name']}[/cyan] "
                    f"([dim]~/{cmd_record['path']}[/dim])"
                )
        for rel in orphans:
            tree.add(f"[yellow]Removed orphaned global slash command[/yellow] [dim]~/{rel}[/dim]")

    # Install the global hooks \u2014 when requested, or carried forward from a
    # previous install.
    _install_claude_hooks(
        home, previous_manifest, with_hook, tree, manifest, global_mode=True, display_prefix="~/"
    )

    manifest.save()
    tree.add("[dim]Manifest saved[/dim]")

    console.print()
    console.print(tree)
    console.print()
    console.print(
        "[green]Done.[/green] Every project will now get a development blog.\n"
        "[dim]Per-project customization: run [cyan]devlog init[/cyan] in any project to drop a "
        ".devlog/config.yaml with custom triggers, voice, and tags.[/dim]"
    )
    if not manifest.hooks:
        console.print(
            "[dim]Tip: re-run with [cyan]--with-hook[/cyan] to also install a global Stop hook.[/dim]"
        )


# ── Uninstall command ────────────────────────────────────────────────────


@app.command()
def uninstall(
    ai: str = typer.Option(..., "--ai", help="AI agent key to remove convention from."),
    global_: bool = typer.Option(
        False,
        "--global",
        help="(claude only) Remove the global convention from ~/.claude/.",
    ),
) -> None:
    """Remove the blog convention from an agent's context file."""
    try:
        agent = get_agent(ai)
    except KeyError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    if global_ and ai != "claude":
        console.print(f"[red]--global is only supported for 'claude' right now (got {ai!r}).[/red]")
        raise typer.Exit(1)

    root_dir = Path.home() if global_ else Path.cwd()
    ctx_display_prefix = "~/" if global_ else ""

    manifest_path = root_dir / ".devlog" / "manifests" / f"{ai}.manifest.json"
    if not manifest_path.exists():
        scope = "global " if global_ else ""
        console.print(f"[red]No {scope}manifest found for {agent.name}. Not installed?[/red]")
        raise typer.Exit(1)

    manifest = Manifest.load(manifest_path, root_dir)

    # Remove convention from context file. Global installs live under
    # ~/.claude/; also sweep the legacy home-root location from old versions.
    primary_rel = (
        f"{GLOBAL_CONTEXT_DIR_REL}/{agent.context_file}" if global_ else agent.context_file
    )
    _remove_convention_from(root_dir / primary_rel, f"{ctx_display_prefix}{primary_rel}")
    if global_:
        # Sweep the legacy home-root location from old versions too.
        _remove_convention_from(
            root_dir / agent.context_file,
            f"{ctx_display_prefix}{agent.context_file}",
            quiet_if_absent=True,
        )

    # Remove any installed hooks recorded in the manifest
    if manifest is not None and ai == "claude":
        for hook in manifest.hooks:
            for action in _uninstall_claude_hook(root_dir, hook):
                console.print(f"[green]{action}[/green]")

    # Remove any installed slash commands recorded in the manifest
    if manifest is not None:
        for cmd in manifest.commands:
            for action in _uninstall_claude_command(root_dir, cmd):
                console.print(f"[green]{action}[/green]")

    # Clean up manifest
    if manifest_path.exists():
        manifest_path.unlink()
        parent = manifest_path.parent
        while parent != root_dir and parent.exists():
            try:
                if any(parent.iterdir()):
                    break
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    scope = "global " if global_ else ""
    console.print(f"[green]Done. {agent.name} {scope}convention uninstalled.[/green]")


# ── List command ─────────────────────────────────────────────────────────


@app.command("list")
def list_agents() -> None:
    """List all available AI agent integrations."""
    table = Table(title="Available Agents")
    table.add_column("Key", style="cyan")
    table.add_column("Name")
    table.add_column("Context File", style="dim")

    # Group by context file for cleaner display
    for cfg in sorted(AGENTS.values(), key=lambda c: (c.context_file, c.name)):
        table.add_row(cfg.key, cfg.name, cfg.context_file)

    console.print(table)


# ── Status command ───────────────────────────────────────────────────────


@app.command()
def status() -> None:
    """Show which agents have the blog convention installed and whether entries are being written."""
    project_root = Path.cwd()
    manifests_dir = project_root / ".devlog" / "manifests"

    if not manifests_dir.exists():
        console.print("[yellow]No agents installed. Run [cyan]devlog install --ai <agent>[/cyan] first.[/yellow]")
        raise typer.Exit(0)

    manifest_files = sorted(manifests_dir.glob("*.manifest.json"))
    if not manifest_files:
        console.print("[yellow]No agents installed.[/yellow]")
        raise typer.Exit(0)

    config = load_config(project_root)
    entry_count, latest_entry = scan_entries(project_root, config)
    blog_dir = config["blog_dir"]

    # Blog summary line
    if entry_count == 0:
        console.print(f"[bold]Blog:[/bold] [cyan]{blog_dir}/[/cyan] \u2014 [yellow]no entries yet[/yellow]")
    else:
        noun = "entry" if entry_count == 1 else "entries"
        console.print(
            f"[bold]Blog:[/bold] [cyan]{blog_dir}/[/cyan] \u2014 "
            f"{entry_count} {noun}, most recent [green]{latest_entry}[/green]"
        )

    # Session coverage, recorded by the SessionEnd hook when installed.
    # Sessions newer than the latest entry are the convention's blind spot:
    # work may have happened there without leaving a trace in the blog.
    total_sessions, last_session, since_entry = _read_session_log(project_root, latest_entry)
    if total_sessions:
        line = f"[bold]Sessions:[/bold] {total_sessions} recorded"
        if last_session:
            line += f", last [green]{last_session}[/green]"
        if since_entry:
            line += f" \u2014 [yellow]{since_entry} since the last entry[/yellow]"
        console.print(line)
    console.print()

    table = Table(title="Installed Conventions")
    table.add_column("Agent", style="cyan")
    table.add_column("Context File", style="dim")
    table.add_column("Status")
    table.add_column("Version", style="dim")
    table.add_column("Installed", style="dim")

    earliest_install: Optional[datetime] = None
    drift_warnings: list[str] = []
    for mf in manifest_files:
        manifest = Manifest.load(mf, project_root)
        if manifest is None:
            continue
        agent_key = manifest.agent_key
        try:
            agent = get_agent(agent_key)
        except KeyError:
            continue

        ctx_path = project_root / agent.context_file
        ctx_text: Optional[str] = None
        if ctx_path.exists():
            try:
                ctx_text = ctx_path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                ctx_text = None
        block_present = bool(ctx_text) and _SENTINEL_START_MARKER in ctx_text
        status_text = "[green]active[/green]" if block_present else "[red]missing[/red]"

        installed_display = "\u2014"
        if manifest.installed_at:
            try:
                dt = datetime.fromisoformat(manifest.installed_at.replace("Z", "+00:00"))
                installed_display = dt.strftime("%Y-%m-%d")
                if earliest_install is None or dt < earliest_install:
                    earliest_install = dt
            except ValueError:
                pass

        # Drift: anything a reinstall would change. A manifest or stamp from a
        # NEWER devlog than the running tool flips the advice — resyncing
        # there would downgrade templates, so the fix is upgrading the tool.
        issues: list[str] = []
        upgrade_tool = False
        mine = _version_tuple(__version__)
        if manifest.version != __version__:
            theirs = _version_tuple(manifest.version)
            if mine is not None and theirs is not None and theirs > mine:
                issues.append(
                    f"installed by devlog {manifest.version}, newer than this tool ({__version__})"
                )
                upgrade_tool = True
            else:
                issues.append(f"installed by devlog {manifest.version}, current is {__version__}")
        if block_present:
            stamp = sentinel_version(ctx_text)
            if stamp is None:
                issues.append("convention block predates the version stamp")
            elif stamp != __version__:
                issues.append(f"convention block is from v{stamp}")
                stamped = _version_tuple(stamp)
                if mine is not None and stamped is not None and stamped > mine:
                    upgrade_tool = True
        missing_hash, mismatched = _count_stale_artifacts(manifest)
        if mismatched:
            noun = "artifact differs" if mismatched == 1 else "artifacts differ"
            issues.append(f"{mismatched} installed {noun} from the current templates")
        if missing_hash:
            noun = "artifact lacks" if missing_hash == 1 else "artifacts lack"
            issues.append(f"{missing_hash} installed {noun} a recorded hash (pre-0.2.0 install)")
        if issues:
            if upgrade_tool:
                hint = (
                    "This tool is older than the install — a reinstall would downgrade; "
                    "upgrade devlog first (e.g. [cyan]uv tool upgrade devlog[/cyan])."
                )
            else:
                hint = (
                    f"Run [cyan]devlog install --ai {agent_key}[/cyan] to resync "
                    "(customized files are preserved)."
                )
            drift_warnings.append(
                f"[yellow]{agent.name}:[/yellow] " + "; ".join(issues) + ". " + hint
            )

        table.add_row(
            agent.name, agent.context_file, status_text, manifest.version or "\u2014", installed_display
        )

    console.print(table)
    for warning in drift_warnings:
        console.print()
        console.print(warning)

    # Warn if the convention may not be firing
    if earliest_install is not None and entry_count == 0:
        days = (datetime.now(timezone.utc) - earliest_install).days
        if days >= 1:
            console.print()
            console.print(Panel(
                f"No entries written since install ({days} day{'s' if days != 1 else ''} ago).\n"
                f"The convention may not be firing. Things to try:\n"
                f"  \u2022 Start a fresh agent session (context files are usually read at session start).\n"
                f"  \u2022 Nudge the agent: [cyan]\"check if this session warrants"
                f" a devlog entry and write one if so\"[/cyan]\n"
                f"  \u2022 If the defaults don't fit your project, edit"
                f" [cyan].devlog/config.yaml[/cyan] and re-run install.",
                title="[yellow]Warning[/yellow]",
                border_style="yellow",
            ))


# ── Index command ────────────────────────────────────────────────────────


@app.command()
def index() -> None:
    """Regenerate the blog index from entry frontmatter (newest first)."""
    project_root = Path.cwd()
    config = load_config(project_root)
    blog_dir = project_root / config["blog_dir"]
    if not blog_dir.is_dir():
        console.print(
            f"[red]No {config['blog_dir']}/ directory here. Run [cyan]devlog init[/cyan] first.[/red]"
        )
        raise typer.Exit(1)

    content, count = build_index(project_root, config)
    index_path = blog_dir / config.get("index_file", "_index.md")
    index_path.write_text(content, encoding="utf-8")
    noun = "entry" if count == 1 else "entries"
    console.print(
        f"[green]Regenerated {config['blog_dir']}/{index_path.name}[/green] — {count} {noun}."
    )


# ── Version command ──────────────────────────────────────────────────────


@app.command()
def version() -> None:
    """Display version information."""
    console.print(LOGO)
    console.print(f"  devlog {__version__}")
    console.print()


# ── Helpers ──────────────────────────────────────────────────────────────


def _templates_dir() -> Path:
    """Find the bundled templates directory."""
    return Path(__file__).parent / "templates"


def _read_session_log(
    project_root: Path, latest_entry: str | None
) -> tuple[int, str | None, int]:
    """Summarize .devlog/sessions.jsonl (written by the SessionEnd hook).

    Returns ``(total, last_session_date, sessions_since_latest_entry)``;
    ``(0, None, 0)`` when the log is absent or unreadable."""
    sessions_path = project_root / ".devlog" / "sessions.jsonl"
    if not sessions_path.exists():
        return 0, None, 0
    total = 0
    last_ts: str | None = None
    since_entry = 0
    try:
        # Stream rather than read_text(): the log grows one line per session
        # for the life of the project.
        with sessions_path.open(encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(rec, dict):
                    continue
                total += 1
                ts = str(rec.get("ts") or "")
                if ts and (last_ts is None or ts > last_ts):
                    last_ts = ts
                if latest_entry and ts[:10] > latest_entry:
                    since_entry += 1
    except (OSError, UnicodeDecodeError):
        return 0, None, 0
    return total, (last_ts[:10] if last_ts else None), since_entry


def _version_tuple(version: str) -> tuple[int, ...] | None:
    """Parse 'X.Y.Z' into a comparable tuple; None when unparseable."""
    try:
        return tuple(int(part) for part in str(version).strip().split("."))
    except ValueError:
        return None


def _count_stale_artifacts(manifest: Manifest) -> tuple[int, int]:
    """Classify installed artifacts against the templates this version ships.

    Returns ``(missing_hash, mismatched)`` — records with no recorded hash
    (pre-0.2.0 installs: unverifiable, not necessarily different) and records
    whose recorded hash differs from the current template (what a reinstall
    would refresh; includes user-customized files, which reinstall preserves)."""
    missing = 0
    mismatched = 0

    def check(record_hash: str | None, template: Path) -> None:
        nonlocal missing, mismatched
        template_hash = _safe_file_hash(template)
        if not template_hash:
            return
        if not record_hash:
            missing += 1
        elif record_hash != template_hash:
            mismatched += 1

    for cmd in manifest.commands:
        name = cmd.get("name")
        if name:
            check(cmd.get("sha256"), _templates_dir() / "commands" / f"{name}.md")
    for hook in manifest.hooks:
        rel = hook.get("script_path")
        if rel:
            check(hook.get("sha256"), _templates_dir() / "hooks" / Path(rel).name)
    return missing, mismatched


def _global_install_detected(agent: AgentConfig) -> bool:
    """True when a devlog global install for this agent is present and its
    convention block is actually in place (manifest alone isn't enough — the
    user may have removed the file)."""
    home = Path.home()
    manifest_path = home / ".devlog" / "manifests" / f"{agent.key}.manifest.json"
    if not manifest_path.exists():
        return False
    candidates = (
        home / GLOBAL_CONTEXT_DIR_REL / agent.context_file,
        home / agent.context_file,  # legacy pre-migration location
    )
    for path in candidates:
        try:
            if path.exists() and _SENTINEL_START_MARKER in path.read_text(encoding="utf-8"):
                return True
        except (OSError, UnicodeDecodeError):
            continue
    return False


def _remove_convention_from(ctx_path: Path, display: str, *, quiet_if_absent: bool = False) -> None:
    """Strip the devlog sentinel block from a context file, deleting the file
    if nothing else remains. quiet_if_absent suppresses noise when sweeping
    locations that legitimately may not exist (e.g. legacy paths)."""
    if not ctx_path.exists():
        if not quiet_if_absent:
            console.print(f"[yellow]{display} not found[/yellow]")
        return
    try:
        content = ctx_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        console.print(f"[yellow]Could not read {display}; left untouched[/yellow]")
        return
    if _SENTINEL_START_MARKER not in content:
        if not quiet_if_absent:
            console.print(f"[yellow]No devlog section found in {display}[/yellow]")
        return
    new_content = remove_convention(content)
    if new_content.strip():
        ctx_path.write_text(new_content, encoding="utf-8")
        console.print(f"[green]Removed convention from {display}[/green]")
    else:
        ctx_path.unlink()
        console.print(f"[green]Removed {display} (was empty after removal)[/green]")


# ── Claude Code Stop hook helpers ────────────────────────────────────────

CLAUDE_SETTINGS_REL = ".claude/settings.json"
# Global installs write the convention under ~/.claude/ (Claude Code's user
# memory), not the home directory root (which only loads via ancestor traversal).
GLOBAL_CONTEXT_DIR_REL = ".claude"
STOP_HOOK_SCRIPT_REL = ".devlog/hooks/stop.py"
SESSION_HOOK_SCRIPT_REL = ".devlog/hooks/session_end.py"
# The (event, script) pairs that --with-hook installs: the Stop reminder and
# the SessionEnd coverage recorder.
CLAUDE_HOOKS: list[tuple[str, str]] = [
    ("Stop", STOP_HOOK_SCRIPT_REL),
    ("SessionEnd", SESSION_HOOK_SCRIPT_REL),
]


def _hook_command(script_rel: str, *, global_mode: bool) -> str:
    var = "$HOME" if global_mode else "$CLAUDE_PROJECT_DIR"
    return f'python3 "{var}/{script_rel}"'


def _install_claude_hook(
    root_dir: Path,
    event: str,
    script_rel: str,
    previous: dict[str, Any] | None = None,
    *,
    global_mode: bool = False,
) -> tuple[dict[str, Any], bool]:
    """Copy a hook script and register it under `event` in settings.json.

    root_dir is the project root (per-project) or Path.home() (global).
    `previous` is the prior manifest's record for this event, used to detect
    user customizations of the script (mirroring slash-command handling).

    Returns ``(record, preserved)`` — the manifest record, and whether an
    existing customized script was left untouched instead of overwritten.
    """
    command = _hook_command(script_rel, global_mode=global_mode)

    # 1. Copy the hook script — unless the user customized it since install.
    src = _templates_dir() / "hooks" / Path(script_rel).name
    new_hash = Manifest._sha256(src.read_text(encoding="utf-8"))
    script_dst = root_dir / script_rel
    script_dst.parent.mkdir(parents=True, exist_ok=True)

    preserved = False
    record_hash = new_hash
    prev_hash = (previous or {}).get("sha256")
    if script_dst.exists() and prev_hash:
        current_hash = _safe_file_hash(script_dst)
        if current_hash and current_hash != prev_hash and current_hash != new_hash:
            # User edited the script since install — keep their version.
            preserved = True
            record_hash = current_hash
        # current_hash is None → unreadable; fall through and overwrite from
        # the template rather than aborting the install.
    # When the previous record carries no sha256 (pre-hashing manifests) we
    # deliberately overwrite on reinstall: an old template and a user edit are
    # indistinguishable, and preserving-when-unsure would permanently pin
    # stale scripts (e.g. the pre-exit-0 Stop hook) on every legacy install.
    # One reinstall migrates the manifest to hashed records; edits made after
    # that are detected and preserved. Uninstall makes the opposite call —
    # see _uninstall_claude_hook — because deletion is unrecoverable while
    # overwriting-from-template at least leaves a working hook.
    if not preserved:
        shutil.copy2(src, script_dst)
        script_dst.chmod(0o755)

    # 2. Merge the hook entry into settings.json (preserving existing config).
    settings_path = root_dir / CLAUDE_SETTINGS_REL
    settings: dict[str, Any] = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8")) or {}
        except json.JSONDecodeError as exc:
            settings_rel = f"~/{CLAUDE_SETTINGS_REL}" if global_mode else CLAUDE_SETTINGS_REL
            console.print(
                f"[red]Could not parse {settings_rel}: {exc}[/red]\n"
                "[red]Refusing to overwrite. Fix the file and re-run install.[/red]"
            )
            raise typer.Exit(1)

    hooks_root = settings.setdefault("hooks", {})
    event_entries: list[dict[str, Any]] = hooks_root.setdefault(event, [])

    # Strip any prior devlog-installed entry for this event so reinstalls are
    # idempotent.
    event_entries[:] = [e for e in event_entries if not _is_devlog_hook_entry(e, script_rel)]

    event_entries.append({
        "hooks": [
            {"type": "command", "command": command}
        ]
    })

    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return {
        "event": event,
        "settings_path": CLAUDE_SETTINGS_REL,
        "script_path": script_rel,
        "command": command,
        "sha256": record_hash,
    }, preserved


def _install_claude_hooks(
    root_dir: Path,
    previous_manifest: Optional[Manifest],
    with_hook: bool,
    tree: Tree,
    manifest: Manifest,
    *,
    global_mode: bool = False,
    display_prefix: str = "",
) -> None:
    """Install the devlog hook bundle when requested (--with-hook) or carried
    forward from a previous install. A reinstall without --with-hook must not
    orphan hooks that settings.json still points at; refreshing also resyncs
    stale scripts."""
    prev_hooks = previous_manifest.hooks if previous_manifest else []
    if not (with_hook or prev_hooks):
        return
    for event, script_rel in CLAUDE_HOOKS:
        prev = next((h for h in prev_hooks if h.get("event") == event), None)
        hook_record, preserved = _install_claude_hook(
            root_dir, event, script_rel, prev, global_mode=global_mode
        )
        manifest.hooks.append(hook_record)
        carried = not with_hook and prev is not None
        _add_hook_tree_line(
            tree, hook_record, preserved, carried=carried, display_prefix=display_prefix
        )


def _add_hook_tree_line(
    tree: Tree,
    hook_record: dict[str, Any],
    preserved: bool,
    *,
    carried: bool,
    display_prefix: str = "",
) -> None:
    """Report what happened to a hook during install."""
    event = hook_record.get("event", "")
    paths = (
        f"[dim]{display_prefix}{hook_record['script_path']} → "
        f"{display_prefix}{hook_record['settings_path']}[/dim]"
    )
    if preserved:
        tree.add(
            f"[yellow]Preserved customized {event} hook script[/yellow] ({paths} — local edits kept)"
        )
    elif carried:
        tree.add(f"[green]Refreshed existing {event} hook[/green] ({paths})")
    else:
        tree.add(f"[green]Installed {event} hook[/green] ({paths})")


def _is_devlog_hook_entry(entry: dict[str, Any], script_rel: str) -> bool:
    """Detect a hook entry installed by devlog by matching the script path
    in any of its commands."""
    for h in entry.get("hooks", []):
        if h.get("type") == "command" and script_rel in h.get("command", ""):
            return True
    return False


def _uninstall_claude_hook(project_root: Path, hook_record: dict[str, Any]) -> list[str]:
    """Remove a previously-installed hook. Returns a list of human-readable
    actions taken (for display)."""
    actions: list[str] = []
    event = hook_record.get("event", "Stop")
    script_rel = hook_record.get("script_path", STOP_HOOK_SCRIPT_REL)

    settings_path = project_root / hook_record.get("settings_path", CLAUDE_SETTINGS_REL)
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8")) or {}
        except json.JSONDecodeError:
            settings = None

        if isinstance(settings, dict):
            event_entries = settings.get("hooks", {}).get(event, [])
            before = len(event_entries)
            event_entries[:] = [e for e in event_entries if not _is_devlog_hook_entry(e, script_rel)]
            if len(event_entries) < before:
                # Clean up empty containers so settings.json stays tidy.
                if not event_entries:
                    settings["hooks"].pop(event, None)
                if not settings.get("hooks"):
                    settings.pop("hooks", None)

                if settings:
                    settings_path.write_text(
                        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8",
                    )
                    actions.append(f"Removed {event} hook from {hook_record['settings_path']}")
                else:
                    settings_path.unlink()
                    actions.append(f"Removed empty {hook_record['settings_path']}")

    script_path = project_root / hook_record.get("script_path", STOP_HOOK_SCRIPT_REL)
    if script_path.exists():
        # Only delete a script we can positively identify as devlog's: it must
        # match the recorded install hash, or — for pre-hashing manifests that
        # recorded none — the currently shipped template. Anything else may
        # carry user edits; an unregistered leftover script is inert, a deleted
        # customization is unrecoverable.
        reference_hash = hook_record.get("sha256") or _safe_file_hash(
            _templates_dir() / "hooks" / script_path.name
        )
        current_hash = _safe_file_hash(script_path)
        if reference_hash is None or current_hash is None or current_hash != reference_hash:
            actions.append(
                f"Preserved hook script {hook_record['script_path']} "
                f"(could not confirm it is unmodified; file kept)"
            )
            return actions
        script_path.unlink()
        # Drop empty parent dirs (hooks/, then .devlog/ only if empty).
        parent = script_path.parent
        while parent != project_root and parent.exists():
            try:
                if any(parent.iterdir()):
                    break
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
        actions.append(f"Removed {hook_record['script_path']}")

    return actions


# ── Claude Code slash command helpers ────────────────────────────────────

CLAUDE_COMMANDS_DIR_REL = ".claude/commands"


def _install_claude_commands(
    root_dir: Path,
    previous: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Copy bundled slash command templates into .claude/commands/.

    root_dir is the project root (per-project) or Path.home() (global).
    `previous` is the prior manifest's commands list (used to reconcile orphans
    from removed/renamed templates and to detect user customizations).

    Returns ``(records, preserved, removed_orphans)``:
        records          — command records to store in the new manifest.
        preserved        — names of commands that were left untouched because
                           the user customized them since install (warn the
                           caller; do not overwrite).
        removed_orphans  — paths of files removed because the corresponding
                           template no longer exists in this version.
    """
    src_dir = _templates_dir() / "commands"
    dst_dir = root_dir / CLAUDE_COMMANDS_DIR_REL

    previous = previous or []

    # If templates aren't shipped with this build (packaging error, incomplete
    # checkout), pass the previous records through untouched. Reconciliation
    # would otherwise treat every tracked command as an orphan and delete user
    # files on what is really a broken install — a net-destructive failure mode.
    if not src_dir.is_dir():
        return list(previous), [], []

    prev_by_name = {p["name"]: p for p in previous if "name" in p}

    records: list[dict[str, Any]] = []
    preserved: list[str] = []
    removed_orphans: list[str] = []

    dst_dir.mkdir(parents=True, exist_ok=True)
    for src in sorted(src_dir.glob("*.md")):
        dst = dst_dir / src.name
        new_text = src.read_text(encoding="utf-8")
        new_hash = Manifest._sha256(new_text)
        rel = f"{CLAUDE_COMMANDS_DIR_REL}/{src.name}"

        prev = prev_by_name.get(src.stem)
        if dst.exists() and prev and prev.get("sha256"):
            current_hash = _safe_file_hash(dst)
            if current_hash and current_hash != prev["sha256"] and current_hash != new_hash:
                # User edited the file since install — preserve their edits.
                records.append({"name": src.stem, "path": rel, "sha256": current_hash})
                preserved.append(src.stem)
                continue
            # current_hash is None → file is unreadable. Fall through and
            # overwrite from the template; better than aborting the install.

        shutil.copy2(src, dst)
        records.append({"name": src.stem, "path": rel, "sha256": new_hash})

    # Reconcile orphans: any previously-tracked command that this version no
    # longer ships should be removed, unless the user customized it (in which
    # case we leave the file alone but stop tracking it).
    new_names = {r["name"] for r in records}
    for prev in previous:
        name = prev.get("name")
        rel = prev.get("path")
        if not name or not rel or name in new_names:
            continue
        old_path = root_dir / rel
        if not old_path.exists():
            continue
        prev_hash = prev.get("sha256")
        if prev_hash:
            current_hash = _safe_file_hash(old_path)
            if current_hash is None or current_hash != prev_hash:
                # Either the file diverged from the recorded hash, or we can't
                # read it to be sure. Either way, don't risk deleting it.
                preserved.append(name)
                continue
        old_path.unlink()
        removed_orphans.append(rel)
        # Drop empty parent dirs.
        parent = old_path.parent
        while parent != root_dir and parent.exists():
            try:
                if any(parent.iterdir()):
                    break
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    return records, preserved, removed_orphans


def _safe_file_hash(path: Path) -> str | None:
    """Hash a file's UTF-8 contents, returning None if it's unreadable."""
    try:
        return Manifest._sha256(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return None


def _uninstall_claude_command(root_dir: Path, cmd_record: dict[str, Any]) -> list[str]:
    """Remove a previously-installed slash command. Returns a list of human-readable
    actions taken (for display).

    If the file's hash diverges from the manifest's recorded hash, the user has
    customized it since install — leave it in place and report that.
    """
    actions: list[str] = []

    rel = cmd_record.get("path")
    if not rel:
        return actions

    cmd_path = root_dir / rel
    if not cmd_path.exists():
        return actions

    recorded_hash = cmd_record.get("sha256")
    if recorded_hash:
        current_hash = _safe_file_hash(cmd_path)
        if current_hash is None or current_hash != recorded_hash:
            # File diverged from manifest, or we couldn't read it to confirm.
            # Don't risk deleting a customized file — leave it for the user.
            actions.append(
                f"Preserved customized slash command /{cmd_record.get('name', cmd_path.stem)} "
                f"({rel} — local edits detected, file kept)"
            )
            return actions

    cmd_path.unlink()
    # Drop empty parent dirs (commands/, then .claude/ only if empty).
    parent = cmd_path.parent
    while parent != root_dir and parent.exists():
        try:
            if any(parent.iterdir()):
                break
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent
    actions.append(f"Removed slash command /{cmd_record.get('name', cmd_path.stem)}")

    return actions


# ── Entry point ──────────────────────────────────────────────────────────


def main() -> None:
    app()
