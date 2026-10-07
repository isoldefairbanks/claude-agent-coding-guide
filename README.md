# Claude coding agents beyond Claude Code — Cline, OpenCode, Qwen Code and the Claude Agent SDK

Recipes for running Claude Opus 5.5, Opus 5, Sonnet 5 and Fable 5.1 inside open-source coding agents with one API key, and a small test-fixing agent built on the Claude Agent SDK. Every recipe points at the same Anthropic-compatible endpoint, [ArgoLink](https://argolink.io/gh-claude-agent-coding-guide), where these models cost 60% less than Anthropic's list price.

<sub>Configuration keys checked 2026-10-07 against docs.cline.bot, opencode.ai/docs, the Qwen Code docs and code.claude.com, and against each tool's source where the docs were silent. Unofficial; not affiliated with Anthropic, Cline, Anomaly or Alibaba.</sub>

| Agent | Runs in | Install | Where the Claude settings go |
|---|---|---|---|
| [Cline](#cline) | VS Code, JetBrains, terminal | `npm i -g cline` or the VS Code Marketplace extension `saoudrizwan.claude-dev` | Settings ⚙ → API Provider, or `cline auth` |
| [OpenCode](#opencode) | terminal, desktop | `curl -fsSL https://opencode.ai/install \| bash` | `opencode.json` |
| [Qwen Code](#qwen-code) | terminal, IDEs | `npm install -g @qwen-code/qwen-code@latest` (Node.js 22+) | `~/.qwen/settings.json` |
| [Claude Agent SDK](#claude-agent-sdk-a-test-fixing-agent) | your Python program | `pip install claude-agent-sdk` (Python 3.10+) | the `env` option |

## The setting that breaks most setups: root origin or `/v1`

Every agent asks for a "base URL", and the right value depends on the HTTP library inside the agent, not on the endpoint:

| Library the agent uses | Path it adds | Value to enter | Agents |
|---|---|---|---|
| `@anthropic-ai/sdk` (official Anthropic SDK) | `/v1/messages` | `https://argolink.io` | Qwen Code, Claude Code, Agent SDK |
| `@ai-sdk/anthropic` (Vercel AI SDK) | `/messages` | `https://argolink.io/v1` | Cline, OpenCode |

The wrong value fails in a recognizable way: an AI SDK client without `/v1` gets `405 Method Not Allowed` from `/messages`, and an Anthropic SDK client with `/v1` gets `404` from `/v1/v1/messages`.

## Cline

**VS Code or JetBrains**

1. Open Cline's settings (⚙) and choose **Anthropic** as the API Provider.
2. Paste your key into **Anthropic API Key**.
3. Tick **Use custom base URL** and enter `https://argolink.io/v1`.
4. Pick `claude-opus-5-5`, `claude-opus-5`, `claude-sonnet-5` or `claude-fable-5-1` from the model list.

Cline can keep a different model for Plan and for Act mode: enable **Use different models for Plan and Act** and pick, for example, Opus 5.5 to plan and Sonnet 5 to edit. Switching modes then switches models.

**CLI** ([`configs/cline-cli.sh`](./configs/cline-cli.sh))

```bash
npm i -g cline
cline auth -p anthropic -k "$ANTHROPIC_API_KEY" -m claude-opus-5-5 -b https://argolink.io/v1
cline "Run the tests and fix any failures"
git diff origin/main | cline -m claude-opus-5 "Review these changes for bugs"
```

The key and provider are stored in `~/.cline/data/settings/providers.json` and shared by the IDE extensions, the CLI and the SDK. `--thinking low|medium|high|xhigh` sets the effort for a run. For Claude 4.6 and 5.x model IDs Cline sends adaptive thinking with an effort level, the only thinking shape these models accept, so no extra setting is needed.

## OpenCode

OpenCode's built-in `anthropic` provider takes a `baseURL` override. [`configs/opencode.json`](./configs/opencode.json) also hides the Claude models the endpoint does not serve and replaces list prices with the endpoint's, so `opencode stats` reports what you pay:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "anthropic": {
      "options": { "baseURL": "https://argolink.io/v1", "apiKey": "{env:ANTHROPIC_API_KEY}" },
      "whitelist": ["claude-opus-5-5", "claude-opus-5", "claude-sonnet-5", "claude-fable-5-1"],
      "models": {
        "claude-opus-5-5": { "cost": { "input": 1.6, "output": 8, "cache_read": 0.08, "cache_write": 2 } }
      }
    }
  },
  "model": "anthropic/claude-opus-5-5",
  "small_model": "anthropic/claude-sonnet-5",
  "agent": {
    "plan": { "model": "anthropic/claude-opus-5-5" },
    "build": { "model": "anthropic/claude-sonnet-5" }
  }
}
```

Put it in the project root as `opencode.json` or in `~/.config/opencode/opencode.json`; the project file wins. Instead of `apiKey`, you can run `/connect`, choose Anthropic and paste the key, which OpenCode stores in `~/.local/share/opencode/auth.json`. Non-interactive runs work too: `opencode run -m anthropic/claude-opus-5 "Explain the retry logic in src/queue"`.

`small_model` runs titles and other light work. Set it explicitly: without it OpenCode looks for a cheaper model from the same provider and otherwise falls back to the main model.

## Qwen Code

Qwen Code reaches Claude through its `anthropic` protocol, which uses the official Anthropic SDK, so the base URL is the bare origin. From [`configs/qwen-settings.json`](./configs/qwen-settings.json):

```json
{
  "modelProviders": {
    "anthropic": [
      {
        "id": "claude-opus-5-5",
        "envKey": "ANTHROPIC_API_KEY",
        "baseUrl": "https://argolink.io",
        "capabilities": {
          "reasoning": { "profile": "anthropic-adaptive", "efforts": ["low", "medium", "high", "xhigh", "max"], "defaultEffort": "medium" }
        },
        "generationConfig": { "contextWindowSize": 1000000, "samplingParams": { "max_tokens": 32000 } }
      }
    ]
  },
  "security": { "auth": { "selectedType": "anthropic" } },
  "model": { "name": "claude-opus-5-5" }
}
```

The `anthropic-adaptive` profile matters: these Claude models reject a manual `thinking.budget_tokens`, and declaring the profile makes Qwen Code send adaptive thinking with an effort instead. Leave `temperature`, `top_p` and `top_k` out of `samplingParams`: Claude 4.7 and later models return 400 for any non-default value. Switch models with `/model` or `qwen --model claude-sonnet-5`.

## Claude Agent SDK: a test-fixing agent

The Agent SDK runs the same agent loop as Claude Code inside your program and forwards `env` to it, so the gateway setup is two variables. [`examples/fix_tests_agent.py`](./examples/fix_tests_agent.py) runs a test command, edits code until the tests pass, and stops at a dollar budget:

```bash
pip install claude-agent-sdk
export ANTHROPIC_BASE_URL=https://argolink.io
export ANTHROPIC_AUTH_TOKEN=your-key
python examples/fix_tests_agent.py ~/src/my-service "pytest -q" --budget 1.00
```

The core of it:

```python
options = ClaudeAgentOptions(
    cwd=repo,
    model="claude-opus-5-5",
    allowed_tools=["Read", "Edit", "Write", "Bash(pytest *)"],
    permission_mode="acceptEdits",
    max_turns=40,
    max_budget_usd=budget_usd / 0.4,
    env={"ANTHROPIC_BASE_URL": "https://argolink.io", "ANTHROPIC_AUTH_TOKEN": token},
)
async for message in query(prompt=PROMPT, options=options):
    ...
```

Two details are easy to miss:

- **`allowed_tools` pre-approves; it does not restrict.** Edits and the test runner run without asking; any other tool call falls through to the permission mode, and the result message lists refused calls in `permission_denials`.
- **The SDK's dollar figures use Anthropic list prices.** `total_cost_usd` and `max_budget_usd` are client-side estimates, so the script divides your budget by 0.4 before passing it, and multiplies the reported cost by 0.4. That ratio holds for the Claude models only.

## Which Claude model for which agent role

| Role | Model | Effort | Input / output per 1M | Why |
|---|---|---|---:|---|
| Plan mode, architecture questions | `claude-opus-5-5` | medium (its default) or high | $1.60 / $8 | the strongest Opus at the lowest Opus price |
| Act mode, routine edits | `claude-sonnet-5` | high (its default) | $0.80 / $4 | half the Opus 5.5 output rate |
| Code review | `claude-opus-5` | high | $2 / $10 | accepts `thinking: disabled` at effort high or lower for short, cheap passes; Opus 5.5 always thinks |
| Long unattended tasks | `claude-fable-5-1` | high | $4 / $20 | Anthropic's model for long-horizon work; the endpoint bills `max` effort at 3× |
| Search and summarization subagents | `claude-sonnet-5` | low | $0.80 / $4 | fast and cheap |

Endpoint prices from the model pages; Anthropic list prices are 2.5× these ([pricing](https://platform.claude.com/docs/en/about-claude/pricing)). All checked 2026-10-07.

## What one agent task costs

Assumed run of a "fix the failing test" task: 25 turns, 1,200,000 cached-read tokens, 90,000 tokens written to the 5-minute cache, 15,000 uncached input tokens and 30,000 output tokens including thinking.

| Model | Anthropic list price | Through the endpoint |
|---|---:|---:|
| `claude-sonnet-5` | $0.80 | $0.32 |
| `claude-opus-5-5` | $1.35 | $0.54 |
| `claude-opus-5` | $1.99 | $0.80 |
| `claude-fable-5-1` | $3.08 | $1.23 |

Cached reads are most of the tokens in an agent loop, so each model's cache-read price moves the total more than its headline input price.

## Troubleshooting

| Symptom | Agent | Cause and fix |
|---|---|---|
| `405 Method Not Allowed` | Cline, OpenCode | base URL lacks `/v1`; enter `https://argolink.io/v1` |
| `404` on `/v1/v1/messages` | Qwen Code, Agent SDK | base URL has `/v1`; use `https://argolink.io` |
| 400 mentioning `budget_tokens` or thinking | Qwen Code | add the `anthropic-adaptive` reasoning profile |
| 400 on `temperature`, `top_p` or `top_k` | any | remove sampling overrides; Claude 4.7 and later reject non-default values |
| Model not found for `claude-sonnet-5-5` or a Haiku model | any | the endpoint serves `claude-sonnet-5` and no Haiku; pick from `GET https://argolink.io/v1/models` |
| Agent run stops early on budget | Agent SDK | the budget is compared with list-price estimates; convert it as the example does |

## FAQ

**Do these agents need a Claude subscription?**
No. Each one sends your endpoint key with every request and bills per token. Cline's separate "Claude Code" provider is the subscription path and is not used here.

**Can I mix Claude with cheaper non-Claude models in the same agent?**
Yes. Cline's OpenAI Compatible provider and OpenCode custom providers take `https://argolink.io/v1` with models such as `glm-5.3` or `deepseek-v4-pro`, so Plan and Act or primary and sub-agents can sit on different vendors.

**Which Claude model IDs does the endpoint serve?**
`claude-opus-5-5`, `claude-opus-5`, `claude-opus-4-8`, `claude-fable-5-1`, `claude-fable-5` and `claude-sonnet-5`, each with a 1M-token context and up to 128K output tokens. `GET https://argolink.io/v1/models` lists them without a key.

**Why does the Agent SDK example pass only two environment variables?**
The Python SDK merges `env` over the parent environment, so the two gateway variables are enough. In TypeScript, `options.env` replaces the environment; spread `process.env` into it.

**Is prompt caching kept?**
The Messages endpoint honors `cache_control`, and cached reads bill at $0.08 to $0.20 per 1M depending on the model. Whether an agent marks its prompts for caching is up to the agent; after a few turns, check that `cache_read_input_tokens` in the usage is growing.

## Run the tests

```bash
pip install pytest
pytest tests/
```

The tests check the agent's options, budget conversion and summary without starting an agent or calling an API.

## License

MIT
