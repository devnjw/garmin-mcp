import os

from .errors import Fault

KEY_ENV = "GARMIN_PERSONAL_API_KEY"
KEY_PAGE = "https://connect.garmin.com/app/settings/personalApiToken"


class EnvironmentCredentials:
    """Read the key supplied by the MCP host; never persist credentials."""

    def get(self):
        key = os.environ.get(KEY_ENV)
        if not key:
            return None
        # Reject whitespace/control characters before HTTP header construction.
        if len(key) > 4096 or any(not 33 <= ord(char) <= 126 for char in key):
            raise Fault(
                "invalid_api_key",
                f"Set {KEY_ENV} to a non-empty API key without whitespace or control characters.",
            )
        return key
