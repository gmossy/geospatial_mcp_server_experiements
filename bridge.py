import asyncio
import httpx
import sys
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, EmbeddedResource, ImageContent
from mcp.server import Server

# Connect to the running HTTP server
MCP_HTTP_URL = "http://localhost:8000"

async def fetch_tools():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{MCP_HTTP_URL}/mcp/tools")
            resp.raise_for_status()
            data = resp.json()
            return data.get("tools", [])
        except Exception as e:
            # Fallback or error logging
            return []

async def call_remote_tool(name: str, arguments: dict):
    async with httpx.AsyncClient() as client:
        payload = {"name": name, "arguments": arguments}
        resp = await client.post(f"{MCP_HTTP_URL}/mcp/call", json=payload, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("error", "Unknown error"))
        return data.get("data")

async def main():
    app = Server("geo-mcp-bridge")

    # Fetch tools dynamically at startup
    tools_data = await fetch_tools()
    
    @app.list_tools()
    async def list_tools() -> list[Tool]:
        mcp_tools = []
        for t in tools_data:
            mcp_tools.append(Tool(
                name=t["name"],
                description=t["description"],
                inputSchema=t["input_schema"]
            ))
        return mcp_tools

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
        try:
            result_data = await call_remote_tool(name, arguments)
            
            # Check if this is an image response
            if isinstance(result_data, dict) and "image_base64" in result_data:
                return [
                    ImageContent(
                        type="image",
                        data=result_data["image_base64"],
                        mimeType=f"image/{result_data.get('format', 'png')}"
                    ),
                    TextContent(type="text", text=result_data.get("message", "Rendered image."))
                ]

            # Format result as JSON string for Claude
            import json
            return [TextContent(type="text", text=json.dumps(result_data, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
