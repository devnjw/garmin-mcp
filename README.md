# Garmin MCP

A local MCP server for **all 26 documented Garmin Connect Personal API GET endpoints**, plus **8 convenient summary tools**. Runs on **macOS, Windows and Linux** with an API key supplied through an environment variable. Uses Garmin's official Python client. Independent community project; not affiliated with or endorsed by Garmin.

[한국어 설치 안내](docs/INSTALL.ko.md) · [All tools and API coverage](docs/API.md) · [Security and privacy](SECURITY.md) · [Contributing](CONTRIBUTING.md)

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git — uv runs Git when installing from a `git+https` source, so the Quick Start needs both too.
- Python **3.12.4 or newer**; tested on 3.12, 3.13 and 3.14. uv can provision Python for you.
- Your own [Garmin Connect Personal API key](https://connect.garmin.com/app/settings/personalApiToken).
- An MCP client supporting local STDIO servers, such as Claude Desktop, Cursor or Codex.

## Quick Start with uvx (no clone)

Run the server without cloning this repository or creating a virtualenv. With [uv](https://docs.astral.sh/uv/getting-started/installation/) installed, this is the whole setup:

```sh
uvx --from git+https://github.com/devnjw/garmin-mcp garmin-mcp
```

uvx builds the package from this GitHub repository and caches the result: the first run takes a minute, later runs start from cache. Re-running the command picks up recent commits on this repository. You can also pin a version with `git+https://github.com/devnjw/garmin-mcp@v0.2.0`.

> **Important:** an unrelated package by another author already holds the name `garmin-mcp` on PyPI. Plain `uvx garmin-mcp`, `pip install garmin-mcp`, or anything without this git URL does **not** install this project. Always go through `git+https://github.com/devnjw/garmin-mcp`.

### Claude Desktop

Add this to `claude_desktop_config.json` (Claude Desktop → Settings → Developer → Edit Config), then restart Claude Desktop:

```json
{
  "mcpServers": {
    "garmin": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/devnjw/garmin-mcp", "garmin-mcp"],
      "env": {
        "GARMIN_PERSONAL_API_KEY": "YOUR_GARMIN_PERSONAL_API_KEY",
        "GARMIN_MCP_TIMEZONE": "Europe/Berlin"
      }
    }
  }
}
```

### Cursor and Windsurf

The same shape goes into Cursor's `~/.cursor/mcp.json` (MCP → Add new global MCP server) or Windsurf's `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "garmin": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/devnjw/garmin-mcp", "garmin-mcp"],
      "env": {
        "GARMIN_PERSONAL_API_KEY": "YOUR_GARMIN_PERSONAL_API_KEY",
        "GARMIN_MCP_TIMEZONE": "Europe/Berlin"
      }
    }
  }
}
```

On Windows, `uvx` is on your `PATH` after installing uv; no Python installation is needed beforehand, but Git for Windows is required for the `git+https` source. Set `GARMIN_MCP_TIMEZONE` to your IANA timezone (for example `Asia/Seoul`); see [Timezone](#timezone). Note a literal key in a client configuration is stored as plaintext by that client; keep that file private, outside Git, and out of chat or issue reports.

## What can you ask Claude?

Once connected, natural questions work out of the box. A few to start with:

- **Recovery check before training:** "Read my sleep, HRV and Body Battery from last night. If my HRV is below my recent baseline, suggest an easy session instead of a hard run."
- **Weekly training load:** "Summarize my last four weeks of runs — distance, time and training effect — and tell me if I'm ramping up faster than I recover. Include missing days."
- **Sleep stage comparison:** "Compare my deep and REM sleep minutes over the last 30 days. Which nights were worst, and how did evening stress and activity differ on those days?"
- **Energy patterns:** "Show my Body Battery pattern for the last 14 days and point out when I drain fastest during the day."

The 26 raw `garmin_api_*` tools cover anything more specific — heart-rate zones, weight trends, food logs, activity ZIP downloads. These prompts ask for analysis, not medical advice.

## Install from source

The same commands work in a POSIX shell or Windows PowerShell:

```sh
git clone https://github.com/devnjw/garmin-mcp.git
cd garmin-mcp
uv sync --frozen --no-dev --python 3.12 --no-editable
```

The installed executable is `.venv/bin/garmin-mcp` on macOS/Linux or `.venv/Scripts/garmin-mcp.exe` on Windows. Keep the clone in place and use an **absolute path** in your MCP client. This project is distributed through GitHub; do not assume an identically named PyPI package belongs to this repository. The clone install pins the code locally and suits development and restricted environments; the uvx route above is simpler for everyday use.

## Configure your API key

Set **`GARMIN_PERSONAL_API_KEY` in the MCP server's environment**. The server never saves the key, prompts for it, reads a keychain, or automatically loads `.env` files. Access tokens remain in process memory.

The simplest setup is the MCP client's per-server `env` configuration. **A literal key in a client configuration is stored as plaintext by that client.** Keep that file private, outside Git, and out of chat or issue reports. Alternatively, have your shell or secret manager supply the environment variable at launch.

### Codex

Add this to your user-level `~/.codex/config.toml`, replacing the path and placeholder locally:

```toml
[mcp_servers.garmin]
command = "/absolute/path/to/garmin-mcp/.venv/bin/garmin-mcp"
tool_timeout_sec = 180

[mcp_servers.garmin.env]
GARMIN_PERSONAL_API_KEY = "YOUR_GARMIN_PERSONAL_API_KEY"
GARMIN_MCP_TIMEZONE = "Europe/Berlin"
```

For Windows, use a TOML literal string for the command, for example:

```toml
command = 'C:\Users\YOUR_USER\garmin-mcp\.venv\Scripts\garmin-mcp.exe'
```

To keep the key out of the configuration file, **omit the key from `env`** and add `env_vars = ["GARMIN_PERSONAL_API_KEY"]` directly under `[mcp_servers.garmin]`. The Codex process must already have that environment variable; setting it in an unrelated terminal does not update a running desktop app. These alternatives are documented in [Codex's official MCP guide](https://learn.chatgpt.com/docs/extend/mcp#stdio-servers).

On macOS/Linux, restrict a configuration containing a key with `chmod 600 ~/.codex/config.toml`. On Windows, keep the file under your private user profile with access limited to your account and administrators. Restart the `garmin` MCP server after changing settings. Ask it to call `garmin_status(verify=true)` to verify authentication without returning profile data.

### Other STDIO clients

For clients accepting an `mcpServers` JSON configuration — the uvx form below needs no clone:

```json
{
  "mcpServers": {
    "garmin": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/devnjw/garmin-mcp", "garmin-mcp"],
      "env": {
        "GARMIN_PERSONAL_API_KEY": "YOUR_GARMIN_PERSONAL_API_KEY",
        "GARMIN_MCP_TIMEZONE": "Europe/Berlin"
      }
    }
  }
}
```

Or point `command` at the clone install instead:

```json
{
  "mcpServers": {
    "garmin": {
      "command": "/absolute/path/to/garmin-mcp/.venv/bin/garmin-mcp",
      "env": {
        "GARMIN_PERSONAL_API_KEY": "YOUR_GARMIN_PERSONAL_API_KEY",
        "GARMIN_MCP_TIMEZONE": "Europe/Berlin"
      }
    }
  }
}
```

On Windows, use the `.exe` path and escape backslashes in JSON (`C:\\Users\\...`) or use forward slashes. Environment-variable interpolation such as `${VAR}` is client-specific; this server does not expand it.

### Check from a terminal

With the key already present in that terminal's environment, run:

```sh
# uvx install:
uvx --from git+https://github.com/devnjw/garmin-mcp garmin-mcp check

# clone install:
uv run --frozen --no-dev garmin-mcp check
```

`check` verifies authentication and today's summary plus recent sleep, HRV, Body Battery and activities. It prints statuses and counts, not measurements or credentials. A key configured only in your MCP client is not automatically available in a separate terminal. The default command, or `serve`, starts STDIO MCP; `--version` reports the package version.

### Timezone

Set `GARMIN_MCP_TIMEZONE` to your IANA timezone, such as `America/New_York` or `Asia/Seoul`. Without it, a system `/etc/localtime` zoneinfo link is used when available; otherwise the default is **UTC**, including Windows. The bundled `tzdata` dependency provides IANA zones on Windows. Garmin calendar dates are preserved; summary timestamps use the selected timezone.

Try: “Show my sleep, HRV and workouts for the last seven days, including missing dates.”

## What is supported?

**Summary tools:** `garmin_status`, `garmin_daily_summary`, `garmin_sleep`, `garmin_hrv`, `garmin_body_battery`, `garmin_activities`, `garmin_activity`, `garmin_day`.

**Full API tools:** 26 `garmin_api_*` tools expose all operations and documented parameters in the official Personal API 1.0.0 Swagger snapshot checked on 2026-10-24. This includes every documented activity-search filter, original JSON fields, profile, food logs, menstrual health, heart-rate zones, weight endpoints and original activity ZIP downloads. [Complete mapping and limits](docs/API.md).

- Summary ranges default to seven days and allow 90 days, split into 31-day requests.
- Raw range tools default to seven days and allow 31 days per call. Query consecutive intervals for longer history; raw responses are not merged or silently truncated.
- Raw activity search allows 1–100 records per page and all documented filters, with `next_start`. Its date filters can span longer history.
- Raw JSON preserves Garmin field names, units, nulls, negative sentinels and placeholders. Use summary tools for normalized metrics and explicit missing dates.
- `garmin_api_download_activity` creates a new private ZIP file, never extracts or overwrites files, and returns its path/size/hash. Files can contain GPS tracks.
- `garmin_api_heart_rate_zones` defaults `generate_defaults` to false. Explicitly enabling it may generate zone settings in Garmin. This tool and the local download tool are marked as potentially writing; the other 32 tools are marked read-only.

API coverage does not imply that every Garmin app feature is available, every device records every metric, or every account has data for every endpoint. There are no workout-upload or record-editing endpoints in this API snapshot. Empty data and denied access remain distinguishable.

**Known live-API limitation:** `weight/all` returned HTTP 400 during verification even with documented ISO dates. Its tool preserves the error and suggests `garmin_api_weight_range(include_all=true)`, which succeeded. It does not silently change endpoints or response shapes. [Verification details](docs/VERIFICATION.md).

## Why the official API instead of a scraper?

Many Garmin MCP servers log in with your Garmin **username and password** against undocumented, reverse-engineered web endpoints. That gives a tool your full account credentials and breaks whenever Garmin changes its private web API. This server takes a different path:

- **Official Personal API token only.** You create your own API key in Garmin Connect; the server uses Garmin's documented, supported Personal API. No password is ever requested, seen or handled by this code.
- **Nothing stored.** The only credential is `GARMIN_PERSONAL_API_KEY`, supplied through the environment and kept in process memory. There is no token cache file, no keychain write and no telemetry. Revoke the key in Garmin Connect when you are done.
- **Independently reviewed.** M8ven Tool Trust lists this repository as **Code Verified** on the [M8ven Trust Index](https://m8ven.ai/mcp/devnjw/garmin-mcp): all 34 tools' handlers verified to match their declared behavior, 32 read-only tools confirmed free of write/delete/exec, and no credential exfiltration, sensitive file access or obfuscation found (static and behavioral review of commit `fbe5127`, October 2026). That is an automated review, not a formal security audit; the full self-description of the security model is in [SECURITY.md](SECURITY.md).

## Privacy and storage

| Item | Location |
| --- | --- |
| Personal API key | Environment supplied by your MCP client; never saved by this server |
| Access token | Process memory only; no SDK token cache file |
| Installed runtime | `.venv` inside the clone |
| Downloads on macOS/Linux | `~/.local/share/garmin-mcp/downloads` (directory 0700, files 0600) |
| Downloads on Windows | `%LOCALAPPDATA%/garmin-mcp/downloads/<unique-directory>` (current-user/administrator ACL) |
| Ordinary API responses | Returned to the MCP client; no server-side database or response log |

Downloads are saved only on explicit tool calls, never extracted, and never overwrite existing files. Use a local filesystem supporting native permissions (NTFS on Windows) for private downloads. Data returned through MCP is available to your AI client/model and may be retained by that client. Raw tools can return identifiers, GPS and sensitive health information. There is no telemetry or hosted relay. Only Garmin's documented HTTPS host is contacted during use; uv contacts package sources during installation.

Garmin describes the Personal API as access to an individual's own data, not a commercial multi-user service. Distributing this client does not change those terms. See [Garmin's FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/).

## Update and troubleshoot

```sh
git pull --ff-only
uv sync --frozen --no-dev --python 3.12 --no-editable --reinstall-package garmin-mcp
```

Restart the MCP server after updating. Your client-managed environment settings are unaffected. If a key expires or is revoked, replace `GARMIN_PERSONAL_API_KEY` and restart.

- `not_authenticated`: the launched server has no key. Check its `env` or the client's environment forwarding.
- `invalid_api_key`: remove whitespace, line breaks or other non-key characters from the value.
- `authentication_failed`: create a fresh Personal API key, update the environment and restart.
- `access_denied`: Garmin declined access; this is not an empty measurement.
- `rate_limited`: wait before retrying; the server does not loop on HTTP 429.
- `response_too_large`: use a smaller range or page. Limits are 8 MiB for JSON and 64 MiB for ZIPs.
- `schema_changed`: report the tool and sanitized structural details, without a private API response.

For existing macOS/Linux installations using `scripts/install.sh` and `scripts/run.sh`, those compatibility launchers remain available. They install into `~/.local/share/garmin-mcp/venv` and now pass through the environment key. The old interactive `auth` command has been removed. When moving from the initial macOS-only release, set your key in the client environment and clone afresh because the repository history was reset; old clones cannot update with `git pull --ff-only`. An obsolete `garmin-mcp` Keychain item can be deleted after the new setup works; the server never reads it.

To uninstall, remove the MCP server configuration and its key, delete the clone and any downloads or compatibility runtime. Revoke the key in Garmin Connect when no longer needed.

## Development and verification

```sh
uv sync --frozen --python 3.12
uv run --frozen pytest -q
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv build
```

CI covers macOS, Windows and Linux with Python 3.12, 3.13 and 3.14. Tests use synthetic fixtures without Garmin credentials. They exercise the real MCP protocol, all endpoint/parameter mappings, environment authentication, platform-specific downloads and summary regressions. See [verification scope](docs/VERIFICATION.md).

## License

[Apache-2.0](LICENSE). Garmin's official [`garmin-connect-personal-api-python`](https://github.com/garmin/connect-personal-api-python) dependency is also Apache-2.0. See [third-party notices](THIRD_PARTY_NOTICES.md).
