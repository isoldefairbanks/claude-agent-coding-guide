#!/usr/bin/env bash
# Point the Cline CLI at Claude models on an Anthropic-compatible endpoint.
# Cline's Anthropic provider is built on @ai-sdk/anthropic, so the base URL ends in /v1.
set -euo pipefail
: "${ANTHROPIC_API_KEY:?export ANTHROPIC_API_KEY first}"

npm i -g cline
cline auth -p anthropic -k "$ANTHROPIC_API_KEY" -m claude-opus-5-5 -b https://argolink.io/v1
cline config                      # confirm the provider, model and base URL

# One-off runs on another model, headless with JSON events:
#   cline -m claude-sonnet-5 --thinking high "Run the tests and fix any failures"
#   git diff origin/main | cline -m claude-opus-5 "Review these changes for bugs"
