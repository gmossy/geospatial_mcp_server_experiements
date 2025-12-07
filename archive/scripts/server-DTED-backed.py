import os
import numpy as np
import rasterio
from rasterio import windows

DTED_ROOT = os.getenv("DTED_ROOT", "./dted")  # directory of DTED/GeoTIFF tiles


def load_dem_for_point(lat, lon):
    """
    Very simplistic tile locator; in reality you'd map lat/lon to a specific DTED tile.
    For now, assume a single dem.tif in DTED_ROOT.
    """
    dem_path = os.path.join(DTED_ROOT, "dem.tif")
    if not os.path.exists(dem_path):
        raise FileNotFoundError(f"DEM not found at {dem_path}")
    ds = rasterio.open(dem_path)
    return ds


def sample_elevation(lat, lon):
    ds = load_dem_for_point(lat, lon)
    x, y = ds.transform * (lon, lat)  # or rasterio.warp.transform if needed
    row, col = ds.index(lon, lat)
    elev = float(ds.read(1)[row, col])
    ds.close()
    return elev


def tool_dted_elevation(args: dict) -> MCPToolResult:
    try:
        lat = float(args["lat"])
        lon = float(args["lon"])
        elevation_m = sample_elevation(lat, lon)
        return MCPToolResult(ok=True, data={"elevation_m": elevation_m})
    except Exception as e:
        return MCPToolResult(ok=False, error=str(e))


def tool_line_of_sight(args: dict) -> MCPToolResult:
    """
    Very simplified LOS: sample elevations between observer and target, check blockages.
    """
    try:
        obs_lat = float(args["observer_lat"])
        obs_lon = float(args["observer_lon"])
        tgt_lat = float(args["target_lat"])
        tgt_lon = float(args["target_lon"])
        obs_height = float(args.get("observer_height_m", 2.0))
        tgt_height = float(args.get("target_height_m", 2.0))

        ds = load_dem_for_point(obs_lat, obs_lon)  # naive: single DEM
        n_samples = int(args.get("samples", 128))

        lats = np.linspace(obs_lat, tgt_lat, n_samples)
        lons = np.linspace(obs_lon, tgt_lon, n_samples)

        # elevations along the path
        band = ds.read(1)
        elevations = []
        for lat, lon in zip(lats, lons):
            row, col = ds.index(lon, lat)
            elevations.append(float(band[row, col]))
        ds.close()

        # distances along path
        dists = [haversine_distance_m(obs_lat, obs_lon, lat, lon) for lat, lon in zip(lats, lons)]
        total_dist = dists[-1]

        # line from observer eye height to target height
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
