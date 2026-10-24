#!/bin/sh
set -eu
umask 077
if ! command -v uv >/dev/null 2>&1; then
  printf '%s\n' 'Install uv first: https://docs.astral.sh/uv/getting-started/installation/' >&2
  exit 1
fi
garmin_project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export UV_PROJECT_ENVIRONMENT="$HOME/.local/share/garmin-mcp/venv"
cd "$garmin_project_dir"
uv sync --frozen --python 3.12 --no-dev --no-editable --reinstall-package garmin-mcp
printf '%s\n' 'Installed. Register scripts/run.sh as a STDIO MCP server in Codex.'
