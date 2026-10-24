import math
import re
from datetime import UTC, date, datetime, timedelta

from .errors import Fault
from .settings import timezone


def day(value=None):
    if value is None:
        return datetime.now(timezone()).date()
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise Fault("invalid_date", "Dates must use YYYY-MM-DD.")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise Fault("invalid_date", "This calendar date is invalid.") from None


def date_range(start=None, end=None):
    last = day(end)
    first = day(start) if start is not None else last - timedelta(days=6)
    if first > last or (last - first).days >= 90:
        raise Fault(
            "invalid_range", "Use an inclusive date range of 1 to 90 days, with start <= end."
        )
    if last > day():
        raise Fault("future_date", "Future measurements cannot be queried.")
    return first, last


def windows(first, last, size=31):
    while first <= last:
        end = min(first + timedelta(days=size - 1), last)
        yield first.isoformat(), end.isoformat()
        first = end + timedelta(days=1)


def number(value):
    # Garmin uses negative sentinels for unavailable measurements. Keep real zeroes.
    return (
        value
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
        else None
    )


def obj(value):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise Fault("schema_changed", "Garmin returned a different object structure than expected.")
    return value


def rows(value, field=None):
    if value is None:
        return []
    if field:
        value = obj(value).get(field)
        if value is None:
            raise Fault(
                "schema_changed", f"Garmin's response is missing the expected {field} field."
            )
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise Fault("schema_changed", "Garmin returned a different list structure than expected.")
    return value


def utc_to_local(value):
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdecimal()):
            timestamp = datetime.fromtimestamp(float(value) / 1000, UTC)
        else:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)
        return timestamp.astimezone(timezone()).isoformat()
    except (ValueError, TypeError, OverflowError, OSError):
        return None


def metrics(record, mapping):
    result = {key: number(record.get(source)) for key, source in mapping.items()}
    result["missing_fields"] = [key for key, value in result.items() if value is None]
    result["has_measurements"] = any(
        value is not None for key, value in result.items() if key != "missing_fields"
    )
    return result


def daily(record, requested_date):
    r = obj(record)
    return {
        "date": r.get("calendarDate") or requested_date,
        **metrics(
            r,
            {
                "steps": "totalSteps",
                "distance_m": "totalDistanceMeters",
                "energy_total_kcal": "totalKilocalories",
                "energy_active_kcal": "activeKilocalories",
                "resting_hr_bpm": "restingHeartRate",
                "min_hr_bpm": "minHeartRate",
                "max_hr_bpm": "maxHeartRate",
                "stress_average_0_100": "averageStressLevel",
                "stress_max_0_100": "maxStressLevel",
                "body_battery_high_0_100": "bodyBatteryHighestValue",
                "body_battery_low_0_100": "bodyBatteryLowestValue",
                "moderate_intensity_min": "moderateIntensityMinutes",
                "vigorous_intensity_min": "vigorousIntensityMinutes",
            },
        ),
    }


def empty_sleep_placeholder(record):
    r = obj(record.get("dailySleepDTO", record))
    # Garmin returns undated, null measurements alongside sleep-need metadata
    # for days without recorded sleep. Sleep need is not a sleep measurement.
    metadata = {"deviceRemCapable", "retro", "sleepNeed", "nextSleepNeed"}
    return (
        "calendarDate" in r
        and "sleepTimeSeconds" in r
        and all(value is None for key, value in r.items() if key not in metadata)
    )


def sleep(record):
    r = obj(record.get("dailySleepDTO", record))
    result = {
        "date": r.get("calendarDate"),
        **metrics(
            r,
            {
                "sleep_s": "sleepTimeSeconds",
                "deep_s": "deepSleepSeconds",
                "light_s": "lightSleepSeconds",
                "rem_s": "remSleepSeconds",
                "awake_s": "awakeSleepSeconds",
                "nap_s": "napTimeSeconds",
                "average_hr_bpm": "avgHeartRate",
                "average_spo2_percent": "averageSpO2Value",
                "average_respiration_per_min": "averageRespirationValue",
                "sleep_stress_average": "avgSleepStress",
            },
        ),
    }
    result["score_0_100"] = number(obj(obj(r.get("sleepScores")).get("overall")).get("value"))
    result["start_time"] = utc_to_local(r.get("sleepStartTimestampGMT"))
    result["end_time"] = utc_to_local(r.get("sleepEndTimestampGMT"))
    result["date_source"] = "calendarDate" if result["date"] else None
    has_night_values = any(
        value is not None
        for key, value in result.items()
        if key not in {"date", "date_source", "nap_s", "missing_fields", "has_measurements"}
    )
    if not result["date"] and result["nap_s"] is not None and not has_night_values:
        nap_dates = [nap.get("calendarDate") for nap in rows(r.get("dailyNapDTOS"))]
        # Use explicit nap dates, never list position or sleep-need dates. A nap
        # date cannot establish the date of an undated overnight measurement.
        if (
            nap_dates
            and isinstance(nap_dates[0], str)
            and all(value == nap_dates[0] for value in nap_dates)
        ):
            result["date"] = nap_dates[0]
            result["date_source"] = "dailyNapDTOS.calendarDate"
    if result["score_0_100"] is not None:
        result["has_measurements"] = True
    return result


def hrv(record):
    return {
        "date": record.get("calendarDate"),
        **metrics(
            record,
            {
                "last_night_avg_ms": "lastNightAvg",
                "weekly_avg_ms": "weeklyAvg",
                "last_night_5min_high_ms": "lastNight5MinHigh",
            },
        ),
        "garmin_status": record.get("status"),
        "baseline": record.get("baseline"),
    }


def body_battery(record):
    result = {
        "date": record.get("date"),
        **metrics(record, {"charged_points": "charged", "drained_points": "drained"}),
    }
    descriptors = record.get("bodyBatteryValueDescriptorDTOList") or []
    index = next(
        (
            d.get("bodyBatteryValueDescriptorIndex")
            for d in descriptors
            if isinstance(d, dict) and d.get("bodyBatteryValueDescriptorKey") == "bodyBatteryLevel"
        ),
        None,
    )
    values = []
    if isinstance(index, int) and index >= 0:
        for row in record.get("bodyBatteryValuesArray") or []:
            if isinstance(row, list) and len(row) > index:
                level = number(row[index])
                if level is not None and level <= 100:
                    values.append(level)
    result.update(
        observed_min_0_100=min(values) if values else None,
        observed_max_0_100=max(values) if values else None,
        valid_sample_count=len(values),
    )
    if values:
        result["has_measurements"] = True
    return result


def activity(record):
    r = obj(record)
    summary = obj(r.get("summaryDTO", r))
    kind = obj(r.get("activityTypeDTO", r.get("activityType")))
    detailed = "summaryDTO" in r
    return {
        "activity_id": r.get("activityId"),
        "name": r.get("activityName"),
        "type": kind.get("typeKey"),
        "start_time": utc_to_local(summary.get("startTimeGMT")),
        **metrics(
            summary,
            {
                "distance_m": "distance",
                "duration_s": "duration",
                "moving_duration_s": "movingDuration",
                "average_speed_m_s": "averageSpeed",
                "average_hr_bpm": "averageHR",
                "max_hr_bpm": "maxHR",
                "energy_kcal": "calories",
                "ascent_m": "elevationGain",
                "average_power_w": "averagePower" if detailed else "avgPower",
                "aerobic_training_effect": "trainingEffect"
                if detailed
                else "aerobicTrainingEffect",
                "anaerobic_training_effect": "anaerobicTrainingEffect",
            },
        ),
    }
