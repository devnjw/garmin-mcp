import pytest

from garmin_mcp import data
from garmin_mcp.errors import Fault


def test_seoul_today_uses_next_day_after_utc_1500():
    assert data.day().isoformat() == "2026-10-24"
    assert data.date_range()[0].isoformat() == "2026-10-18"


@pytest.mark.parametrize(
    "value", ["20261020", "2026-2-20", "2026-02-30", "2026-10-20T00:00:00", "../key"]
)
def test_rejects_ambiguous_dates(value):
    with pytest.raises(Fault):
        data.day(value)


@pytest.mark.parametrize(
    "start,end",
    [("2026-10-24", "2026-10-20"), ("2026-07-26", "2026-10-24"), ("2026-10-24", "2026-10-25")],
)
def test_rejects_reversed_too_long_and_future_ranges(start, end):
    with pytest.raises(Fault):
        data.date_range(start, end)


def test_exact_90_day_window_is_split_without_overlap():
    first, last = data.date_range("2026-07-27", "2026-10-24")
    assert list(data.windows(first, last)) == [
        ("2026-07-27", "2026-08-26"),
        ("2026-08-27", "2026-09-26"),
        ("2026-09-27", "2026-10-24"),
    ]


def test_zero_is_real_but_negative_sentinels_and_non_numbers_are_missing():
    result = data.daily(
        {"totalSteps": 0, "averageStressLevel": -1, "restingHeartRate": None, "maxHeartRate": "75"},
        "2026-10-20",
    )
    assert result["steps"] == 0
    assert result["has_measurements"] is True
    assert result["stress_average_0_100"] is None
    assert result["max_hr_bpm"] is None
    assert "steps" not in result["missing_fields"]
    assert data.daily({}, "2026-10-20")["has_measurements"] is False


def test_sleep_time_is_from_gmt_and_not_double_shifted_local_timestamp():
    result = data.sleep(
        {
            "calendarDate": "2026-10-20",
            "sleepTimeSeconds": 28800,
            "sleepStartTimestampGMT": "2026-10-19T14:00:00",
            "sleepStartTimestampLocal": "2026-10-19T23:00:00",
            "sleepEndTimestampGMT": "2026-10-19T22:00:00Z",
            "sleepScores": {"overall": {"value": 0}},
        }
    )
    assert result["start_time"] == "2026-10-19T23:00:00+09:00"
    assert result["end_time"] == "2026-10-20T07:00:00+09:00"
    assert result["sleep_s"] == 28800
    assert result["score_0_100"] == 0


def test_body_battery_uses_descriptors_not_hardcoded_column_positions():
    result = data.body_battery(
        {
            "date": "2026-10-20",
            "charged": 0,
            "drained": 20,
            "bodyBatteryValueDescriptorDTOList": [
                {
                    "bodyBatteryValueDescriptorIndex": 2,
                    "bodyBatteryValueDescriptorKey": "bodyBatteryLevel",
                }
            ],
            "bodyBatteryValuesArray": [
                [123, "ACTIVE", 70],
                [124, "REST", 0],
                [125, "MISSING", -1],
                [126, "BAD", 101],
            ],
        }
    )
    assert result["observed_min_0_100"] == 0
    assert result["observed_max_0_100"] == 70
    assert result["valid_sample_count"] == 2
    assert result["charged_points"] == 0
    assert (
        data.body_battery({"date": "2026-10-20", "bodyBatteryValuesArray": [[123, 50]]})[
            "observed_max_0_100"
        ]
        is None
    )


def test_activity_detail_maps_official_detail_fields_and_omits_gps():
    result = data.activity(
        {
            "activityId": 42,
            "activityTypeDTO": {"typeKey": "running"},
            "summaryDTO": {
                "distance": 10000,
                "duration": 3600,
                "averageHR": 142,
                "averagePower": 240,
                "trainingEffect": 3.2,
                "startLatitude": 37.1,
                "startTimeGMT": "2026-10-20T01:00:00",
            },
        }
    )
    assert result["distance_m"] == 10000
    assert result["duration_s"] == 3600
    assert result["average_power_w"] == 240
    assert result["aerobic_training_effect"] == 3.2
    assert "startLatitude" not in result


@pytest.mark.parametrize("value", [[1], "html response", {"wrongField": []}])
def test_changed_hrv_schema_is_not_treated_as_empty(value):
    with pytest.raises(Fault):
        data.rows(value, "hrvSummaries")
