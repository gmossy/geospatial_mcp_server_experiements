# mcp/server.py
"""Refactored MCP server that uses the official `mcp-protocol` library.
All tool functions remain unchanged; they are simply registered with
an `MCPServer` instance.
"""

import os
import json
import math
import io
import base64
import numpy as np
import rasterio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from typing import Optional, List
from pydantic import BaseModel
from mgrs import MGRS
from pyproj import Transformer, CRS
from shapely.geometry import shape, mapping
from shapely.ops import transform as shp_transform

# -------------------------------------------------
# Official MCP library imports
# -------------------------------------------------
from mcp_protocol import MCPServer, MCPToolCall, MCPToolResult, MCPListToolsResult

# -------------------------------------------------
# Global objects
# -------------------------------------------------
mgrs_converter = MGRS()
GEOMETRY_STORE: dict = {}
DTED_ROOT = os.getenv("DTED_ROOT", "./dted")

# -------------------------------------------------
# Create the MCP server instance
# -------------------------------------------------
mcp_server = MCPServer()

# -------------------------------------------------
# Helper functions (unchanged from original implementation)
# -------------------------------------------------
def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great‑circle distance between two geographic points.

    Parameters
    ----------
    lat1, lon1 : float
        Latitude and longitude of the first point in decimal degrees.
    lat2, lon2 : float
        Latitude and longitude of the second point in decimal degrees.

    Returns
    -------
    float
        Distance in meters.
    """
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def load_dem_for_point(lat: float, lon: float):
    """Retrieve a DEM tile covering the given latitude/longitude.

    This is a thin wrapper around the global ``tile_manager`` which
    returns a ``rasterio`` dataset and its CRS.
    """
    return tile_manager.get_tile(lat, lon)
    return tile_manager.get_tile(lat, lon)

# -------------------------------------------------
# Tool implementations (trimmed for brevity – copy the full bodies from the original server.py)
# -------------------------------------------------
def tool_to_mgrs(args: dict) -> MCPToolResult:
    """Convert latitude/longitude to an MGRS string.

    Expected ``args`` keys:
        - ``lat`` (float): Latitude.
        - ``lon`` (float): Longitude.
        - ``precision`` (int, optional): MGRS precision (default 5 → 1 m).
    """
    try:
        lat = float(args["lat"])
        lon = float(args["lon"])
        precision = int(args.get("precision", 5))
        mgrs_str = mgrs_converter.toMGRS(lat, lon, MGRSPrecision=precision)
        return MCPToolResult(ok=True, data={"mgrs": mgrs_str})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))
    try:
        lat = float(args["lat"])
        lon = float(args["lon"])
        precision = int(args.get("precision", 5))
        mgrs_str = mgrs_converter.toMGRS(lat, lon, MGRSPrecision=precision)
        return MCPToolResult(ok=True, data={"mgrs": mgrs_str})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))

def tool_from_mgrs(args: dict) -> MCPToolResult:
    """Convert an MGRS string to latitude/longitude.

    Expected ``args`` key:
        - ``mgrs`` (str): MGRS coordinate.
    """
    try:
        mgrs_str = str(args["mgrs"]).replace(" ", "")
        lat, lon = mgrs_converter.toLatLon(mgrs_str)
        return MCPToolResult(ok=True, data={"lat": lat, "lon": lon})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))
    try:
        mgrs_str = str(args["mgrs"]).replace(" ", "")
        lat, lon = mgrs_converter.toLatLon(mgrs_str)
        return MCPToolResult(ok=True, data={"lat": lat, "lon": lon})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))

def tool_transform(args: dict) -> MCPToolResult:
    """Transform a coordinate from one CRS to another.

    Expected ``args`` keys:
        - ``lat`` (float): Latitude in source CRS.
        - ``lon`` (float): Longitude in source CRS.
        - ``source_crs`` (str, optional): Source CRS identifier (default ``EPSG:4326``).
        - ``target_crs`` (str): Target CRS identifier.
    """
    try:
        lat = float(args["lat"])
        lon = float(args["lon"])
        source_crs = args.get("source_crs", "EPSG:4326")
        target_crs = args["target_crs"]
        transformer = Transformer.from_crs(CRS.from_user_input(source_crs), CRS.from_user_input(target_crs), always_xy=True)
        x, y = transformer.transform(lon, lat)
        return MCPToolResult(ok=True, data={"x": x, "y": y, "target_crs": target_crs})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))
    try:
        lat = float(args["lat"])
        lon = float(args["lon"])
        source_crs = args.get("source_crs", "EPSG:4326")
        target_crs = args["target_crs"]
        transformer = Transformer.from_crs(CRS.from_user_input(source_crs), CRS.from_user_input(target_crs), always_xy=True)
        x, y = transformer.transform(lon, lat)
        return MCPToolResult(ok=True, data={"x": x, "y": y, "target_crs": target_crs})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))

def tool_distance(args: dict) -> MCPToolResult:
    """Compute the haversine distance between two points.

    Expected ``args`` keys:
        - ``lat1``, ``lon1``: First point.
        - ``lat2``, ``lon2``: Second point.
    """
    try:
        lat1 = float(args["lat1"])
        lon1 = float(args["lon1"])
        lat2 = float(args["lat2"])
        lon2 = float(args["lon2"])
        meters = haversine_distance_m(lat1, lon1, lat2, lon2)
        return MCPToolResult(ok=True, data={"distance_m": meters})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))
    try:
        lat1 = float(args["lat1"])
        lon1 = float(args["lon1"])
        lat2 = float(args["lat2"])
        lon2 = float(args["lon2"])
        meters = haversine_distance_m(lat1, lon1, lat2, lon2)
        return MCPToolResult(ok=True, data={"distance_m": meters})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))

def tool_elevation(args: dict) -> MCPToolResult:
    """Return elevation (in meters) for a given coordinate.

    Expected ``args`` keys:
        - ``lat`` (float): Latitude.
        - ``lon`` (float): Longitude.
    """
    try:
        lat = float(args["lat"])
        lon = float(args["lon"])
        ds, crs = load_dem_for_point(lat, lon)
        if ds:
            if crs != "EPSG:4326":
                xs, ys = transform("EPSG:4326", crs, [lon], [lat])
                x, y = xs[0], ys[0]
            else:
                x, y = lon, lat
            row, col = ds.index(x, y)
            if 0 <= row < ds.height and 0 <= col < ds.width:
                val = ds.read(1)[row, col]
                ds.close()
                return MCPToolResult(ok=True, data={"elevation_m": float(val), "source": "DTED"})
            ds.close()
        # fallback stub
        elevation_m = 1000.0 + (lat % 1.0) * 100 + (lon % 1.0) * 10
        return MCPToolResult(ok=True, data={"elevation_m": elevation_m, "source": "stub"})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))
    try:
        lat = float(args["lat"])
        lon = float(args["lon"])
        ds, crs = load_dem_for_point(lat, lon)
        if ds:
            if crs != "EPSG:4326":
                xs, ys = transform("EPSG:4326", crs, [lon], [lat])
                x, y = xs[0], ys[0]
            else:
                x, y = lon, lat
            row, col = ds.index(x, y)
            if 0 <= row < ds.height and 0 <= col < ds.width:
                val = ds.read(1)[row, col]
                ds.close()
                return MCPToolResult(ok=True, data={"elevation_m": float(val), "source": "DTED"})
            ds.close()
        # fallback stub
        elevation_m = 1000.0 + (lat % 1.0) * 100 + (lon % 1.0) * 10
        return MCPToolResult(ok=True, data={"elevation_m": elevation_m, "source": "stub"})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))

# NOTE: The remaining tool implementations (line_of_sight, render_heatmap,
# get_terrain_grid, load_geojson, buffer, intersect, within) should be copied
# verbatim from the original `server.py`. They are omitted here for brevity.

# -------------------------------------------------
# Register all tools with the MCP server
# -------------------------------------------------
mcp_server.register_tool("to_mgrs", tool_to_mgrs)
mcp_server.register_tool("from_mgrs", tool_from_mgrs)
mcp_server.register_tool("transform", tool_transform)
mcp_server.register_tool("distance", tool_distance)
mcp_server.register_tool("elevation", tool_elevation)
# Register the other tools after copying their full bodies:
# mcp_server.register_tool("line_of_sight", tool_line_of_sight)
# mcp_server.register_tool("render_heatmap", tool_render_heatmap)
# mcp_server.register_tool("get_terrain_grid", tool_get_terrain_grid)
# mcp_server.register_tool("load_geojson", tool_load_geojson)
# mcp_server.register_tool("buffer", tool_buffer)
# mcp_server.register_tool("intersect", tool_intersect)
# mcp_server.register_tool("within", tool_within)

# -------------------------------------------------
# Optional thin FastAPI wrapper (kept for backward compatibility)
# -------------------------------------------------


# -------------------------------------------------
# Tile manager and other utility classes (unchanged – copy from original server.py)
# -------------------------------------------------
# ... (TileManager class, project_geom_to_meters, project_geom_from_meters, etc.) ...

if __name__ == "__main__":
    # Run the MCP server on WebSocket port 9000 (default transport = websockets)
    mcp_server.run(host="0.0.0.0", port=9000)
