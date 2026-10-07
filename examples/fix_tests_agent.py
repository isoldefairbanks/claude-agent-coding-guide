"""A test-fixing coding agent on the Claude Agent SDK, pointed at an Anthropic-compatible endpoint.

    pip install claude-agent-sdk            # Python 3.10+
    export ANTHROPIC_BASE_URL=https://argolink.io
    export ANTHROPIC_AUTH_TOKEN=your-key
    python examples/fix_tests_agent.py ~/src/my-service "pytest -q" --budget 1.00

The agent runs the test command, reads and edits code until the tests pass, then
summarizes. File edits and the test command are pre-approved; no other shell
command is, and the final result lists any tool call that was not allowed.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import shlex

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, TextBlock, query

# The SDK estimates cost from Anthropic list prices. The endpoint bills Claude
# models at 40% of list (model pages, checked 2026-10-07), so a real budget of
# $1 is a list-price budget of $2.50. This ratio is wrong for non-Claude IDs.
PRICE_RATIO = 0.4

PROMPT = (
    "Run `{command}`. If any test fails, find the cause in the code under test and fix it; "
    "change a test only if the test itself is wrong, and say so. Re-run `{command}` after each "
    "change. Stop when the tests pass or after you have shown why they cannot pass. "
    "End with a short summary of each file you changed and why."
)


def build_options(repo: str, command: str, model: str, budget_usd: float) -> ClaudeAgentOptions:
    program = shlex.split(command)[0]
    gateway_env = {name: os.environ[name] for name in ("ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN") if name in os.environ}
    return ClaudeAgentOptions(
        cwd=repo,
        model=model,
        allowed_tools=["Read", "Edit", "Write", f"Bash({program} *)"],
        permission_mode="acceptEdits",
        max_turns=40,
        max_budget_usd=round(budget_usd / PRICE_RATIO, 2),
        env=gateway_env,  # merged over the inherited environment by the Python SDK
    )


def summarize(result: ResultMessage) -> str:
    listed = result.total_cost_usd or 0.0
    denied = len(result.permission_denials or [])
    return (
        f"{result.num_turns} turns, {'error' if result.is_error else 'done'}, {denied} tool calls not allowed; "
        f"SDK estimate at list price ${listed:.4f}, about ${listed * PRICE_RATIO:.4f} at the endpoint's rate"
    )


async def run(repo: str, command: str, model: str, budget_usd: float) -> int:
    options = build_options(repo, command, model, budget_usd)
    async for message in query(prompt=PROMPT.format(command=command), options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print(block.text)
        elif isinstance(message, ResultMessage):
            print("\n" + summarize(message))
            return 1 if message.is_error else 0
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix failing tests with a Claude agent.")
    parser.add_argument("repo")
    parser.add_argument("command", help='test command, e.g. "pytest -q" or "npm test"')
    parser.add_argument("--model", default="claude-opus-5-5")
    parser.add_argument("--budget", type=float, default=1.0, help="stop at about this many USD at the endpoint's rate")
    args = parser.parse_args()
    return asyncio.run(run(os.path.abspath(args.repo), args.command, args.model, args.budget))


if __name__ == "__main__":
    raise SystemExit(main())
