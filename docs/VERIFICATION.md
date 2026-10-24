# Verification scope

Verification was performed on 2026-10-24. The environment-only release is version 0.2.0.

## Automated

- 145 collected tests (platform-specific cases run on their respective OS) with synthetic data and network requests disabled during ordinary tests.
- Independent official-contract comparison: 26 GET paths, every parameter name/type/location and all 26 detailed MCP signatures.
- Official SDK routing and parameter forwarding for all 25 JSON endpoints; the ZIP endpoint is separately exercised using a synthetic archive.
- Real MCP STDIO initialization, discovery and successful synthetic calls to all 34 tools, plus error/annotation checks.
- Summary date boundaries, timezone conversion/DST, missing values versus real zeroes, sleep null placeholders and nap-only dates, pagination, partial failures, and rate-limit behavior.
- Environment credential loading, missing/malformed values, no implicit dotenv loading or credential persistence, status/CLI redaction, token caching/refresh and safe errors.
- Request host/method/TLS/redirect restrictions, streamed response-size limits, ZIP validation, POSIX private permissions, native Windows ACL/junction checks, partial-write cleanup, symlink rejection and non-extraction.
- Ruff lint/format checks, dependency consistency, source/wheel builds and package-content checks.

CI runs on macOS, Windows and Linux with Python 3.12, 3.13 and 3.14 (nine combinations). CI uses no Garmin account, API key or real health fixtures. Build artifacts contain the API catalog and license.

## Live account smoke testing

All 26 documented endpoint request paths were exercised against Garmin using one local account. **25 returned successful HTTP responses**, including the original activity ZIP download. An empty successful response counts as a successful request, not evidence that the account had measurements. The temporary verification download was deleted; no health responses or credentials are included in this repository.

The documented `GET /weight-service/weight/all/{startDate}/{endDate}` returned **HTTP 400 with an empty error object** for valid ISO date intervals. The same failure occurred when called directly through the official client, outside MCP. This establishes a limitation observed with that account/request; it does not prove the cause or affect all accounts. The server exposes the exact documented endpoint and preserves this error. Its error response suggests an explicit alternative: `garmin_api_weight_range(..., include_all=true)`, which succeeded in local verification. The two endpoint response schemas differ, so no automatic substitution is performed.

Live checks also confirmed the existing summary tools after authentication. Some dates lacked sleep or HRV records and remained explicitly partial/missing. These checks do not compare every returned value to Garmin's UI, cover every device/entitlement, test every filter combination against real data, or establish historical completeness.

## Release boundary

This release claims **26/26 endpoint and documented-parameter implementations**, not 26 endpoints guaranteed to return measurements for every account. Authentication uses the same environment variable on all supported platforms. The server does not manage a persistent credential store. Security regression tests are not an independent security audit.
