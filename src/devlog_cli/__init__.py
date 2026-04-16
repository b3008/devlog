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

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from devlog_cli.agents import AGENTS, get_agent
from devlog_cli.convention import (
    SENTINEL_START,
    discover_tags,
    generate_convention,
    inject_convention,
    load_config,
    remove_convention,
    scan_entries,
)
from devlog_cli.manifest import Manifest

__version__ = "0.1.0"

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
) -> None:
    """Inject the blog convention into an agent's context file."""
    project_root = Path.cwd()

    try:
        agent = get_agent(ai)
    except KeyError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    # Check if devlog is initialized
    config_path = project_root / ".devlog" / "config.yaml"
    if not config_path.exists():
        console.print("[yellow]devlog not initialized. Running init first...[/yellow]")
        console.print()
        init(project_name=None)
        console.print()

    # Check for existing manifest
    manifest_path = project_root / ".devlog" / "manifests" / f"{ai}.manifest.json"
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

    convention_text = generate_convention(config)
    manifest = Manifest(agent_key=ai, project_root=project_root, version=__version__)

    tree = Tree(f"[bold green]Installing devlog convention[/bold green] — {agent.name}")
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

    manifest.save()
    tree.add("[dim]Manifest saved[/dim]")

    console.print()
    console.print(tree)
    console.print()
    console.print(
        f"[green]Done.[/green] {agent.name} will now maintain a development blog "
        f"in [cyan]{config['blog_dir']}/[/cyan]."
    )


# ── Uninstall command ────────────────────────────────────────────────────


@app.command()
def uninstall(
    ai: str = typer.Option(..., "--ai", help="AI agent key to remove convention from."),
) -> None:
    """Remove the blog convention from an agent's context file."""
    project_root = Path.cwd()

    try:
        agent = get_agent(ai)
    except KeyError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    manifest_path = project_root / ".devlog" / "manifests" / f"{ai}.manifest.json"
    if not manifest_path.exists():
        console.print(f"[red]No manifest found for {agent.name}. Not installed?[/red]")
        raise typer.Exit(1)

    # Remove convention from context file
    ctx_path = project_root / agent.context_file
    if ctx_path.exists():
        content = ctx_path.read_text(encoding="utf-8")
        if SENTINEL_START in content:
            new_content = remove_convention(content)
            if new_content.strip():
                ctx_path.write_text(new_content, encoding="utf-8")
                console.print(f"[green]Removed convention from {agent.context_file}[/green]")
            else:
                # Context file is now empty — remove it
                ctx_path.unlink()
                console.print(f"[green]Removed {agent.context_file} (was empty after removal)[/green]")
        else:
            console.print(f"[yellow]No devlog section found in {agent.context_file}[/yellow]")
    else:
        console.print(f"[yellow]{agent.context_file} not found[/yellow]")

    # Clean up manifest
    if manifest_path.exists():
        manifest_path.unlink()
        # Clean empty parent dirs
        parent = manifest_path.parent
        while parent != project_root and parent.exists():
            try:
                if any(parent.iterdir()):
                    break
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    console.print(f"[green]Done. {agent.name} convention uninstalled.[/green]")


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
    console.print()

    table = Table(title="Installed Conventions")
    table.add_column("Agent", style="cyan")
    table.add_column("Context File", style="dim")
    table.add_column("Status")
    table.add_column("Installed", style="dim")

    earliest_install: Optional[datetime] = None
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
        if ctx_path.exists() and SENTINEL_START in ctx_path.read_text(encoding="utf-8"):
            status_text = "[green]active[/green]"
        else:
            status_text = "[red]missing[/red]"

        installed_display = "\u2014"
        if manifest.installed_at:
            try:
                dt = datetime.fromisoformat(manifest.installed_at.replace("Z", "+00:00"))
                installed_display = dt.strftime("%Y-%m-%d")
                if earliest_install is None or dt < earliest_install:
                    earliest_install = dt
            except ValueError:
                pass

        table.add_row(agent.name, agent.context_file, status_text, installed_display)

    console.print(table)

    # Warn if the convention may not be firing
    if earliest_install is not None and entry_count == 0:
        days = (datetime.now(timezone.utc) - earliest_install).days
        if days >= 1:
            console.print()
            console.print(Panel(
                f"No entries written since install ({days} day{'s' if days != 1 else ''} ago).\n"
                f"The convention may not be firing. Things to try:\n"
                f"  \u2022 Start a fresh agent session (context files are usually read at session start).\n"
                f"  \u2022 Nudge the agent: [cyan]\"check if this session warrants a devlog entry and write one if so\"[/cyan]\n"
                f"  \u2022 If the defaults don't fit your project, edit [cyan].devlog/config.yaml[/cyan] and re-run install.",
                title="[yellow]Warning[/yellow]",
                border_style="yellow",
            ))


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


# ── Entry point ──────────────────────────────────────────────────────────


def main() -> None:
    app()
