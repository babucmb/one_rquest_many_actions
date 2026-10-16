import argparse
import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.config import get_settings


async def inspect_server(url: str, invoke_tool: str | None = None) -> dict:
    async with streamable_http_client(url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            initialization = await session.initialize()
            tools = await session.list_tools()
            resources = await session.list_resources()
            prompts = await session.list_prompts()
            report = {
                "server": initialization.serverInfo.model_dump(),
                "tool_names": [tool.name for tool in tools.tools],
                "resources": [str(resource.uri) for resource in resources.resources],
                "prompts": [prompt.name for prompt in prompts.prompts],
            }
            if invoke_tool:
                result = await session.call_tool(invoke_tool, {})
                report["tool_result"] = {
                    "is_error": result.isError,
                    "content": [
                        item.text if item.type == "text" else item.model_dump()
                        for item in result.content
                    ],
                }
            return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect the local workflow MCP server.")
    parser.add_argument(
        "--url",
        default=get_settings().mcp_server_url,
        help="Streamable HTTP MCP URL (default: MCP_SERVER_URL).",
    )
    parser.add_argument(
        "--call-budget",
        action="store_true",
        help="Also invoke get_budget_summary_tool and print its result.",
    )
    args = parser.parse_args()
    result = asyncio.run(
        inspect_server(args.url, "get_budget_summary_tool" if args.call_budget else None)
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
