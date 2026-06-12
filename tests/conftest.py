"""Shared fixtures for devlog tests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path_factory, monkeypatch) -> Path:
    """Point Path.home() (and $HOME for subprocesses) at a temp directory.

    Local installs consult the real home for a global devlog install
    (thin-block detection), so without this the suite would behave
    differently on machines that have devlog installed globally."""
    home = tmp_path_factory.mktemp("home")
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setenv("HOME", str(home))
    return home


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal project directory and chdir into it."""
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original_cwd)


@pytest.fixture()
def initialized_project(project_dir: Path) -> Path:
    """A project directory with `devlog init` already run."""
    from devlog_cli import init

    init(project_name="Test Project")
    return project_dir


@pytest.fixture()
def installed_project(initialized_project: Path) -> Path:
    """A project directory with `devlog install --ai claude` already run."""
    from typer.testing import CliRunner

    from devlog_cli import app

    CliRunner().invoke(app, ["install", "--ai", "claude"])
    return initialized_project


@pytest.fixture()
def sample_entry(installed_project: Path) -> Path:
    """Create a sample blog entry with frontmatter."""
    entry = installed_project / "blog" / "2026-04-16-test-entry.md"
    entry.write_text(
        "---\n"
        'title: "Test entry"\n'
        "date: 2026-04-16\n"
        "tags: [feature, custom-tag, testing]\n"
        'summary: "A test."\n'
        "---\n"
        "\n"
        "Body text.\n",
        encoding="utf-8",
    )
    return entry
