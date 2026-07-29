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

    def test_claude_capabilities(self):
        agent = get_agent("claude")
        assert agent.commands_dir == ".claude/commands"
        assert agent.global_dir == ".claude"
        assert agent.supports_hooks is True

    def test_opencode_registered_with_capabilities(self):
        agent = get_agent("opencode")
        assert agent.name == "OpenCode"
        assert agent.context_file == "AGENTS.md"
        assert agent.commands_dir == ".opencode/commands"
        assert agent.global_dir == ".config/opencode"
        assert agent.supports_hooks is False

    def test_plain_agents_have_no_extras(self):
        agent = get_agent("codex")
        assert agent.commands_dir is None
        assert agent.global_dir is None
        assert agent.supports_hooks is False

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
