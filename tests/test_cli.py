"""Tests for CLI commands via typer's CliRunner."""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from devlog_cli import app
from devlog_cli.convention import _SENTINEL_START_MARKER, SENTINEL_END

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
        assert _SENTINEL_START_MARKER in claude_md
        assert SENTINEL_END in claude_md

    def test_preserves_existing_content(self, initialized_project: Path):
        claude_md = initialized_project / "CLAUDE.md"
        claude_md.write_text("# My Rules\n\nDon't touch this.\n")
        runner.invoke(app, ["install", "--ai", "claude"])
        content = claude_md.read_text()
        assert "# My Rules" in content
        assert _SENTINEL_START_MARKER in content

    def test_reinstall_replaces(self, installed_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        content = (installed_project / "CLAUDE.md").read_text()
        assert content.count(_SENTINEL_START_MARKER) == 1

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


class TestSlashCommands:
    def test_command_file_created(self, initialized_project: Path):
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        cmd_file = initialized_project / ".claude" / "commands" / "devlog-catchup.md"
        assert cmd_file.exists()
        body = cmd_file.read_text(encoding="utf-8")
        assert "blog/_index.md" in body
        assert "learned.md" in body

    def test_write_command_file_created(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        cmd_file = initialized_project / ".claude" / "commands" / "devlog-write.md"
        assert cmd_file.exists()
        body = cmd_file.read_text(encoding="utf-8")
        assert "$ARGUMENTS" in body

    def test_manicure_command_file_created(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        cmd_file = initialized_project / ".claude" / "commands" / "devlog-manicure.md"
        assert cmd_file.exists()
        body = cmd_file.read_text(encoding="utf-8")
        # Phase markers and key concepts present.
        assert "Phase 1" in body
        assert "Phase 4" in body
        assert "annotate" in body
        assert "wipe" in body
        # Optional topic argument is wired in.
        assert "$ARGUMENTS" in body

    def test_manifest_records_command(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        data = json.loads(
            (initialized_project / ".devlog" / "manifests" / "claude.manifest.json").read_text()
        )
        names = {c["name"] for c in data["commands"]}
        assert "devlog-catchup" in names
        assert "devlog-write" in names
        assert "devlog-manicure" in names

    def test_install_message_lists_command(self, initialized_project: Path):
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert "/devlog-catchup" in result.output
        assert "/devlog-write" in result.output
        assert "/devlog-manicure" in result.output

    def test_idempotent_on_reinstall(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        runner.invoke(app, ["install", "--ai", "claude"])
        cmd_files = list((initialized_project / ".claude" / "commands").glob("*.md"))
        assert len(cmd_files) == 3  # catchup + write + manicure

    def test_not_installed_for_non_claude(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "copilot"])
        assert not (initialized_project / ".claude" / "commands").exists()

    def test_uninstall_removes_command(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        cmd_file = initialized_project / ".claude" / "commands" / "devlog-catchup.md"
        assert cmd_file.exists()
        runner.invoke(app, ["uninstall", "--ai", "claude"])
        assert not cmd_file.exists()
        # Empty .claude/commands and .claude get cleaned up.
        assert not (initialized_project / ".claude" / "commands").exists()

    def test_global_install_creates_command(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        runner.invoke(app, ["install", "--ai", "claude", "--global"])
        cmd_file = project_dir / ".claude" / "commands" / "devlog-catchup.md"
        assert cmd_file.exists()

    def test_global_uninstall_removes_command(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        runner.invoke(app, ["install", "--ai", "claude", "--global"])
        runner.invoke(app, ["uninstall", "--ai", "claude", "--global"])
        assert not (project_dir / ".claude" / "commands" / "devlog-catchup.md").exists()

    def test_manifest_records_command_hashes(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        data = json.loads(
            (initialized_project / ".devlog" / "manifests" / "claude.manifest.json").read_text(encoding="utf-8")
        )
        for cmd in data["commands"]:
            assert "sha256" in cmd
            assert len(cmd["sha256"]) == 64

    def test_reinstall_preserves_user_customization(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        cmd_file = initialized_project / ".claude" / "commands" / "devlog-catchup.md"
        cmd_file.write_text("# my custom version\n", encoding="utf-8")
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        assert cmd_file.read_text(encoding="utf-8") == "# my custom version\n"
        assert "Preserved" in result.output

    def test_uninstall_preserves_user_customization(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        cmd_file = initialized_project / ".claude" / "commands" / "devlog-catchup.md"
        cmd_file.write_text("# my custom version\n", encoding="utf-8")
        result = runner.invoke(app, ["uninstall", "--ai", "claude"])
        assert result.exit_code == 0
        assert cmd_file.exists()
        assert cmd_file.read_text(encoding="utf-8") == "# my custom version\n"

    def test_reinstall_removes_orphaned_command(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        manifest_path = initialized_project / ".devlog" / "manifests" / "claude.manifest.json"
        # Simulate a previous version that shipped an extra slash command:
        # add an orphan file plus a manifest entry pointing at it.
        orphan = initialized_project / ".claude" / "commands" / "devlog-zombie.md"
        orphan.write_text("ghost from a prior release\n", encoding="utf-8")
        import hashlib

        orphan_hash = hashlib.sha256(
            orphan.read_text(encoding="utf-8").encode("utf-8")
        ).hexdigest()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data["commands"].append({
            "name": "devlog-zombie",
            "path": ".claude/commands/devlog-zombie.md",
            "sha256": orphan_hash,
        })
        manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        assert not orphan.exists()
        # And the manifest stops tracking it.
        new_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "devlog-zombie" not in {c["name"] for c in new_data["commands"]}

    def test_install_passthrough_when_templates_missing(self, initialized_project: Path, monkeypatch):
        """If templates/commands/ is missing (packaging error / incomplete checkout),
        reinstall must NOT delete previously-tracked commands as orphans."""
        from devlog_cli import _install_claude_commands

        runner.invoke(app, ["install", "--ai", "claude"])
        cmd_file = initialized_project / ".claude" / "commands" / "devlog-catchup.md"
        assert cmd_file.exists()
        manifest_path = initialized_project / ".devlog" / "manifests" / "claude.manifest.json"
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))["commands"]

        # Point _templates_dir() at a directory without commands/ to simulate the failure.
        from devlog_cli import _templates_dir as real_templates_dir
        broken_root = initialized_project / "broken_templates"
        broken_root.mkdir()
        monkeypatch.setattr("devlog_cli._templates_dir", lambda: broken_root)

        records, preserved, orphans = _install_claude_commands(initialized_project, previous)
        assert records == previous  # passthrough preserves the prior manifest exactly
        assert preserved == []
        assert orphans == []
        assert cmd_file.exists()  # critically, no files deleted

    def test_reinstall_overwrites_unreadable_file(self, initialized_project: Path):
        """If dst exists but is unreadable, install must not abort — it should
        fall back to overwriting from the template."""
        runner.invoke(app, ["install", "--ai", "claude"])
        cmd_file = initialized_project / ".claude" / "commands" / "devlog-catchup.md"
        # Write invalid UTF-8 to trigger UnicodeDecodeError on read.
        cmd_file.write_bytes(b"\xff\xfe not valid utf-8 \x80")
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        # File got overwritten from the template — content should now be valid UTF-8
        # matching the bundled template (starts with frontmatter).
        body = cmd_file.read_text(encoding="utf-8")
        assert body.startswith("---")

    def test_reinstall_preserves_modified_orphan(self, initialized_project: Path):
        runner.invoke(app, ["install", "--ai", "claude"])
        manifest_path = initialized_project / ".devlog" / "manifests" / "claude.manifest.json"
        orphan = initialized_project / ".claude" / "commands" / "devlog-zombie.md"
        orphan.write_text("original ghost\n", encoding="utf-8")
        import hashlib

        original_hash = hashlib.sha256("original ghost\n".encode("utf-8")).hexdigest()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data["commands"].append({
            "name": "devlog-zombie",
            "path": ".claude/commands/devlog-zombie.md",
            "sha256": original_hash,
        })
        manifest_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        # User customized it after install; reinstall must not delete their edits.
        orphan.write_text("user-edited ghost\n", encoding="utf-8")
        result = runner.invoke(app, ["install", "--ai", "claude"])
        assert result.exit_code == 0
        assert orphan.exists()
        assert orphan.read_text(encoding="utf-8") == "user-edited ghost\n"


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
        assert _SENTINEL_START_MARKER not in content

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


class TestGlobalInstall:
    def test_creates_global_claude_md(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        result = runner.invoke(app, ["install", "--ai", "claude", "--global"])
        assert result.exit_code == 0
        claude_md = project_dir / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text()
        assert _SENTINEL_START_MARKER in content
        assert "Every project" in content  # global opener wording

    def test_includes_bootstrap_section(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        runner.invoke(app, ["install", "--ai", "claude", "--global"])
        content = (project_dir / "CLAUDE.md").read_text()
        assert "First-time setup" in content
        assert ".devlog/config.yaml" in content

    def test_with_hook_global(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        result = runner.invoke(app, ["install", "--ai", "claude", "--global", "--with-hook"])
        assert result.exit_code == 0
        assert (project_dir / ".devlog" / "hooks" / "stop.py").exists()
        settings = json.loads((project_dir / ".claude" / "settings.json").read_text())
        command = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
        assert "$HOME/" in command  # global hook uses $HOME, not $CLAUDE_PROJECT_DIR

    def test_manifest_in_home(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        runner.invoke(app, ["install", "--ai", "claude", "--global"])
        manifest = project_dir / ".devlog" / "manifests" / "claude.manifest.json"
        assert manifest.exists()

    def test_rejected_for_non_claude(self, project_dir: Path):
        result = runner.invoke(app, ["install", "--ai", "copilot", "--global"])
        assert result.exit_code == 1

    def test_preserves_existing_global_content(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        claude_md = project_dir / "CLAUDE.md"
        claude_md.write_text("# My global rules\n")
        runner.invoke(app, ["install", "--ai", "claude", "--global"])
        content = claude_md.read_text()
        assert "# My global rules" in content
        assert _SENTINEL_START_MARKER in content


class TestGlobalUninstall:
    def test_removes_global_convention(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        runner.invoke(app, ["install", "--ai", "claude", "--global"])
        result = runner.invoke(app, ["uninstall", "--ai", "claude", "--global"])
        assert result.exit_code == 0
        # CLAUDE.md was devlog-only, so file should be removed
        assert not (project_dir / "CLAUDE.md").exists()

    def test_removes_global_hook(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        runner.invoke(app, ["install", "--ai", "claude", "--global", "--with-hook"])
        runner.invoke(app, ["uninstall", "--ai", "claude", "--global"])
        assert not (project_dir / ".devlog" / "hooks" / "stop.py").exists()

    def test_global_uninstall_not_installed(self, project_dir: Path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: project_dir)
        result = runner.invoke(app, ["uninstall", "--ai", "claude", "--global"])
        assert result.exit_code == 1


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
