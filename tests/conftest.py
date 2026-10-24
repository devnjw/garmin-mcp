import json
from datetime import UTC, datetime

import pytest
import requests
from garmin_personal_api import GarminPersonalApiClient

from garmin_mcp import data
from garmin_mcp.service import Service


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = datetime(2026, 10, 23, 16, tzinfo=UTC)
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)


@pytest.fixture(autouse=True)
def no_network_and_fixed_clock(monkeypatch):
    monkeypatch.setenv("GARMIN_MCP_TIMEZONE", "Asia/Seoul")
    monkeypatch.delenv("GARMIN_PERSONAL_API_KEY", raising=False)

    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected network access during tests")

    monkeypatch.setattr(requests.Session, "request", forbidden)
    monkeypatch.setattr(data, "datetime", FixedDateTime)


class RouteSession:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs.get("params")))
        for path, result in self.routes.items():
            if path in url:
                if isinstance(result, Exception):
                    raise result
                value = result(url, kwargs) if callable(result) else result
                response = requests.Response()
                response.status_code = 200
                response._content = (
                    value
                    if isinstance(value, bytes)
                    else json.dumps(value).encode()
                    if value is not None
                    else b""
                )
                return response
        raise AssertionError(f"No fake route for {url}")

    def close(self):
        pass


class TestGateway:
    __test__ = False

    def __init__(self, client):
        self.client = client

    def call(self, operation):
        return operation(self.client)


@pytest.fixture
def make_service():
    def create(routes):
        session = RouteSession(routes)
        client = GarminPersonalApiClient("synthetic-test-token", session=session)
        return Service(TestGateway(client)), session, client

    return create
