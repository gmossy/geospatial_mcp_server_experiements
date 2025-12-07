import httpx

MCP_BASE_URL = "http://localhost:8000"


async def mcp_call_tool(name: str, arguments: dict):
    payload = {"name": name, "arguments": arguments}
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{MCP_BASE_URL}/mcp/call", json=payload, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok", False):
            raise RuntimeError(f"MCP error: {data.get('error')}")
        return data["data"]
