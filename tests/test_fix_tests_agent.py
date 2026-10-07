"""Offline tests for the Agent SDK example. Uses the real claude_agent_sdk when it is
installed (Python 3.10+); otherwise a minimal stand-in, so the glue logic is still checked."""
import dataclasses
import json
import os
import sys
import types

import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "examples"))

try:
    import claude_agent_sdk  # noqa: F401
except ImportError:  # pragma: no cover - depends on the interpreter
    stub = types.ModuleType("claude_agent_sdk")

    @dataclasses.dataclass
    class ClaudeAgentOptions:
        cwd: object = None
        model: object = None
        allowed_tools: list = dataclasses.field(default_factory=list)
        permission_mode: object = None
        max_turns: object = None
        max_budget_usd: object = None
        env: dict = dataclasses.field(default_factory=dict)

    @dataclasses.dataclass
    class ResultMessage:
        subtype: str
        duration_ms: int
        duration_api_ms: int
        is_error: bool
        num_turns: int
        session_id: str
        total_cost_usd: object = None
        permission_denials: object = None

    stub.ClaudeAgentOptions = ClaudeAgentOptions
    stub.ResultMessage = ResultMessage
    stub.AssistantMessage = type("AssistantMessage", (), {})
    stub.TextBlock = type("TextBlock", (), {})
    stub.query = None
    sys.modules["claude_agent_sdk"] = stub

import fix_tests_agent  # noqa: E402
from claude_agent_sdk import ResultMessage  # noqa: E402


@pytest.fixture
def gateway(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://argolink.io")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "test-key")


def test_only_the_test_runner_is_preapproved(gateway):
    options = fix_tests_agent.build_options("/repo", "pytest -q tests/", "claude-opus-5-5", 1.0)
    assert options.allowed_tools == ["Read", "Edit", "Write", "Bash(pytest *)"]
    assert options.permission_mode == "acceptEdits"
    assert options.cwd == "/repo"


def test_budget_is_converted_to_list_price(gateway):
    options = fix_tests_agent.build_options("/repo", "npm test", "claude-sonnet-5", 1.0)
    assert options.max_budget_usd == 2.5
    assert options.allowed_tools[-1] == "Bash(npm *)"


def test_gateway_variables_are_passed_and_nothing_else(gateway, monkeypatch):
    monkeypatch.setenv("UNRELATED_SECRET", "x")
    options = fix_tests_agent.build_options("/repo", "go test ./...", "claude-opus-5", 2.0)
    assert options.env == {"ANTHROPIC_BASE_URL": "https://argolink.io", "ANTHROPIC_AUTH_TOKEN": "test-key"}


def test_summary_reports_both_cost_figures():
    result = ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False,
                           num_turns=12, session_id="s", total_cost_usd=1.25, permission_denials=[])
    text = fix_tests_agent.summarize(result)
    assert "12 turns, done, 0 tool calls not allowed" in text
    assert "$1.2500" in text and "$0.5000" in text


def test_prompt_names_the_command_twice():
    prompt = fix_tests_agent.PROMPT.format(command="cargo test")
    assert prompt.count("`cargo test`") == 2


@pytest.mark.parametrize("name", ["opencode.json", "qwen-settings.json"])
def test_shipped_configs_parse(name):
    with open(os.path.join(HERE, "..", "configs", name), encoding="utf-8") as handle:
        json.load(handle)
