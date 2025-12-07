#!/usr/bin/env python3
"""
3D Drone Flight Path Visualization (Integrated with Geo MCP Server)
"""

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import json
import requests
import os

MCP_BASE_URL = "http://localhost:8000"

def call_mcp(name, arguments):
    try:
        resp = requests.post(f"{MCP_BASE_URL}/mcp/call", json={"name": name, "arguments": arguments})
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(f"MCP Error: {data.get('error')}")
        return data["data"]
    except Exception as e:
        print(f"Connection Error: {str(e)}")
        raise

def main():
    print("Loading route data...")
    with open('routes.geojson', 'r') as f:
        routes_data = json.load(f)

    route1 = routes_data['features'][0]
    route_coords = route1['geometry']['coordinates']
    route_lons = np.array([coord[0] for coord in route_coords])
    route_lats = np.array([coord[1] for coord in route_coords])

    # Determine bounding box for terrain
    min_lon, max_lon = route_lons.min() - 0.02, route_lons.max() + 0.02
    min_lat, max_lat = route_lats.min() - 0.02, route_lats.max() + 0.02

    print(f"Fetching terrain grid for bbox: {min_lat:.4f}, {min_lon:.4f} to {max_lat:.4f}, {max_lon:.4f}...")
    
    # Call MCP server to get terrain grid
    grid_data = call_mcp("get_terrain_grid", {
        "min_lat": min_lat, "max_lat": max_lat,
        "min_lon": min_lon, "max_lon": max_lon,
        "width": 60, "height": 60
    })
    
    grid_elev = np.array(grid_data["grid"])
    grid_lats = np.array(grid_data["lats"])
    grid_lons = np.array(grid_data["lons"])
    grid_lon_mesh, grid_lat_mesh = np.meshgrid(grid_lons, grid_lats)

    print("Fetching flight path elevations...")
    # Sample elevation for each route point
    route_ground_elevs = []
    for lat, lon in zip(route_lats, route_lons):
        res = call_mcp("elevation", {"lat": lat, "lon": lon})
        route_ground_elevs.append(res["elevation_m"])
    route_ground_elevs = np.array(route_ground_elevs)

    drone_altitude_agl = 100
    route_elevs = route_ground_elevs + drone_altitude_agl

    # Plotting
    print("Generating 3D plot...")
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Convert to km relative to origin
    origin_lon, origin_lat = min_lon, min_lat
    lon_to_km = 111.0 * np.cos(np.radians(origin_lat))
    lat_to_km = 111.0

    X = (grid_lon_mesh - origin_lon) * lon_to_km
    Y = (grid_lat_mesh - origin_lat) * lat_to_km
    Z = grid_elev

    route_X = (route_lons - origin_lon) * lon_to_km
    route_Y = (route_lats - origin_lat) * lat_to_km
    route_Z = route_elevs

    # Plot terrain
    surf = ax.plot_surface(X, Y, Z, cmap='terrain', alpha=0.8, linewidth=0, antialiased=True)
    
    # Plot route
    ax.plot(route_X, route_Y, route_Z, 'r-', linewidth=3, label='Drone Path', zorder=10)
    
    # Shadow
    ax.plot(route_X, route_Y, route_ground_elevs, 'k--', linewidth=1, alpha=0.5, label='Ground Track')

    # Start/End
    ax.scatter([route_X[0]], [route_Y[0]], [route_Z[0]], c='lime', s=100, label='Start')
    ax.scatter([route_X[-1]], [route_Y[-1]], [route_Z[-1]], c='blue', s=100, label='End')

    ax.set_xlabel('East-West (km)')
    ax.set_ylabel('North-South (km)')
    ax.set_zlabel('Elevation (m)')
    ax.set_title(f'Drone Flight Path over Real Terrain\n(Data from Geo MCP Server)')
    
    fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10, label='Elevation (m)')
    ax.legend()
    
    output_file = 'drone_flight_real_data.png'
    plt.savefig(output_file, dpi=150)
    print(f"Saved visualization to {output_file}")

if __name__ == "__main__":
    main()
