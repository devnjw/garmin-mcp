import pytest
from garmin_personal_api import HttpError


def sleep_placeholder(**changes):
    return {
        "calendarDate": None,
        "sleepTimeSeconds": None,
        "napTimeSeconds": None,
        "deviceRemCapable": True,
        "retro": False,
        "sleepNeed": {"calendarDate": "2026-10-20", "actual": 480},
        "nextSleepNeed": {"calendarDate": "2026-10-21", "actual": 480},
        **changes,
    }


def test_sleep_null_placeholder_is_missing_not_a_schema_failure(make_service):
    service, _, _ = make_service({"dailySleepSummariesByDate": [sleep_placeholder()]})
    result = service.execute("sleep", start="2026-10-20", end="2026-10-20")
    assert result["ok"] and result["status"] == "no_data"
    assert result["data"] == []
    assert result["missing_dates"] == ["2026-10-20"]


def test_sleep_nap_only_day_uses_explicit_nap_date_and_keeps_night_missing(make_service):
    service, _, _ = make_service(
        {
            "dailySleepSummariesByDate": [
                sleep_placeholder(),
                {"calendarDate": "2026-10-21", "sleepTimeSeconds": 28000},
                sleep_placeholder(
                    napTimeSeconds=1200,
                    dailyNapDTOS=[{"calendarDate": "2026-10-22", "napTimeSec": 1200}],
                ),
            ]
        }
    )
    result = service.execute("sleep", start="2026-10-20", end="2026-10-22")
    assert result["ok"] and result["status"] == "partial"
    assert result["missing_dates"] == ["2026-10-20"]
    nap = result["data"][1]
    assert nap["date"] == "2026-10-22"
    assert nap["date_source"] == "dailyNapDTOS.calendarDate"
    assert nap["nap_s"] == 1200 and nap["sleep_s"] is None
    assert "sleep_s" in nap["missing_fields"]


@pytest.mark.parametrize(
    "changes",
    [
        {"sleepTimeSeconds": 100},
        {"newMeasurement": 100},
        {"napTimeSeconds": 1200, "dailyNapDTOS": []},
        {
            "napTimeSeconds": 1200,
            "dailyNapDTOS": [{"calendarDate": "2026-10-20"}, {"calendarDate": "2026-10-21"}],
        },
        {
            "sleepTimeSeconds": 100,
            "napTimeSeconds": 1200,
            "dailyNapDTOS": [{"calendarDate": "2026-10-20"}],
        },
    ],
)
def test_undated_sleep_measurements_still_fail_if_date_cannot_be_established(make_service, changes):
    service, _, _ = make_service({"dailySleepSummariesByDate": [sleep_placeholder(**changes)]})
    result = service.execute("sleep", start="2026-10-20", end="2026-10-21")
    assert not result["ok"] and result["error"]["code"] == "schema_changed"


def test_sleep_reports_missing_days_without_zero_filling(make_service):
    service, session, _ = make_service(
        {
            "dailySleepSummariesByDate": [
                {"calendarDate": "2026-10-20", "sleepTimeSeconds": 28000},
                {"calendarDate": "2026-10-22", "sleepTimeSeconds": 0},
            ]
        }
    )
    result = service.execute("sleep", start="2026-10-20", end="2026-10-22")
    assert result["ok"] and result["status"] == "partial"
    assert result["missing_dates"] == ["2026-10-21"]
    assert result["data"][1]["sleep_s"] == 0
    assert session.calls[0][1] == {"startDate": "2026-10-20", "endDate": "2026-10-22"}


def test_range_splits_sdk_requests_and_reports_no_data(make_service):
    service, session, _ = make_service({"dailySleepSummariesByDate": []})
    result = service.execute("sleep", start="2026-07-27", end="2026-10-24")
    assert len(session.calls) == 3
    assert result["status"] == "no_data"
    assert len(result["missing_dates"]) == 90


def test_hrv_uses_nested_summary_envelope(make_service):
    service, _, _ = make_service(
        {
            "/hrv/daily/": {
                "hrvSummaries": [
                    {
                        "calendarDate": "2026-10-20",
                        "lastNightAvg": 55,
                        "weeklyAvg": 58,
                        "status": "BALANCED",
                    }
                ]
            }
        }
    )
    result = service.execute("hrv", start="2026-10-20", end="2026-10-20")
    assert result["status"] == "ok"
    assert result["data"][0]["last_night_avg_ms"] == 55


def test_api_error_is_not_replaced_by_missing_data_or_leaked(make_service):
    error = HttpError(
        status_code=429,
        method="GET",
        url="https://example.invalid/secret",
        response_text="LEAKED_KEY",
    )
    service, _, _ = make_service({"/hrv/daily/": error})
    result = service.execute("hrv", start="2026-10-20", end="2026-10-20")
    assert not result["ok"] and result["error"]["code"] == "rate_limited"
    assert result["error"]["retryable"]
    assert "LEAKED_KEY" not in str(result) and "example.invalid" not in str(result)


def test_activity_pagination_and_filters_are_forwarded(make_service):
    service, session, _ = make_service(
        {
            "/activities/search/": [
                {"activityId": 10, "distance": 0},
                {"activityId": 11, "distance": 1234},
            ]
        }
    )
    result = service.execute(
        "activities",
        start="2026-10-20",
        end="2026-10-22",
        activity_type="running",
        limit=2,
        offset=4,
    )
    assert result["pagination"]["next_offset"] == 6
    assert session.calls[0][1] == {
        "start": 4,
        "limit": 2,
        "startDate": "2026-10-20",
        "endDate": "2026-10-22",
        "activityType": "running",
    }
    assert result["data"][0]["distance_m"] == 0


def test_invalid_pagination_does_not_call_api(make_service):
    service, session, _ = make_service({})
    result = service.execute("activities", limit=100)
    assert result["error"]["code"] == "invalid_pagination" and session.calls == []


def test_day_preserves_good_sections_when_one_endpoint_fails(make_service):
    service, _, _ = make_service(
        {
            "/usersummary/daily": {"calendarDate": "2026-10-20", "totalSteps": 4000},
            "dailySleepSummariesByDate": [
                {"calendarDate": "2026-10-20", "sleepTimeSeconds": 28000}
            ],
            "/hrv/daily/": HttpError(
                status_code=503, method="GET", url="/fake", response_text="private details"
            ),
            "/bodyBattery/reports/": [{"date": "2026-10-20", "charged": 60}],
            "/activities/search/": [],
        }
    )
    result = service.execute("day", date="2026-10-20")
    assert result["ok"] and result["status"] == "partial"
    assert result["data"]["daily_summary"]["data"]["steps"] == 4000
    assert result["data"]["hrv"]["error"]["code"] == "garmin_unavailable"
    assert "private details" not in str(result)


def test_all_failed_sections_are_not_success(make_service):
    service, _, _ = make_service({})
    result = service.execute("day", date="2026-10-25")
    assert result["ok"] is False
    assert result["error"]["code"] == "future_date"


def test_conflicting_duplicate_days_are_rejected(make_service):
    service, _, _ = make_service(
        {
            "dailySleepSummariesByDate": [
                {"calendarDate": "2026-10-20", "sleepTimeSeconds": 1},
                {"calendarDate": "2026-10-20", "sleepTimeSeconds": 2},
            ]
        }
    )
    result = service.execute("sleep", start="2026-10-20", end="2026-10-20")
    assert result["error"]["code"] == "conflicting_data"


def test_rate_limited_day_stops_requesting_more_endpoints(make_service):
    service, session, _ = make_service(
        {
            "/usersummary/daily": HttpError(
                status_code=429, method="GET", url="/fake", response_text="private"
            )
        }
    )
    result = service.execute("day", date="2026-10-20")
    assert len(session.calls) == 1
    assert result["error"]["code"] == "rate_limited"
