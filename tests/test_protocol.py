import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from garmin_mcp.api import ENDPOINTS


def test_all_34_tools_are_discoverable_and_callable_over_stdio(tmp_path):
    async def verify():
        env = {
            **os.environ,
            "GARMIN_TEST_OUTPUT_DIR": str(tmp_path),
            "GARMIN_PERSONAL_API_KEY": "synthetic-key",
        }
        script = Path(__file__).with_name("stdio_fixture.py")
        async with stdio_client(
            StdioServerParameters(command=sys.executable, args=[str(script)], env=env)
        ) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                initialized = await session.initialize()
                assert "Check ok/status/error" in initialized.instructions
                catalog = (await session.list_tools()).tools
                assert len(catalog) == 34
                writes = {t.name for t in catalog if not t.annotations.readOnlyHint}
                assert writes == {"garmin_api_download_activity", "garmin_api_heart_rate_zones"}
                for endpoint in ENDPOINTS.values():
                    tool = next(t for t in catalog if t.name == endpoint["tool"])
                    assert set(tool.inputSchema["properties"]) == {
                        p["argument"] for p in endpoint["parameters"]
                    }
                for tool in catalog:
                    args = (
                        {"activity_id": 42}
                        if "activity_id" in tool.inputSchema.get("required", [])
                        else {}
                    )
                    if tool.name == "garmin_status":
                        args["verify"] = True
                    result = await session.call_tool(tool.name, args)
                    assert not result.isError, tool.name
                    parsed = result.structuredContent or json.loads(
                        next(c.text for c in result.content if c.type == "text")
                    )
                    assert parsed["ok"], (tool.name, parsed)
                    assert "synthetic-key" not in json.dumps(parsed)
                result = await session.call_tool("garmin_api_activity", {"activity_id": -1})
                parsed = result.structuredContent
                assert not parsed["ok"] and parsed["error"]["code"] == "invalid_parameter"

    asyncio.run(verify())


def test_production_stdio_reports_missing_key_without_network():
    async def verify():
        env = {k: v for k, v in os.environ.items() if k != "GARMIN_PERSONAL_API_KEY"}
        async with stdio_client(
            StdioServerParameters(command=sys.executable, args=["-m", "garmin_mcp.cli"], env=env)
        ) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                assert len((await session.list_tools()).tools) == 34
                status = (await session.call_tool("garmin_status")).structuredContent
                assert status["ok"] and status["data"]["key_configured"] is False
                checked = (
                    await session.call_tool("garmin_status", {"verify": True})
                ).structuredContent
                assert checked["error"]["code"] == "not_authenticated"
                assert "GARMIN_PERSONAL_API_KEY" in checked["error"]["message"]

    asyncio.run(verify())
