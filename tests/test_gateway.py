import base64
import io
import json
from types import SimpleNamespace

import pytest
import requests
from garmin_personal_api import HttpError

from garmin_mcp.errors import Fault
from garmin_mcp.gateway import (
    BASE,
    TOKEN_PATH,
    GarminSession,
    Gateway,
    MemoryAuthenticator,
    public_error,
)


class Store:
    def __init__(self, value="synthetic-key"):
        self.value = value

    def get(self):
        return self.value


class Auth:
    def __init__(self):
        self.calls = []

    def obtain_token(self, key, force_refresh=False):
        self.calls.append((key, force_refresh))
        return SimpleNamespace(access_token=f"test-token-{len(self.calls)}")


class Client:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_401_refreshes_once_then_returns_data():
    auth = Auth()
    gateway = Gateway(Store(), auth, lambda token: Client())
    calls = []

    def operation(client):
        calls.append(1)
        if len(calls) == 1:
            raise HttpError(status_code=401, method="GET", url="/fake", response_text="secret")
        return {"totalSteps": 5000}

    assert gateway.call(operation) == {"totalSteps": 5000}
    assert [refresh for _, refresh in auth.calls] == [False, True]


def test_persistent_401_cannot_loop_or_leak_response():
    auth = Auth()
    gateway = Gateway(Store(), auth, lambda token: Client())

    def operation(client):
        raise HttpError(status_code=401, method="GET", url="/fake", response_text="PRIVATE_TOKEN")

    with pytest.raises(Fault) as error:
        gateway.call(operation)
    assert len(auth.calls) == 2
    assert error.value.code == "authentication_failed"
    assert "PRIVATE_TOKEN" not in str(error.value)


def test_missing_key_never_calls_network():
    auth = Auth()
    gateway = Gateway(Store(None), auth, lambda token: Client())
    with pytest.raises(Fault, match="GARMIN_PERSONAL_API_KEY"):
        gateway.call(lambda client: None)
    assert auth.calls == []


@pytest.mark.parametrize("status", [400, 401, 403])
def test_rejected_personal_key_does_not_retry_token_endpoint(status):
    class RejectedAuth(Auth):
        def obtain_token(self, key, force_refresh=False):
            self.calls.append((key, force_refresh))
            raise HttpError(
                status_code=status, method="POST", url="/token", response_text="PRIVATE_TOKEN"
            )

    auth = RejectedAuth()
    gateway = Gateway(Store(), auth, lambda token: Client())
    with pytest.raises(Fault) as error:
        gateway.call(lambda client: None)
    assert error.value.code == "authentication_failed"
    assert len(auth.calls) == 1
    assert "PRIVATE_TOKEN" not in str(error.value)


@pytest.mark.parametrize(
    "status,code,retry",
    [
        (400, "garmin_request_failed", False),
        (401, "authentication_failed", False),
        (403, "access_denied", False),
        (404, "garmin_request_failed", False),
        (429, "rate_limited", True),
        (503, "garmin_unavailable", True),
    ],
)
def test_http_error_classification_is_safe(status, code, retry):
    fault = public_error(
        HttpError(
            status_code=status,
            method="GET",
            url="https://private.invalid/key",
            response_text="PRIVATE_TOKEN",
        )
    )
    assert fault.code == code and fault.retryable == retry
    assert "PRIVATE_TOKEN" not in str(fault.as_dict())
    assert "private.invalid" not in str(fault.as_dict())


@pytest.mark.parametrize(
    "method,url",
    [
        ("GET", "https://evil.invalid/test"),
        ("GET", "http://personal.connectapi.garmin.com/test"),
        ("GET", "https://personal.connectapi.garmin.com.evil.invalid/test"),
        ("POST", BASE + "/write"),
        ("DELETE", BASE + "/read"),
        ("GET", "https://secret@personal.connectapi.garmin.com/test"),
        ("GET", BASE + ":444/test"),
    ],
)
def test_external_hosts_and_mutations_are_blocked(method, url):
    with pytest.raises(Fault) as error:
        GarminSession().request(method, url)
    assert error.value.code == "blocked_request"


def test_redirects_are_rejected_and_tls_timeouts_forced(monkeypatch):
    received = []

    def response(self, method, url, **kwargs):
        received.append(kwargs)
        result = requests.Response()
        result.status_code = 302
        result.raw = io.BytesIO(b"")
        result.headers["Location"] = "https://evil.invalid/steal"
        return result

    monkeypatch.setattr(requests.Session, "request", response)
    with pytest.raises(Fault, match="redirect"):
        GarminSession().post(BASE + TOKEN_PATH)
    assert received[0]["allow_redirects"] is False
    assert received[0]["verify"] is True
    assert received[0]["timeout"] == (5, 20)


def test_official_token_cache_is_memory_only_and_refreshes_on_expiry(tmp_path, monkeypatch):
    now = [10000]

    class Session:
        def __init__(self):
            self.calls = []

        def post(self, url, **kwargs):
            self.calls.append(url)
            payload = (
                base64.urlsafe_b64encode(json.dumps({"exp": now[0] + 86400}).encode())
                .decode()
                .rstrip("=")
            )
            return SimpleNamespace(ok=True, text=f"header.{payload}.signature")

        def close(self):
            pass

    session = Session()
    monkeypatch.setenv("GARMIN_PERSONAL_API_BASE_URL", "https://evil.invalid")
    cache = tmp_path / "must-not-exist.json"
    auth = MemoryAuthenticator(session=session, clock=lambda: now[0], bearer_token_cache_file=cache)
    first = auth.obtain_token("synthetic-key")
    assert auth.obtain_token("synthetic-key").access_token == first.access_token
    assert len(session.calls) == 1
    now[0] += 85000
    auth.obtain_token("synthetic-key")
    assert len(session.calls) == 2
    auth.obtain_token("different-key")
    assert len(session.calls) == 3
    assert all(url.startswith(BASE + "/") for url in session.calls)
    assert not cache.exists()


@pytest.mark.parametrize(
    "exception,code",
    [
        (requests.Timeout("secret"), "timeout"),
        (requests.ConnectionError("secret"), "network_error"),
        (ValueError("secret"), "unexpected_error"),
    ],
)
def test_non_http_errors_are_safe(exception, code):
    fault = public_error(exception)
    assert fault.code == code and "secret" not in str(fault.as_dict())
