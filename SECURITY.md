# Security and privacy

This is a local, single-user client for personal Garmin data. It does not provide a shared account, cloud relay or hosted multi-user service.

- The only credential input is `GARMIN_PERSONAL_API_KEY`. The server never persists the key, reads an OS credential store, automatically loads `.env`, or accepts a key as an MCP tool argument. The MCP host or user chooses how to store and supply it.
- Environment variables are not encrypted storage. A literal key in client JSON/TOML or a `.env` file is plaintext. Restrict access to those files, exclude them from version control, and avoid putting keys in shell arguments, history, chat, debug dumps or issue reports. Processes with sufficient access to your account can read its credentials.
- Garmin's official authentication/token-expiry implementation is reused. Its two cache hooks keep tokens in memory; SDK version 1.0.0 is pinned and tested. Restart after updating the client environment.
- HTTPS requests are restricted to `personal.connectapi.garmin.com`, with certificate verification, redirects disabled, timeouts, response-size limits, and no `.netrc` or environment-proxy authentication. Only named documented GET routes and the authentication POST are exposed.
- Upstream exception text, headers, bodies and tokens are not included in tool errors. Ordinary responses are not persisted by the server. Results are sent to the MCP client/model; consult that client's retention settings.
- Raw tools preserve original data, including identifiers, GPS coordinates and sensitive health information. Summary tools deliberately expose fewer fields.
- Downloads use exclusive filenames in a fixed user application directory and are never extracted. On macOS/Linux the directory is opened without following a symlink, directory permissions are 0700 and files 0600. On Windows each download gets a new directory created with a protected current-user/administrator ACL using Python 3.12.4+ `mkdir(0700)`; files inherit that ACL. Existing download-root symlinks and Windows junctions are rejected. Use a local filesystem supporting native access controls, not a shared or permissionless filesystem. This does not isolate the server from malicious processes running as the same user or an administrator.
- Heart-rate zone lookup can create settings when `generate_defaults=true`. The default is false and its MCP annotation allows client review. The download tool also has a write annotation because it creates a local file.
- Credentials and real health fixtures must never be committed. Tests and CI use synthetic fixtures without Garmin network access.

For security-sensitive reports, use the repository's private vulnerability reporting feature if available. Do not disclose credentials or health records in public issues. For ordinary bugs, include the tool name, package/Python/OS versions, safe error code and a synthetic reproduction. Revoke exposed keys in Garmin Connect.

This project has automated security regression tests; it has not undergone an independent security audit.
