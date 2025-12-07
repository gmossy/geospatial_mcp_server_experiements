import json
import math
from typing import Optional, List

from fastapi import FastAPI
from pydantic import BaseModel
from mgrs import MGRS
from pyproj import Transformer, CRS
from shapely.geometry import Point, shape, mapping
from shapely.ops import transform as shp_transform
import numpy as np
import rasterio
from rasterio.warp import transform_bounds, transform
import os
import io
import base64
import matplotlib
matplotlib.use('Agg') # Non-interactive backend
import matplotlib.pyplot as plt

app = FastAPI(title="Geospatial MCP Server")

mgrs_converter = MGRS()
GEOMETRY_STORE = {}
DTED_ROOT = os.getenv("DTED_ROOT", "./dted")


# ---------- MCP Protocol-ish Models ----------

class MCPToolCall(BaseModel):
    name: str
    arguments: dict


class MCPToolResult(BaseModel):
    ok: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class MCPListToolsResult(BaseModel):
    tools: List[dict]


# ---------- Utility Functions ----------

def haversine_distance_m(lat1, lon1, lat2, lon2):
    R = 6371000.0  # meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


class TileManager:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.tiles = []  # List of (wgs84_bounds, filepath, crs)
        self.scan()

    def scan(self):
        self.tiles = []
        if not os.path.exists(self.root_dir):
            return
        
        for root, dirs, files in os.walk(self.root_dir):
            for f in files:
                if f.lower().endswith(('.tif', '.tiff', '.dt2', '.dt1', '.hgt')):
                    path = os.path.join(root, f)
                    try:
                        with rasterio.open(path) as src:
                            # Transform bounds to WGS84 if needed
                            if src.crs != "EPSG:4326":
                                left, bottom, right, top = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
                                bounds = rasterio.coords.BoundingBox(left, bottom, right, top)
                            else:
                                bounds = src.bounds
                            
                            self.tiles.append((bounds, path, src.crs))
                    except Exception as e:
                        print(f"Failed to load {f}: {e}")
                        pass
        print(f"Loaded {len(self.tiles)} elevation tiles.")

    def get_tile(self, lat, lon):
        # Naive linear search
        for bounds, path, crs in self.tiles:
            if bounds.left <= lon <= bounds.right and bounds.bottom <= lat <= bounds.top:
                return rasterio.open(path), crs
        return None, None

tile_manager = TileManager(DTED_ROOT)

def load_dem_for_point(lat, lon):
    # Returns (dataset, crs)
    return tile_manager.get_tile(lat, lon)


def project_geom_to_meters(geom):
    """
    Project geometry to a local AEQD projection in meters.
    Returns (projected_geom, local_crs).
    """
    lat = geom.centroid.y
    lon = geom.centroid.x
    proj_str = f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    wgs84 = CRS("EPSG:4326")
    local_crs = CRS(proj_str)
    transformer = Transformer.from_crs(wgs84, local_crs, always_xy=True).transform
    return shp_transform(transformer, geom), local_crs


def project_geom_from_meters(geom, local_crs):
    """
    Project geometry back to WGS84 from local CRS.
    """
    wgs84 = CRS("EPSG:4326")
    transformer = Transformer.from_crs(local_crs, wgs84, always_xy=True).transform
    return shp_transform(transformer, geom)


# ---------- Tool Implementations ----------

def tool_to_mgrs(args: dict) -> MCPToolResult:
    try:
        lat = float(args["lat"])
        lon = float(args["lon"])
        precision = int(args.get("precision", 5))  # 5 = 1m
        mgrs_str = mgrs_converter.toMGRS(lat, lon, MGRSPrecision=precision)
        return MCPToolResult(ok=True, data={"mgrs": mgrs_str})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))


def tool_from_mgrs(args: dict) -> MCPToolResult:
    try:
        mgrs_str = str(args["mgrs"])
        lat, lon = mgrs_converter.toLatLon(mgrs_str)
        return MCPToolResult(ok=True, data={"lat": lat, "lon": lon})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))


def tool_transform(args: dict) -> MCPToolResult:
    try:
        lat = float(args["lat"])
        lon = float(args["lon"])
        source_crs = args.get("source_crs", "EPSG:4326")
        target_crs = args["target_crs"]

        transformer = Transformer.from_crs(CRS.from_user_input(source_crs),
                                           CRS.from_user_input(target_crs),
                                           always_xy=True)
        x, y = transformer.transform(lon, lat)
        return MCPToolResult(ok=True, data={"x": x, "y": y, "target_crs": target_crs})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))


def tool_distance(args: dict) -> MCPToolResult:
    try:
        lat1 = float(args["lat1"])
        lon1 = float(args["lon1"])
        lat2 = float(args["lat2"])
        lon2 = float(args["lon2"])

        meters = haversine_distance_m(lat1, lon1, lat2, lon2)
        return MCPToolResult(ok=True, data={"distance_m": meters})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))


def tool_load_geojson(args: dict) -> MCPToolResult:
    try:
        key = args["key"]
        data = args["geojson"]
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                pass
        
        if isinstance(data, str) and os.path.exists(data):
             with open(data, 'r') as f:
                 data = json.load(f)
        
        geom = shape(data)
        GEOMETRY_STORE[key] = geom
        return MCPToolResult(ok=True, data={"message": f"Stored {geom.geom_type} as '{key}'"})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))


def tool_buffer(args: dict) -> MCPToolResult:
    try:
        key = args["key"]
        dist = float(args["distance_m"])
        if key not in GEOMETRY_STORE:
            return MCPToolResult(ok=False, error=f"Geometry '{key}' not found")
        
        geom = GEOMETRY_STORE[key]
        local_geom, local_crs = project_geom_to_meters(geom)
        buffered_local = local_geom.buffer(dist)
        buffered_wgs = project_geom_from_meters(buffered_local, local_crs)
        
        return MCPToolResult(ok=True, data={"geometry": mapping(buffered_wgs)})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))


def tool_intersect(args: dict) -> MCPToolResult:
    try:
        key_a = args["key_a"]
        key_b = args["key_b"]
        if key_a not in GEOMETRY_STORE or key_b not in GEOMETRY_STORE:
            return MCPToolResult(ok=False, error="Geometry key not found")
        
        geom_a = GEOMETRY_STORE[key_a]
        geom_b = GEOMETRY_STORE[key_b]
        
        intersection = geom_a.intersection(geom_b)
        return MCPToolResult(ok=True, data={"geometry": mapping(intersection)})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))


def tool_within(args: dict) -> MCPToolResult:
    try:
        key_a = args["key_a"]
        key_b = args["key_b"]
        if key_a not in GEOMETRY_STORE or key_b not in GEOMETRY_STORE:
            return MCPToolResult(ok=False, error="Geometry key not found")
        
        geom_a = GEOMETRY_STORE[key_a]
        geom_b = GEOMETRY_STORE[key_b]
        
        is_within = geom_a.within(geom_b)
        return MCPToolResult(ok=True, data={"within": is_within})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))


def tool_elevation(args: dict) -> MCPToolResult:
    try:
        lat = float(args["lat"])
        lon = float(args["lon"])
        
        ds, crs = load_dem_for_point(lat, lon)
        if ds:
            # Project point to tile CRS
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
            
        # Fallback stub
        elevation_m = 1000.0 + (lat % 1.0) * 100 + (lon % 1.0) * 10
        return MCPToolResult(ok=True, data={"elevation_m": elevation_m, "source": "stub"})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))


def tool_line_of_sight(args: dict) -> MCPToolResult:
    try:
        obs_lat = float(args["observer_lat"])
        obs_lon = float(args["observer_lon"])
        tgt_lat = float(args["target_lat"])
        tgt_lon = float(args["target_lon"])
        obs_height = float(args.get("observer_height_m", 2.0))
        tgt_height = float(args.get("target_height_m", 2.0))
        
        ds, crs = load_dem_for_point(obs_lat, obs_lon)
        if not ds:
             return MCPToolResult(ok=False, error="No DTED available for LOS")
             
        n_samples = int(args.get("samples", 128))
        lats = np.linspace(obs_lat, tgt_lat, n_samples)
        lons = np.linspace(obs_lon, tgt_lon, n_samples)
        
        # Project path to tile CRS for sampling
        if crs != "EPSG:4326":
            xs, ys = transform("EPSG:4326", crs, lons, lats)
        else:
            xs, ys = lons, lats

        band = ds.read(1)
        elevations = []
        for x, y in zip(xs, ys):
            row, col = ds.index(x, y)
            if 0 <= row < ds.height and 0 <= col < ds.width:
                elevations.append(float(band[row, col]))
            else:
                elevations.append(0.0)
        ds.close()
        
        dists = [haversine_distance_m(obs_lat, obs_lon, lat, lon) for lat, lon in zip(lats, lons)]
        total_dist = dists[-1]
        
        obs_elev = elevations[0] + obs_height
        tgt_elev = elevations[-1] + tgt_height
        
        los_clear = True
        max_block = 0.0
        
        for i in range(1, n_samples - 1):
            frac = dists[i] / total_dist
            line_height = obs_elev + frac * (tgt_elev - obs_elev)
            terrain_height = elevations[i]
            diff = terrain_height - line_height
            if diff > 0:
                los_clear = False
                max_block = max(max_block, diff)
                
        return MCPToolResult(ok=True, data={
            "line_of_sight": los_clear,
            "max_block_m": max_block,
            "distance_m": total_dist
        })
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))


def tool_render_heatmap(args: dict) -> MCPToolResult:
    try:
        # Default to full extent of first tile if no bounds provided
        # For simplicity, just render the first tile found or the one covering lat/lon
        lat = args.get("lat")
        lon = args.get("lon")
        
        ds = None
        if lat is not None and lon is not None:
            ds, crs = tile_manager.get_tile(float(lat), float(lon))
        elif tile_manager.tiles:
            # Just pick the first one
            ds = rasterio.open(tile_manager.tiles[0][1])
            
        if not ds:
            return MCPToolResult(ok=False, error="No elevation data found to render.")

        # Read data (downsample for speed/size if needed)
        data = ds.read(1)
        
        # Mask nodata
        if ds.nodata is not None:
            data = np.ma.masked_equal(data, ds.nodata)
            
        # Create plot
        plt.figure(figsize=(8, 6))
        plt.imshow(data, cmap='terrain')
        plt.colorbar(label='Elevation (m)')
        plt.title(f"Elevation Heatmap")
        plt.axis('off')
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        plt.close()
        buf.seek(0)
        
        # Encode
        img_b64 = base64.b64encode(buf.read()).decode('utf-8')
        ds.close()
        
        return MCPToolResult(ok=True, data={
            "image_base64": img_b64,
            "format": "png",
            "message": "Rendered elevation heatmap."
        })
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))


def tool_get_terrain_grid(args: dict) -> MCPToolResult:
    try:
        min_lat = float(args["min_lat"])
        max_lat = float(args["max_lat"])
        min_lon = float(args["min_lon"])
        max_lon = float(args["max_lon"])
        width = int(args.get("width", 50))
        height = int(args.get("height", 50))
        
        lats = np.linspace(min_lat, max_lat, height)
        lons = np.linspace(min_lon, max_lon, width)
        
        # We need to sample from the tiles. 
        # Optimization: find the tile that covers the center and read from it directly if possible,
        # otherwise sample point by point (slow but correct for multi-tile).
        # For this demo, let's just sample point by point but use the TileManager's cache.
        
        grid = []
        for lat in lats:
            row_vals = []
            for lon in lons:
                ds, crs = tile_manager.get_tile(lat, lon)
                val = 0.0
                if ds:
                    if crs != "EPSG:4326":
                         xs, ys = transform("EPSG:4326", crs, [lon], [lat])
                         x, y = xs[0], ys[0]
                    else:
                         x, y = lon, lat
                    
                    r, c = ds.index(x, y)
                    if 0 <= r < ds.height and 0 <= c < ds.width:
                        val = float(ds.read(1)[r, c])
                row_vals.append(val)
            grid.append(row_vals)
            
        return MCPToolResult(ok=True, data={
            "grid": grid,
            "lats": lats.tolist(),
            "lons": lons.tolist()
        })
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))


TOOLS = {
    "to_mgrs": {
        "name": "to_mgrs",
        "description": "Convert WGS84 lat/lon to MGRS string.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lon": {"type": "number"},
                "precision": {
                    "type": "integer",
                    "description": "MGRS precision digits (1–5). Default 5 = 1m."
                }
            },
            "required": ["lat", "lon"]
        }
    },
    "from_mgrs": {
        "name": "from_mgrs",
        "description": "Convert MGRS string to WGS84 lat/lon.",
        "input_schema": {
            "type": "object",
            "properties": {
                "mgrs": {"type": "string"}
            },
            "required": ["mgrs"]
        }
    },
    "transform": {
        "name": "transform",
        "description": "Transform coordinates from source CRS to target CRS.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lon": {"type": "number"},
                "source_crs": {
                    "type": "string",
                    "description": "Default EPSG:4326"
                },
                "target_crs": {
                    "type": "string",
                    "description": "Target CRS, e.g. 'EPSG:3857' or 'EPSG:32633'."
                }
            },
            "required": ["lat", "lon", "target_crs"]
        }
    },
    "distance": {
        "name": "distance",
        "description": "Great-circle distance in meters between two WGS84 points.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat1": {"type": "number"},
                "lon1": {"type": "number"},
                "lat2": {"type": "number"},
                "lon2": {"type": "number"}
            },
            "required": ["lat1", "lon1", "lat2", "lon2"]
        }
    },
    "elevation": {
        "name": "elevation",
        "description": "Get elevation in meters at a point (uses DTED if available, else stub).",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number"},
                "lon": {"type": "number"}
            },
            "required": ["lat", "lon"]
        }
    },
    "load_geojson": {
        "name": "load_geojson",
        "description": "Load GeoJSON geometry into memory store.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Unique ID for the geometry"},
                "geojson": {"type": "string", "description": "GeoJSON string or file path"}
            },
            "required": ["key", "geojson"]
        }
    },
    "buffer": {
        "name": "buffer",
        "description": "Buffer a geometry by a distance in meters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "distance_m": {"type": "number"}
            },
            "required": ["key", "distance_m"]
        }
    },
    "intersect": {
        "name": "intersect",
        "description": "Calculate intersection of two geometries.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key_a": {"type": "string"},
                "key_b": {"type": "string"}
            },
            "required": ["key_a", "key_b"]
        }
    },
    "within": {
        "name": "within",
        "description": "Check if geometry A is within geometry B.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key_a": {"type": "string"},
                "key_b": {"type": "string"}
            },
            "required": ["key_a", "key_b"]
        }
    },
    "line_of_sight": {
        "name": "line_of_sight",
        "description": "Calculate line of sight between two points using DTED.",
        "input_schema": {
            "type": "object",
            "properties": {
                "observer_lat": {"type": "number"},
                "observer_lon": {"type": "number"},
                "target_lat": {"type": "number"},
                "target_lon": {"type": "number"},
                "observer_height_m": {"type": "number", "default": 2.0},
                "target_height_m": {"type": "number", "default": 2.0}
            },
            "required": ["observer_lat", "observer_lon", "target_lat", "target_lon"]
        }
    },
    "render_heatmap": {
        "name": "render_heatmap",
        "description": "Render a visual heatmap of the elevation data.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "description": "Center latitude (optional)"},
                "lon": {"type": "number", "description": "Center longitude (optional)"}
            }
        }
    },
    "get_terrain_grid": {
        "name": "get_terrain_grid",
        "description": "Get a 2D grid of elevations for a bounding box.",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_lat": {"type": "number"},
                "max_lat": {"type": "number"},
                "min_lon": {"type": "number"},
                "max_lon": {"type": "number"},
                "width": {"type": "integer", "default": 50},
                "height": {"type": "integer", "default": 50}
            },
            "required": ["min_lat", "max_lat", "min_lon", "max_lon"]
        }
    }
}


def dispatch_tool_call(call: MCPToolCall) -> MCPToolResult:
    print(f"[MCP LOG] Tool Call: {call.name} | Args: {call.arguments}")
    if call.name == "to_mgrs":
        return tool_to_mgrs(call.arguments)
    if call.name == "from_mgrs":
        return tool_from_mgrs(call.arguments)
    if call.name == "transform":
        return tool_transform(call.arguments)
    if call.name == "distance":
        return tool_distance(call.arguments)
    if call.name == "elevation":
        return tool_elevation(call.arguments)
    if call.name == "load_geojson":
        return tool_load_geojson(call.arguments)
    if call.name == "buffer":
        return tool_buffer(call.arguments)
    if call.name == "intersect":
        return tool_intersect(call.arguments)
    if call.name == "within":
        return tool_within(call.arguments)
    if call.name == "line_of_sight":
        return tool_line_of_sight(call.arguments)
    if call.name == "render_heatmap":
        return tool_render_heatmap(call.arguments)
    if call.name == "get_terrain_grid":
        return tool_get_terrain_grid(call.arguments)
    return MCPToolResult(ok=False, error=f"Unknown tool: {call.name}")


# ---------- MCP-ish HTTP Endpoints ----------

@app.get("/mcp/tools", response_model=MCPListToolsResult)
def list_tools():
    return MCPListToolsResult(tools=list(TOOLS.values()))


@app.post("/mcp/call", response_model=MCPToolResult)
def call_tool(call: MCPToolCall):
    return dispatch_tool_call(call)
