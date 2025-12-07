import json
import requests
from typing import Optional

# Configuration
MCP_BASE_URL = "http://host.docker.internal:8000" # Use host.docker.internal if OpenWebUI is in Docker

class Tools:
    def __init__(self):
        pass

    def _call_mcp(self, name: str, arguments: dict):
        try:
            # If running locally without docker, use localhost. 
            # If OpenWebUI is in docker, it needs host.docker.internal
            url = f"{MCP_BASE_URL}/mcp/call"
            payload = {"name": name, "arguments": arguments}
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                return f"Error: {data.get('error')}"
            return data["data"]
        except Exception as e:
            return f"Connection Error: {str(e)}"

    def get_elevation(self, lat: float, lon: float) -> str:
        """
        Get the elevation in meters at a specific latitude and longitude.
        :param lat: Latitude
        :param lon: Longitude
        :return: Elevation data
        """
        return json.dumps(self._call_mcp("elevation", {"lat": lat, "lon": lon}))

    def get_mgrs(self, lat: float, lon: float) -> str:
        """
        Convert Latitude/Longitude to MGRS coordinate string.
        :param lat: Latitude
        :param lon: Longitude
        :return: MGRS string
        """
        return json.dumps(self._call_mcp("to_mgrs", {"lat": lat, "lon": lon}))

    def check_line_of_sight(self, obs_lat: float, obs_lon: float, tgt_lat: float, tgt_lon: float) -> str:
        """
        Check if there is a direct line of sight between two points.
        :param obs_lat: Observer Latitude
        :param obs_lon: Observer Longitude
        :param tgt_lat: Target Latitude
        :param tgt_lon: Target Longitude
        :return: Line of sight analysis
        """
        return json.dumps(self._call_mcp("line_of_sight", {
            "observer_lat": obs_lat, "observer_lon": obs_lon,
            "target_lat": tgt_lat, "target_lon": tgt_lon
        }))

    def render_heatmap(self, lat: float, lon: float) -> str:
        """
        Render a visual heatmap of the terrain elevation around a point.
        :param lat: Center Latitude
        :param lon: Center Longitude
        :return: Markdown image of the heatmap
        """
        result = self._call_mcp("render_heatmap", {"lat": lat, "lon": lon})
        if isinstance(result, dict) and "image_base64" in result:
            # Return as markdown image
            return f"![Elevation Heatmap](data:image/png;base64,{result['image_base64']})"
        return str(result)
