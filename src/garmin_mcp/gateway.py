import threading
from urllib.parse import urlsplit

import requests
from garmin_personal_api import (
    GarminPersonalApiClient,
    GarminPersonalApiError,
    HttpError,
    PersonalApiAuthenticator,
)

from .credentials import KEY_ENV, EnvironmentCredentials
from .downloads import MAX_DOWNLOAD_BYTES
from .errors import Fault

BASE = "https://personal.connectapi.garmin.com"
TOKEN_PATH = "/personalapitoken-service/personal-api/personal-api-key/token"
MAX_JSON_BYTES = 8 * 1024 * 1024


class GarminSession(requests.Session):
    """Only the documented HTTPS host and read operations are permitted."""

    def __init__(self):
        super().__init__()
        self.trust_env = False  # No .netrc authentication or environment proxy overrides.

    def request(self, method, url, **kwargs):
        parsed = urlsplit(url)
        method = method.upper()
        if (
            parsed.scheme != "https"
            or parsed.hostname != "personal.connectapi.garmin.com"
            or parsed.port not in (None, 443)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or (method != "GET" and not (method == "POST" and parsed.path == TOKEN_PATH))
        ):
            raise Fault("blocked_request", "The request is outside the supported Garmin API.")
        kwargs.update(allow_redirects=False, timeout=(5, 20), verify=True, stream=True)
        response = super().request(method, url, **kwargs)
        if 300 <= response.status_code < 400:
            response.close()
            raise Fault(
                "unexpected_redirect",
                "Garmin returned an unexpected redirect.",
                http_status=response.status_code,
            )
        limit = (
            MAX_DOWNLOAD_BYTES
            if parsed.path.startswith("/download-service/files/activity/")
            else MAX_JSON_BYTES
        )
        try:
            body = bytearray()
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if len(body) + len(chunk) > limit:
                    raise Fault(
                        "response_too_large",
                        "The response exceeded the size limit. Query a smaller date range or page.",
                    )
                body.extend(chunk)
            response._content = bytes(body)
            response._content_consumed = True
            return response
        finally:
            response.close()


class MemoryAuthenticator(PersonalApiAuthenticator):
    """Garmin SDK 1.0.0 cache hooks, deliberately pinned and regression-tested.

    The official token exchange/expiry logic is retained. Tokens never reach disk.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_url = BASE
        self._memory_cache = None

    def _read_cached_token(self, fingerprint):
        if self._memory_cache and self._memory_cache[0] == fingerprint:
            return self._memory_cache[1]
        return None

    def _write_cached_token(self, fingerprint, token):
        self._memory_cache = (fingerprint, token)


def public_error(exc):
    """Do not expose upstream bodies, URLs, request headers, or exception strings."""
    if isinstance(exc, Fault):
        return exc
    if isinstance(exc, HttpError):
        status = exc.status_code
        if status == 401:
            return Fault(
                "authentication_failed",
                f"The Garmin key or token was rejected. Update {KEY_ENV} and restart the server.",
                False,
                status,
            )
        if status == 403:
            return Fault(
                "access_denied",
                "Garmin denied this request. Check API access and key permissions.",
                False,
                status,
            )
        if status == 429:
            return Fault(
                "rate_limited",
                "Garmin rate-limited this request. Wait before retrying.",
                True,
                status,
            )
        if status >= 500:
            return Fault("garmin_unavailable", "Garmin is temporarily unavailable.", True, status)
        return Fault(
            "garmin_request_failed",
            "Garmin rejected this query; this does not mean the measurement is zero or absent.",
            False,
            status,
        )
    if isinstance(exc, requests.Timeout):
        return Fault("timeout", "Garmin did not respond within the timeout.", True)
    if isinstance(exc, requests.exceptions.JSONDecodeError):
        return Fault("schema_changed", "Garmin returned a response that was not valid JSON.")
    if isinstance(exc, requests.RequestException):
        return Fault("network_error", "The secure connection to Garmin failed.", True)
    if isinstance(exc, GarminPersonalApiError):
        return Fault(
            "invalid_api_response", "Garmin returned an unexpected authentication response."
        )
    return Fault(
        "unexpected_error",
        "The operation could not be completed. No credentials or upstream response bodies were logged.",
    )


class Gateway:
    def __init__(self, store=None, authenticator=None, client_factory=None):
        self.store = store or EnvironmentCredentials()
        self.authenticator = authenticator or MemoryAuthenticator(session=GarminSession())
        self.client_factory = client_factory or self._client
        self._lock = threading.RLock()

    @staticmethod
    def _client(token):
        client = GarminPersonalApiClient(token, session=GarminSession())
        client.base_url = BASE
        return client

    def call(self, operation):
        # requests.Session and the memory token cache are shared, so serialize access.
        with self._lock:
            try:
                key = self.store.get()
                if not key:
                    raise Fault(
                        "not_authenticated",
                        f"Set {KEY_ENV} in your MCP server environment, then restart the server.",
                    )
                for attempt in range(2):
                    try:
                        try:
                            token = self.authenticator.obtain_token(
                                key, force_refresh=bool(attempt)
                            )
                        except HttpError as exc:
                            if exc.status_code in {400, 401, 403}:
                                raise Fault(
                                    "authentication_failed",
                                    f"Garmin rejected the Personal API key. Update {KEY_ENV} and restart the server.",
                                    False,
                                    exc.status_code,
                                ) from None
                            raise
                        with self.client_factory(token.access_token) as client:
                            return operation(client)
                    except HttpError as exc:
                        if exc.status_code != 401 or attempt:
                            raise
            except Exception as exc:
                raise public_error(exc) from None

    def close(self):
        self.authenticator.close()
        self.authenticator._memory_cache = None
