"""Tests for agents.py — registry and lookup."""
from __future__ import annotations

import pytest

from devlog_cli.agents import AGENTS, get_agent


class TestAgentRegistry:
    def test_claude_registered(self):
        agent = get_agent("claude")
        assert agent.name == "Claude Code"
        assert agent.context_file == "CLAUDE.md"

    def test_copilot_registered(self):
        agent = get_agent("copilot")
        assert agent.context_file == ".github/copilot-instructions.md"

    def test_gemini_registered(self):
        agent = get_agent("gemini")
        assert agent.context_file == "GEMINI.md"

    def test_agents_md_agents(self):
        """All agents using AGENTS.md should point to that file."""
        agents_md_keys = [k for k, v in AGENTS.items() if v.context_file == "AGENTS.md"]
        assert len(agents_md_keys) >= 20  # currently 24

    def test_total_count(self):
        assert len(AGENTS) == 27

    def test_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown agent.*nonexistent"):
            get_agent("nonexistent")

    def test_error_lists_available(self):
        with pytest.raises(KeyError, match="claude"):
            get_agent("nonexistent")
