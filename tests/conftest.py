"""Shared fixtures for devlog tests."""
from __future__ import annotations

import os
from pathlib import Path

import pytest


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
    from devlog_cli import install

    install(ai="claude", with_hook=False)
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
