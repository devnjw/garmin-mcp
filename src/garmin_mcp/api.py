"""Validated, allowlisted access to all documented Personal API GET operations."""

import json
import math
from datetime import timedelta
from importlib.resources import files
from urllib.parse import quote

from . import data
from .downloads import save_activity
from .errors import Fault
from .gateway import public_error
from .service import envelope
from .settings import timezone_name

CONTRACT = json.loads(files("garmin_mcp").joinpath("api_catalog.json").read_text())
ENDPOINTS = {entry["id"]: entry for entry in CONTRACT["endpoints"]}


def invalid(name):
    return Fault(
        "invalid_parameter", f"Invalid value for {name}; check the documented type and bounds."
    )


def validate_value(parameter, value):
    name, kind = parameter["argument"], parameter["type"]
    if kind == "integer":
        bits = 31 if parameter.get("format") == "int32" else 63
        if type(value) is not int or not -(2**bits) <= value < 2**bits:
            raise invalid(name)
    elif kind == "number":
        if type(value) not in (float, int) or not math.isfinite(value):
            raise invalid(name)
    elif kind == "boolean":
        if type(value) is not bool:
            raise invalid(name)
    elif kind == "string":
        if not isinstance(value, str) or not value or len(value) > 512:
            raise invalid(name)
        if parameter.get("format") == "date":
            value = data.day(value).isoformat()
    elif kind == "array":
        if (
            not isinstance(value, list)
            or len(value) > 50
            or any(not isinstance(item, str) or not item or len(item) > 128 for item in value)
        ):
            raise invalid(name)
    else:
        raise Fault("invalid_contract", "The API parameter type is not supported.")
    return value


def prepare(endpoint, arguments):
    definitions = {p["argument"]: p for p in endpoint["parameters"]}
    if set(arguments) - set(definitions):
        raise Fault(
            "invalid_parameter", "This endpoint does not accept one of the provided parameters."
        )
    values = {
        name: validate_value(definitions[name], value)
        for name, value in arguments.items()
        if value is not None
    }
    names = set(definitions)
    ranges = [("start_date", "end_date"), ("from_date", "to_date"), ("from_date", "until_date")]
    for first, last in ranges:
        if {first, last} <= names:
            if endpoint["id"] != "activity_search":
                end = data.day(values.get(last))
                start = data.day(values[first]) if first in values else end - timedelta(days=6)
                if start > end or (end - start).days >= 31:
                    raise Fault(
                        "invalid_range",
                        "Raw API date ranges must be inclusive, ordered, and at most 31 days. Query another interval for more history.",
                    )
                values[first], values[last] = start.isoformat(), end.isoformat()
            elif first in values and last in values and values[first] > values[last]:
                raise Fault("invalid_range", "start_date must not be after end_date.")
    for name in ("date", "calendar_date", "today_date"):
        if name in names and name not in values:
            values[name] = data.day().isoformat()
    if endpoint["id"] == "activity_search":
        values.setdefault("start", 0)
        values.setdefault("limit", 20)
        if values["start"] < 0 or not 1 <= values["limit"] <= 100:
            raise Fault("invalid_pagination", "Use start >= 0 and limit 1–100.")
        if "favorite" in values and values["favorite"] not in (-1, 0, 1):
            raise invalid("favorite")
        if "sort_order" in values:
            values["sort_order"] = values["sort_order"].lower()
            if values["sort_order"] not in {"asc", "desc"}:
                raise invalid("sort_order")
        bounds = {"upper_latitude", "lower_latitude", "left_longitude", "right_longitude"}
        if bounds & values.keys() and not bounds <= values.keys():
            raise Fault(
                "invalid_parameter", "A bounding box requires all four latitude/longitude values."
            )
        for name in bounds & values.keys():
            bound = 90 if "latitude" in name else 180
            if not -bound <= values[name] <= bound:
                raise invalid(name)
        if bounds <= values.keys() and values["lower_latitude"] > values["upper_latitude"]:
            raise invalid("lower_latitude")
        pairs = [
            ("min_distance", "max_distance"),
            ("min_duration", "max_duration"),
            ("min_elevation", "max_elevation"),
            ("lower_max_depth", "upper_max_depth"),
            ("min_elapsed_duration", "max_elapsed_duration"),
            ("min_bottom_time", "max_bottom_time"),
        ]
        for low, high in pairs:
            if low in values and high in values and values[low] > values[high]:
                raise invalid(low)
        for name, value in values.items():
            if name.startswith(("min_", "max_")) or name in {"lower_max_depth", "upper_max_depth"}:
                if value < 0:
                    raise invalid(name)
    if endpoint["id"] == "heart_rate_zones":
        # The official default can create zone settings. Make that opt-in.
        values.setdefault("generate_defaults", False)
    for name in ("activity_id", "chunks", "meal_id"):
        if name in values and values[name] <= 0:
            raise invalid(name)
    for name, definition in definitions.items():
        if definition["required"] and name not in values:
            raise Fault("invalid_parameter", f"Missing required parameter: {name}.")
    path = endpoint["path"]
    params = {}
    for name, value in values.items():
        definition = definitions[name]
        if definition["in"] == "path":
            path = path.replace("{" + definition["name"] + "}", quote(str(value), safe=""))
        else:
            params[definition["name"]] = str(value).lower() if type(value) is bool else value
    return path, params, values


class ApiService:
    def __init__(self, gateway):
        self.gateway = gateway

    def execute(self, endpoint_id, **arguments):
        query = {"operation": "api_" + endpoint_id, **arguments}
        try:
            timezone_name()
            endpoint = ENDPOINTS.get(endpoint_id)
            if endpoint is None:
                raise Fault(
                    "unsupported_endpoint", "Only documented, named endpoints are available."
                )
            path, params, values = prepare(endpoint, arguments)
            query = {"operation": "api_" + endpoint_id, **values}
            if endpoint["binary"]:
                content = self.gateway.call(
                    lambda client: client.download_activity(values["activity_id"])
                )
                result = {"status": "ok", "data": save_activity(content, values["activity_id"])}
            else:
                raw = self.gateway.call(lambda client: client.get(path, params=params or None))
                result = {
                    "status": "no_data" if raw is None or raw == [] or raw == {} else "ok",
                    "data": raw,
                    "format": "garmin_raw_json",
                    "note": "Original Garmin fields and units are preserved. Nulls, negative sentinels and empty dated placeholders are not normalized. An ok response does not establish complete measurement coverage.",
                }
                if endpoint_id == "activity_search" and isinstance(raw, list):
                    result["pagination"] = {
                        "start": values["start"],
                        "limit": values["limit"],
                        "next_start": values["start"] + len(raw)
                        if len(raw) == values["limit"]
                        else None,
                    }
            return envelope(query, result)
        except Exception as exc:
            fault = public_error(exc)
            response = envelope(query, error=fault)
            if endpoint_id == "weight_all" and fault.http_status == 400:
                response["alternative"] = {
                    "tool": "garmin_api_weight_range",
                    "arguments": {
                        "start_date": query.get("start_date"),
                        "end_date": query.get("end_date"),
                        "include_all": True,
                    },
                    "note": "The documented weight/all endpoint rejected this request. weight/range with include_all=true can retrieve all daily entries, but its response shape differs. No fallback request was made.",
                }
            return response
