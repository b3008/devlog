"""Tests for CLI commands via typer's CliRunner."""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devlog_cli import app
from devlog_cli.convention import SENTINEL_END, SENTINEL_START

runner = CliRunner()


class TestInit:
    def test_creates_scaffold(self, project_dir: Path):
        result = runner.invoke(app, ["init", "--name", "My Project"])
        assert result.exit_code == 0
        assert (project_dir / ".devlog" / "config.yaml").exists()
        assert (project_dir / ".devlog" / "learned.md").exists()
        assert (project_dir / "blog" / "_index.md").exists()
        assert (project_dir / "blog" / "media").is_dir()

    def test_index_has_project_name(self, project_dir: Path):
        runner.invoke(app, ["init", "--name", "My Project"])
        content = (project_dir / "blog" / "_index.md").read_text()
        assert "My Project" in content

    def test_idempotent(self, project_dir: Path):
        runner.invoke(app, ["init"])
        runner.invoke(app, ["init"])
        assert (project_dir / ".devlog" / "config.yaml").exists()

    def test_defaults_name_to_dirname(self, project_dir: Path):
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0


class TestInstall:
    def test_creates_claude_md(self, initialized_project: Path):
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        claude_md = (initialized_project / "CLAUDE.md").read_text()
        assert SENTINEL_START in claude_md
        assert SENTINEL_END in claude_md

    def test_preserves_existing_content(self, initialized_project: Path):
        claude_md = initialized_project / "CLAUDE.md"
        claude_md.write_text("# My Rules\n\nDon't touch this.\n")
        runner.invoke(app, ["install", "--ai", "claude"])
        content = claude_md.read_text()
        assert "# My Rules" in content
        assert SENTINEL_START in content

    def test_reinstall_replaces(self, installed_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        content = (installed_project / "CLAUDE.md").read_text()
        assert content.count(SENTINEL_START) == 1

    def test_auto_init(self, project_dir: Path):
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        assert (project_dir / ".devlog" / "config.yaml").exists()

    def test_unknown_agent(self, project_dir: Path):
        result = runner.invoke(app, ["install", "--ai", "nonexistent"])
        assert result.exit_code == 1

    def test_tag_discovery(self, installed_project: Path, sample_entry: Path):
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        assert "custom-tag" in result.output

    def test_manifest_created(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        manifest = initialized_project / ".devlog" / "manifests" / "claude.manifest.json"
        assert manifest.exists()
        data = json.loads(manifest.read_text())
        assert data["agent"] == "claude"
        assert "CLAUDE.md" in data["files"]


class TestInstallWithHook:
    def test_creates_hook_files(self, initialized_project: Path):
        result = runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        assert result.exit_code == 0
        assert (initialized_project / ".devlog" / "hooks" / "stop.py").exists()
        assert (initialized_project / ".claude" / "settings.json").exists()

    def test_settings_json_structure(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        settings = json.loads(
            (initialized_project / ".claude" / "settings.json").read_text()
        )
        stop_entries = settings["hooks"]["Stop"]
        assert len(stop_entries) == 1
        commands = [h["command"] for h in stop_entries[0]["hooks"]]
        assert any(".devlog/hooks/stop.py" in c for c in commands)

    def test_preserves_existing_settings(self, initialized_project: Path):
        settings_dir = initialized_project / ".claude"
        settings_dir.mkdir()
        (settings_dir / "settings.json").write_text(
            json.dumps({"theme": "dark", "permissions": {"allow": ["Bash"]}})
        )
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        settings = json.loads((settings_dir / "settings.json").read_text())
        assert settings["theme"] == "dark"
        assert settings["permissions"] == {"allow": ["Bash"]}
        assert "hooks" in settings

    def test_idempotent(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        settings = json.loads(
            (initialized_project / ".claude" / "settings.json").read_text()
        )
        assert len(settings["hooks"]["Stop"]) == 1

    def test_manifest_records_hook(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        data = json.loads(
            (initialized_project / ".devlog" / "manifests" / "claude.manifest.json").read_text()
        )
        assert len(data["hooks"]) == 1
        assert data["hooks"][0]["event"] == "Stop"

    def test_rejected_for_non_claude(self, initialized_project: Path):
        result = runner.invoke(app, ["install", "--ai", "copilot", "--with-hook"])
        assert result.exit_code == 1
        assert "only supported for" in result.output

    def test_hook_tip_shown_without_flag(self, initialized_project: Path):
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert "--with-hook" in result.output


class TestUninstall:
    def test_removes_convention(self, installed_project: Path):
        result = runner.invoke(app, ["uninstall", "--ai", "claude"])
        assert result.exit_code == 0
        assert not (installed_project / "CLAUDE.md").exists()  # was empty besides convention

    def test_preserves_non_devlog_content(self, initialized_project: Path):
        claude_md = initialized_project / "CLAUDE.md"
        claude_md.write_text("# My Rules\n")
        runner.invoke(app, ["install", "--ai", "claude"])
        runner.invoke(app, ["uninstall", "--ai", "claude"])
        content = claude_md.read_text()
        assert "# My Rules" in content
        assert SENTINEL_START not in content

    def test_removes_hook(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        assert (initialized_project / ".devlog" / "hooks" / "stop.py").exists()
        runner.invoke(app, ["uninstall", "--ai", "claude"])
        assert not (initialized_project / ".devlog" / "hooks" / "stop.py").exists()

    def test_hook_removal_preserves_settings(self, initialized_project: Path):
        settings_dir = initialized_project / ".claude"
        settings_dir.mkdir()
        (settings_dir / "settings.json").write_text(json.dumps({"theme": "dark"}))
        runner.invoke(app, ["install", "--ai", "claude", "--with-hook"])
        runner.invoke(app, ["uninstall", "--ai", "claude"])
        settings = json.loads((settings_dir / "settings.json").read_text())
        assert settings == {"theme": "dark"}

    def test_not_installed(self, project_dir: Path):
        result = runner.invoke(app, ["uninstall", "--ai", "claude"])
        assert result.exit_code == 1

    def test_removes_manifest(self, installed_project: Path):
        manifest = installed_project / ".devlog" / "manifests" / "claude.manifest.json"
        assert manifest.exists()
        runner.invoke(app, ["uninstall", "--ai", "claude"])
        assert not manifest.exists()


class TestStatus:
    def test_no_agents(self, project_dir: Path):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "No agents installed" in result.output

    def test_shows_active(self, installed_project: Path):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "active" in result.output
        assert "Claude Code" in result.output

    def test_shows_entry_count(self, installed_project: Path, sample_entry: Path):
        result = runner.invoke(app, ["status"])
        assert "1 entry" in result.output
        assert "2026-04-16" in result.output

    def test_no_entries_shown(self, installed_project: Path):
        result = runner.invoke(app, ["status"])
        assert "no entries yet" in result.output


class TestListAgents:
    def test_lists_agents(self, project_dir: Path):
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "Claude Code" in result.output
        assert "GitHub Copilot" in result.output
        assert "Gemini CLI" in result.output


class TestVersion:
    def test_shows_version(self, project_dir: Path):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
