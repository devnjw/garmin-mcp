import argparse
import json
import logging
import sys

from . import __version__
from .errors import Fault
from .service import Service


def check_connection():
    service = Service()
    try:
        auth = service.execute("status", verify=True)
        if not auth["ok"]:
            print(json.dumps({"authenticated": False, "error": auth["error"]}))
            return 1
        results = {}
        for name in ("daily_summary", "sleep", "hrv", "body_battery", "activities"):
            result = service.execute(name)
            item = {"status": result["status"]}
            if not result["ok"]:
                item["error"] = result["error"]
            elif isinstance(result.get("data"), list):
                item["record_count"] = len(result["data"])
            results[name] = item
        print(json.dumps({"authenticated": True, "checks": results}, ensure_ascii=False, indent=2))
        return int(any(item["status"] == "error" for item in results.values()))
    finally:
        service.gateway.close()


def main():
    parser = argparse.ArgumentParser(
        description="Garmin MCP using GARMIN_PERSONAL_API_KEY from the environment"
    )
    parser.add_argument("command", choices=["serve", "check"], nargs="?", default="serve")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args()
    # Avoid third-party exception/debug output containing authentication material.
    logging.basicConfig(level=logging.CRITICAL, stream=sys.stderr)
    if args.command == "check":
        raise SystemExit(check_connection())
    try:
        from .server import mcp

        mcp.run(transport="stdio")
    except Fault as exc:
        print(exc.message, file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
