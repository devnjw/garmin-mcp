# Contributing

Use macOS, Windows or Linux and Python 3.12.4+ (CI covers 3.12–3.14). Install development dependencies with `uv sync --frozen`. Run pytest, Ruff lint and format checks, and `uv build` before opening a pull request. Keep dependency updates explicit in `uv.lock`.

## API changes

`src/garmin_mcp/api_catalog.json` is the runtime allowlist, including every documented parameter. `api_tools.py` provides explicit MCP signatures. `tests/fixtures/official_endpoints.json` is an independent structural snapshot derived from the official Swagger source on the recorded date. Tests compare the implementation's paths, parameter names/types/locations, and tool signatures to that snapshot.

When Garmin updates its API, inspect the official Swagger, update the catalog/signatures/contract deliberately, and update the coverage table. Keep all eight summary tool names compatible. Do not turn the allowlist into an arbitrary URL or arbitrary path proxy.

Raw API tools preserve original JSON. Summary normalizers distinguish zero from missing values, preserve Garmin calendar dates, and state incomplete coverage. Test new response shapes with small synthetic fixtures, including missing/partial/error cases. Do not copy real account responses into fixtures, issues, snapshots or logs.

Keep authentication environment-only through `GARMIN_PERSONAL_API_KEY`. Do not add hidden OS credential lookups, implicit dotenv loading, credential persistence or key-valued CLI/tool arguments. Test that missing/malformed keys cannot trigger a network request or leak values. Keep platform-specific filesystem operations covered on their native CI runners. SDK authentication uses private cache hooks; verify those hooks whenever the official SDK is upgraded.

Live testing is optional and local: supply your own key through the environment and run `uv run --frozen garmin-mcp check`. Never add credentials as CI secrets just to make tests pass. A successful API call on one account does not establish coverage for every device, metric or subscription.
