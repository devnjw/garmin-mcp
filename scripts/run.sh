#!/bin/sh
set -eu
umask 077
export GARMIN_PERSONAL_API_BASE_URL=https://personal.connectapi.garmin.com
garmin_python="$HOME/.local/share/garmin-mcp/venv/bin/python"
if [ ! -x "$garmin_python" ]; then
  printf '%s\n' 'Garmin MCP is not installed. Run scripts/install.sh first.' >&2
  exit 1
fi
exec "$garmin_python" -I -m garmin_mcp.cli "$@"
