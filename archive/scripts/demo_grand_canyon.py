import asyncio
import httpx
import base64

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

async def main():
    print("--- Grand Canyon Terrain Demo ---")
    
    # 1. Point Elevation
    lat, lon = 36.1, -112.1
    print(f"\n1. Getting elevation at {lat}, {lon}...")
    elev = await mcp_call_tool("elevation", {"lat": lat, "lon": lon})
    print(f"   Elevation: {elev['elevation_m']} meters ({elev.get('source')})")

    # 2. Line of Sight (Rim to River?)
    # Let's try two points nearby
    obs_lat, obs_lon = 36.1, -112.1
    tgt_lat, tgt_lon = 36.11, -112.11
    print(f"\n2. Checking Line of Sight from {obs_lat},{obs_lon} to {tgt_lat},{tgt_lon}...")
    los = await mcp_call_tool("line_of_sight", {
        "observer_lat": obs_lat, "observer_lon": obs_lon,
        "target_lat": tgt_lat, "target_lon": tgt_lon,
        "observer_height_m": 2.0, "target_height_m": 2.0
    })
    print(f"   Clear: {los['line_of_sight']}")
    print(f"   Distance: {los['distance_m']:.1f}m")
    print(f"   Max Blockage: {los['max_block_m']:.1f}m")

    # 3. Render Heatmap
    print(f"\n3. Rendering Heatmap for tile...")
    heatmap = await mcp_call_tool("render_heatmap", {"lat": lat, "lon": lon})
    if "image_base64" in heatmap:
        # Save to file to verify
        with open("grand_canyon_heatmap.png", "wb") as f:
            f.write(base64.b64decode(heatmap["image_base64"]))
        print("   Saved 'grand_canyon_heatmap.png'")
    else:
        print("   Failed to render heatmap.")

if __name__ == "__main__":
    asyncio.run(main())
