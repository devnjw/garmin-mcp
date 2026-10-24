import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .errors import Fault


def timezone():
    """Use an explicit IANA zone or a system zoneinfo link; fall back to UTC."""
    name = os.environ.get("GARMIN_MCP_TIMEZONE")
    if name is None:
        try:
            path = str(Path("/etc/localtime").resolve(strict=True))
            name = path.split("/zoneinfo/", 1)[1] if "/zoneinfo/" in path else "UTC"
        except OSError:
            name = "UTC"
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise Fault(
            "invalid_timezone", "Set GARMIN_MCP_TIMEZONE to a valid IANA timezone."
        ) from None


def timezone_name():
    return timezone().key


def data_directory():
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        if not root.is_absolute():
            raise Fault("invalid_data_directory", "LOCALAPPDATA must be an absolute path.")
        return root / "garmin-mcp"
    return Path.home() / ".local" / "share" / "garmin-mcp"
