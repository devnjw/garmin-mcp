import io

import pytest
import requests

from garmin_mcp import data, gateway, settings
from garmin_mcp.errors import Fault


def test_timezone_is_configurable_and_day_changes_with_zone(monkeypatch):
    monkeypatch.setenv("GARMIN_MCP_TIMEZONE", "America/Los_Angeles")
    assert data.day().isoformat() == "2026-10-23"
    assert data.utc_to_local("2026-10-24T01:00:00Z") == "2026-10-23T18:00:00-07:00"
    assert settings.timezone_name() == "America/Los_Angeles"


def test_timezone_honors_daylight_saving(monkeypatch):
    monkeypatch.setenv("GARMIN_MCP_TIMEZONE", "Europe/Berlin")
    assert data.utc_to_local("2026-01-01T00:00:00Z").endswith("+01:00")
    assert data.utc_to_local("2026-07-01T00:00:00Z").endswith("+02:00")


def test_invalid_timezone_has_safe_error(monkeypatch):
    monkeypatch.setenv("GARMIN_MCP_TIMEZONE", "../../private")
    with pytest.raises(Fault) as error:
        settings.timezone()
    assert error.value.code == "invalid_timezone"
    assert "private" not in error.value.message


def test_system_timezone_falls_back_to_utc(monkeypatch):
    monkeypatch.delenv("GARMIN_MCP_TIMEZONE")
    monkeypatch.setattr(
        settings.Path, "resolve", lambda *args, **kwargs: settings.Path("/nonstandard/tzfile")
    )
    assert settings.timezone_name() == "UTC"


def streamed_response(content, status=200):
    response = requests.Response()
    response.status_code = status
    response.raw = io.BytesIO(content)
    return response


def test_transport_caps_streamed_json_without_trusting_content_length(monkeypatch):
    response = streamed_response(b"123456789")
    response.headers["Content-Length"] = "1"
    monkeypatch.setattr(requests.Session, "request", lambda *args, **kwargs: response)
    monkeypatch.setattr(gateway, "MAX_JSON_BYTES", 5)
    with pytest.raises(Fault) as error:
        gateway.GarminSession().get(gateway.BASE + "/userprofile-service/userprofile/settings")
    assert error.value.code == "response_too_large"
    assert response.raw.closed


def test_transport_materializes_capped_response_for_official_sdk(monkeypatch):
    observed = {}
    response = streamed_response(b'{"synthetic":true}')

    def request(*args, **kwargs):
        observed.update(kwargs)
        return response

    monkeypatch.setattr(requests.Session, "request", request)
    result = gateway.GarminSession().get(gateway.BASE + "/userprofile-service/userprofile/settings")
    assert result.json() == {"synthetic": True}
    assert observed["stream"] is True and observed["verify"] is True
    assert observed["allow_redirects"] is False
    assert result._content_consumed


def test_invalid_timezone_returns_tool_error_before_network(monkeypatch, make_service):
    from garmin_mcp.api import ApiService

    monkeypatch.setenv("GARMIN_MCP_TIMEZONE", "invalid/zone")
    service, session, _ = make_service({})
    for result in (
        service.execute("daily_summary"),
        ApiService(service.gateway).execute("profile"),
    ):
        assert not result["ok"] and result["error"]["code"] == "invalid_timezone"
        assert result["timezone"] is None
    assert session.calls == []
