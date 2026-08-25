import asyncio
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    params = StdioServerParameters(
        command=os.environ.get("STRAVA_MCP_COMMAND", str(Path.home() / ".hermes/integrations/strava-mcp/.venv/bin/strava-mcp")),
        args=[],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools=" + ",".join(tool.name for tool in tools.tools))
            result = await session.call_tool("connection_status", {})
            print("status=" + "".join(block.text for block in result.content if hasattr(block, "text")))


asyncio.run(main())
