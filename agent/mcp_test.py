import asyncio
import os

from dotenv import load_dotenv
from mcp import ClientSession

# The MCP library renamed this function in newer versions; support both.
try:
    from mcp.client.streamable_http import streamable_http_client as http_client
except ImportError:
    from mcp.client.streamable_http import streamablehttp_client as http_client

load_dotenv()
MCP_URL = os.getenv("MCP_URL", "http://localhost:8080/mcp")


async def main():
    async with http_client(MCP_URL) as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 1. Ask the Java server which tools it has
            tools = await session.list_tools()
            print(f"Connected to {MCP_URL}, found {len(tools.tools)} tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}")

            # 2. Call one tool by hand, no AI yet
            print("\nCalling dns_lookup('github.com')...")
            result = await session.call_tool("dns_lookup", {"host": "github.com"})
            for item in result.content:
                if item.type == "text":
                    print(item.text)


asyncio.run(main())