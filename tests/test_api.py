import inspect
import json
import re
from pathlib import Path

import pytest
import requests
from garmin_personal_api import HttpError

from garmin_mcp.api import ENDPOINTS, ApiService, prepare

OFFICIAL = json.loads((Path(__file__).parent / "fixtures/official_endpoints.json").read_text())


def snake(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def test_all_official_paths_parameters_and_mcp_signatures_are_covered():
    from garmin_mcp.api_tools import register_api_tools

    registered = {}

    class Registry:
        def tool(self, **options):
            def register(function):
                registered[function.__name__] = function
                return function

            return register

    register_api_tools(Registry(), None)
    assert len(ENDPOINTS) == len(OFFICIAL) == len(registered) == 26
    assert {e["path"] for e in ENDPOINTS.values()} == {e["path"] for e in OFFICIAL}
    for original in OFFICIAL:
        endpoint = next(e for e in ENDPOINTS.values() if e["path"] == original["path"])
        assert endpoint["method"] == original["method"] == "GET"
        actual = {p["name"]: p for p in endpoint["parameters"]}
        assert set(actual) == {p["name"] for p in original["parameters"]}
        assert set(inspect.signature(registered[endpoint["tool"]]).parameters) == {
            snake(p["name"]) for p in original["parameters"]
        }
        for param in original["parameters"]:
            mapped = actual[param["name"]]
            assert mapped["type"] == param["schema"]["type"]
            assert mapped["in"] == param["in"]
            assert mapped["required"] == param.get("required", False)
            assert mapped.get("format") == param["schema"].get("format")


def sample(param):
    name, schema = param["name"], param["schema"]
    special = {
        "start": 0,
        "limit": 2,
        "favorite": 1,
        "sortOrder": "desc",
        "upperLatitude": 40.0,
        "lowerLatitude": 30.0,
        "leftLongitude": 120.0,
        "rightLongitude": 130.0,
    }
    if name in special:
        return special[name]
    if schema.get("format") == "date":
        return "2026-10-20"
    return {
        "integer": 42,
        "number": 2.5,
        "boolean": True,
        "string": "running",
        "array": ["one", "two"],
    }[schema["type"]]


@pytest.mark.parametrize(
    "original",
    [e for e in OFFICIAL if "download-service" not in e["path"]],
    ids=lambda e: e["path"],
)
def test_every_json_endpoint_forwards_all_documented_parameters_and_preserves_response(
    original, make_service
):
    expected_path = original["path"]
    expected_params = {}
    arguments = {}
    for parameter in original["parameters"]:
        value = sample(parameter)
        arguments[snake(parameter["name"])] = value
        if parameter["in"] == "path":
            expected_path = expected_path.replace("{" + parameter["name"] + "}", str(value))
        else:
            expected_params[parameter["name"]] = (
                str(value).lower() if type(value) is bool else value
            )
    raw = {"unknownFutureField": {"value": -1, "items": [None, 0, "synthetic"]}}
    service, session, _ = make_service({expected_path: raw})
    endpoint = next(e for e in ENDPOINTS.values() if e["path"] == original["path"])
    result = ApiService(service.gateway).execute(endpoint["id"], **arguments)
    assert result["ok"], result
    assert result["data"] == raw
    assert result["format"] == "garmin_raw_json"
    assert session.calls == [
        ("https://personal.connectapi.garmin.com" + expected_path, expected_params or None)
    ]


def test_repeated_activity_filters_and_boolean_encoding_use_real_requests_encoder():
    path, params, _ = prepare(
        ENDPOINTS["activity_search"],
        {
            "excluded_activity_sub_type": ["trail_running", "road_cycling"],
            "required_field": ["distance", "averageHR"],
            "exclude_children": False,
        },
    )
    url = (
        requests.Request("GET", "https://personal.connectapi.garmin.com" + path, params=params)
        .prepare()
        .url
    )
    assert "excludedActivitySubType=trail_running&excludedActivitySubType=road_cycling" in url
    assert "requiredField=distance&requiredField=averageHR" in url
    assert "excludeChildren=false" in url


@pytest.mark.parametrize(
    "endpoint,args",
    [
        ("activity", {"activity_id": "../profile"}),
        ("activity", {"activity_id": True}),
        ("activity", {"activity_id": -1}),
        ("activity", {}),
        ("steps", {"start_date": "2026-09-01", "end_date": "2026-10-20"}),
        ("steps", {"start_date": "2026-10-21", "end_date": "2026-10-20"}),
        ("sleep_daily", {"date": "2026-02-30"}),
        ("activity_search", {"limit": 101}),
        ("activity_search", {"start": -1}),
        ("activity_search", {"favorite": 2}),
        ("activity_search", {"sort_order": "random"}),
        ("activity_search", {"upper_latitude": 40}),
        ("activity_search", {"min_duration": -1}),
        ("activity_search", {"min_distance": 100, "max_distance": 10}),
        ("activity_search", {"required_field": ["good", 12]}),
        ("activity_search", {"upper_latitude": float("nan")}),
        ("heart_rate_zones", {"generate_defaults": "true"}),
        ("profile", {"url": "https://other.invalid"}),
        ("https://other.invalid", {}),
    ],
)
def test_invalid_parameters_never_contact_garmin(endpoint, args, make_service):
    service, session, _ = make_service({})
    result = ApiService(service.gateway).execute(endpoint, **args)
    assert not result["ok"]
    assert session.calls == []


def test_safe_defaults_and_raw_search_support_long_history():
    _, params, _ = prepare(ENDPOINTS["heart_rate_zones"], {})
    assert params == {"generateDefaults": "false"}
    _, params, values = prepare(ENDPOINTS["sleep_summaries"], {})
    assert params == {"startDate": "2026-10-18", "endDate": "2026-10-24"}
    _, params, _ = prepare(
        ENDPOINTS["activity_search"], {"start_date": "2000-01-01", "end_date": "2026-10-24"}
    )
    assert params["limit"] == 20 and params["startDate"] == "2000-01-01"


def test_raw_activity_pagination(make_service):
    service, _, _ = make_service({"/activities/search/": [{"activityId": 42}, {"activityId": 43}]})
    result = ApiService(service.gateway).execute("activity_search", start=10, limit=2)
    assert result["pagination"] == {"start": 10, "limit": 2, "next_start": 12}


def test_raw_failure_does_not_masquerade_as_no_data_or_leak_upstream(make_service):
    service, _, _ = make_service(
        {
            "/dailyHeartRate": HttpError(
                status_code=403,
                method="GET",
                url="private",
                response_text="SYNTHETIC_PRIVATE_TOKEN",
            )
        }
    )
    result = ApiService(service.gateway).execute("heart_rate")
    assert not result["ok"] and result["error"]["code"] == "access_denied"
    assert "SYNTHETIC_PRIVATE_TOKEN" not in json.dumps(result)


@pytest.mark.parametrize("raw", [None, [], {}])
def test_empty_raw_responses_are_preserved(make_service, raw):
    service, _, _ = make_service({"/dailyHeartRate": raw})
    result = ApiService(service.gateway).execute("heart_rate")
    assert result["ok"] and result["status"] == "no_data" and result["data"] == raw


def test_weight_all_400_preserves_error_and_suggests_explicit_alternative(make_service):
    service, session, _ = make_service(
        {"/weight/all/": HttpError(status_code=400, method="GET", url="/fake", response_text="{}")}
    )
    result = ApiService(service.gateway).execute(
        "weight_all", start_date="2026-10-20", end_date="2026-10-22"
    )
    assert not result["ok"] and result["error"]["http_status"] == 400
    assert result["alternative"] == {
        "tool": "garmin_api_weight_range",
        "arguments": {"start_date": "2026-10-20", "end_date": "2026-10-22", "include_all": True},
        "note": "The documented weight/all endpoint rejected this request. weight/range with include_all=true can retrieve all daily entries, but its response shape differs. No fallback request was made.",
    }
    assert len(session.calls) == 1
