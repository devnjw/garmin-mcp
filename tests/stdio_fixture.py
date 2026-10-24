"""Synthetic STDIO server for protocol tests; never used by the installed entrypoint."""

import io
import os
import zipfile
from pathlib import Path

from garmin_mcp import downloads, server
from garmin_mcp.credentials import EnvironmentCredentials


class Client:
    def get(self, path, params=None):
        if path == "/usersummary-service/usersummary/daily":
            return {"calendarDate": (params or {}).get("calendarDate"), "totalSteps": 0}
        return {"synthetic": True, "path": path, "params": params}

    def get_user_profile_settings(self):
        return {"synthetic": True}

    def get_daily_sleep_summaries(self, start, end):
        return [{"calendarDate": str(end), "sleepTimeSeconds": 28800}]

    def get_daily_hrv_summaries(self, start, end):
        return {"hrvSummaries": [{"calendarDate": str(end), "lastNightAvg": 50}]}

    def get_daily_body_battery(self, start, end):
        return [{"date": str(end), "charged": 50}]

    def search_activities(self, **args):
        return [{"activityId": 42, "distance": 1000}]

    def get_activity(self, activity_id):
        return {"activityId": activity_id, "summaryDTO": {"distance": 1000}}

    def download_activity(self, activity_id):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("synthetic.fit", "synthetic")
        return stream.getvalue()


class Gateway:
    store = EnvironmentCredentials()

    def call(self, operation):
        return operation(Client())


if __name__ == "__main__":
    downloads.data_directory = lambda: Path(os.environ["GARMIN_TEST_OUTPUT_DIR"])
    server.service.gateway = server.api_service.gateway = Gateway()
    server.mcp.run(transport="stdio")
