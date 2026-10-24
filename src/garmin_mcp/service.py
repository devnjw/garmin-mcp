from datetime import UTC, datetime, timedelta

from . import data
from .credentials import KEY_ENV
from .errors import Fault
from .gateway import Gateway, public_error
from .settings import timezone_name


def envelope(query, result=None, error=None):
    try:
        zone = timezone_name()
    except Fault as exc:
        zone = None
        error = error or exc
    response = {
        "ok": error is None,
        "source": "garmin_connect_personal_api",
        "timezone": zone,
        "fetched_at": datetime.now(UTC).isoformat(),
        "date_basis": "Garmin calendar date; default dates and displayed timestamps use the configured timezone",
        "query": query,
    }
    if error:
        response.update(status="error", error=error.as_dict())
    else:
        response.update(result)
    return response


class Service:
    def __init__(self, gateway=None):
        self.gateway = gateway or Gateway()

    def execute(self, operation, **args):
        query = {"operation": operation, **args}
        try:
            timezone_name()
            method = getattr(self, "_" + operation)
            return envelope(query, method(**args))
        except Exception as exc:
            return envelope(query, error=public_error(exc))

    def _status(self, verify=False):
        configured = bool(self.gateway.store.get())
        if verify:
            self.gateway.call(lambda client: client.get_user_profile_settings())
        return {
            "status": "ok",
            "data": {
                "key_configured": configured,
                "authentication": "verified" if verify else "not_checked",
                "credential_storage": "environment supplied by the MCP client; not persisted by this server",
                "credential_environment_variable": KEY_ENV,
                "token_storage": "process memory",
                "transport": "stdio",
            },
        }

    def _daily_summary(self, date=None):
        target = data.day(date)
        if target > data.day():
            raise Fault("future_date", "Future measurements cannot be queried.")
        raw = self.gateway.call(
            lambda c: c.get(
                "/usersummary-service/usersummary/daily",
                params={"calendarDate": target.isoformat()},
            )
        )
        result = data.daily(raw, target.isoformat())
        return {"status": "ok" if result["has_measurements"] else "no_data", "data": result}

    def _range(self, metric, start=None, end=None):
        first, last = data.date_range(start, end)

        def fetch(client):
            records = []
            for a, b in data.windows(first, last):
                if metric == "sleep":
                    records.extend(data.rows(client.get_daily_sleep_summaries(a, b)))
                elif metric == "hrv":
                    records.extend(data.rows(client.get_daily_hrv_summaries(a, b), "hrvSummaries"))
                elif metric == "body_battery":
                    records.extend(data.rows(client.get_daily_body_battery(a, b)))
            return records

        raw = self.gateway.call(fetch)
        normalize = getattr(data, metric)
        by_date = {}
        for item in raw:
            if metric == "sleep" and data.empty_sleep_placeholder(item):
                continue
            row = normalize(item)
            if not row.get("date"):
                raise Fault("schema_changed", "A daily record has no calendar date.")
            row_day = data.day(row["date"])
            if not first <= row_day <= last:
                raise Fault(
                    "schema_changed", "Garmin returned a record outside the requested date range."
                )
            if row["date"] in by_date and by_date[row["date"]] != row:
                raise Fault("conflicting_data", "Garmin returned conflicting records for one date.")
            by_date[row["date"]] = row
        expected = [(first + timedelta(days=i)).isoformat() for i in range((last - first).days + 1)]
        missing = [d for d in expected if d not in by_date or not by_date[d]["has_measurements"]]
        status = "no_data" if len(missing) == len(expected) else "partial" if missing else "ok"
        return {
            "status": status,
            "data": [by_date[d] for d in sorted(by_date)],
            "missing_dates": missing,
            "requested_range": {"start": first.isoformat(), "end": last.isoformat()},
            "note": "Missing values are null; missing dates have not been replaced with zeroes.",
        }

    def _sleep(self, start=None, end=None):
        return self._range("sleep", start, end)

    def _hrv(self, start=None, end=None):
        return self._range("hrv", start, end)

    def _body_battery(self, start=None, end=None):
        return self._range("body_battery", start, end)

    def _activities(self, start=None, end=None, activity_type=None, limit=20, offset=0):
        first, last = data.date_range(start, end)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 50
            or isinstance(offset, bool)
            or not isinstance(offset, int)
            or offset < 0
        ):
            raise Fault("invalid_pagination", "Use limit 1–50 and a non-negative integer offset.")
        raw = self.gateway.call(
            lambda c: c.search_activities(
                start=offset,
                limit=limit,
                start_date=first,
                end_date=last,
                activity_type=activity_type,
            )
        )
        results = [data.activity(item) for item in data.rows(raw)]
        return {
            "status": "ok" if results else "no_data",
            "data": results,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "next_offset": offset + len(results) if len(results) == limit else None,
                "note": "A full page may have more results; request next_offset to check.",
            },
        }

    def _activity(self, activity_id):
        if isinstance(activity_id, bool) or not isinstance(activity_id, int) or activity_id <= 0:
            raise Fault("invalid_activity_id", "activity_id must be a positive integer.")
        raw = self.gateway.call(lambda c: c.get_activity(activity_id))
        return {"status": "ok" if raw else "no_data", "data": data.activity(raw) if raw else None}

    def _day(self, date=None):
        target = data.day(date).isoformat()
        sections = {}
        stop_error = None
        for name in ("daily_summary", "sleep", "hrv", "body_battery", "activities"):
            args = {"date": target} if name == "daily_summary" else {"start": target, "end": target}
            if stop_error:
                sections[name] = envelope({"operation": name, **args}, error=stop_error)
                sections[name]["not_queried"] = True
                continue
            section = self.execute(name, **args)
            sections[name] = section
            if not section["ok"] and section["error"]["code"] in {
                "not_authenticated",
                "authentication_failed",
                "invalid_api_key",
                "rate_limited",
            }:
                stop_error = Fault(**section["error"])
        states = [part["status"] for part in sections.values()]
        if all(state == "error" for state in states):
            first_error = next(iter(sections.values()))["error"]
            raise Fault(**first_error)
        status = (
            "no_data"
            if all(s == "no_data" for s in states)
            else "partial"
            if any(s in {"error", "partial", "no_data"} for s in states)
            else "ok"
        )
        return {
            "status": status,
            "data": sections,
            "note": "A partial overview must not be reported as a complete day; inspect each section's status.",
        }
