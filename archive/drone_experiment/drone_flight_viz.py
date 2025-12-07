#!/usr/bin/env python3
"""
3D Drone Flight Path Visualization
Shows drone flying Route 1 (East Arc) over Grand Canyon terrain
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from scipy.interpolate import griddata
import json

# Load route data
with open('/mnt/user-data/outputs/routes.geojson', 'r') as f:
    routes_data = json.load(f)

# Extract Route 1 coordinates
route1 = routes_data['features'][0]
route_coords = route1['geometry']['coordinates']
route_lons = np.array([coord[0] for coord in route_coords])
route_lats = np.array([coord[1] for coord in route_coords])

# Terrain elevation data
terrain_samples = [
    (-112.1, 36.1, 734.0),      # Start - canyon floor
    (-112.15, 36.05, 2067.0),   # Southwest rim
    (-112.05, 36.15, 1024.5),   # Northeast
    (-112.08, 36.08, 1196.0),   # Center-south
    (-112.12, 36.12, 1020.8),   # Northwest
    (-112.11, 36.11, 1019.9),   # Target
    (-112.1, 36.06, 1716.0),    # South rim
    (-112.1, 36.14, 1023.0),    # North
    (-112.05, 36.05, 1500.0),   # SE corner
    (-112.15, 36.15, 1800.0),   # NW corner
]

terrain_lons = np.array([s[0] for s in terrain_samples])
terrain_lats = np.array([s[1] for s in terrain_samples])
terrain_elevs = np.array([s[2] for s in terrain_samples])

# Create high-resolution terrain grid
grid_resolution = 100
grid_lon = np.linspace(-112.15, -112.05, grid_resolution)
grid_lat = np.linspace(36.05, 36.15, grid_resolution)
grid_lon_mesh, grid_lat_mesh = np.meshgrid(grid_lon, grid_lat)

# Interpolate terrain elevation
grid_elev = griddata(
    (terrain_lons, terrain_lats), terrain_elevs,
    (grid_lon_mesh, grid_lat_mesh),
    method='cubic'
)

# Calculate drone flight path elevations (interpolate terrain + flight altitude)
# Interpolate terrain elevation along the route
route_terrain_elev = griddata(
    (terrain_lons, terrain_lats), terrain_elevs,
    (route_lons, route_lats),
    method='linear'
)

# Drone flies at 100m above terrain
drone_altitude_agl = 100  # meters above ground level
route_elevs = route_terrain_elev + drone_altitude_agl

# Create figure with 3D subplot
fig = plt.figure(figsize=(18, 12))
ax = fig.add_subplot(111, projection='3d')

# Convert lat/lon to relative coordinates (in km from origin)
origin_lon, origin_lat = -112.1, 36.1
lon_to_km = 111.0 * np.cos(np.radians(origin_lat))  # km per degree longitude
lat_to_km = 111.0  # km per degree latitude

# Convert terrain mesh to km
X = (grid_lon_mesh - origin_lon) * lon_to_km
Y = (grid_lat_mesh - origin_lat) * lat_to_km
Z = grid_elev

# Convert route to km
route_X = (route_lons - origin_lon) * lon_to_km
route_Y = (route_lats - origin_lat) * lat_to_km
route_Z = route_elevs

# Plot terrain surface
terrain_plot = ax.plot_surface(X, Y, Z, cmap='terrain', alpha=0.7,
                                linewidth=0, antialiased=True, 
                                vmin=np.nanmin(Z), vmax=np.nanmax(Z))

# Plot drone flight path (full route)
ax.plot(route_X, route_Y, route_Z, 'r-', linewidth=3, 
        label='Drone Flight Path', zorder=10)

# Mark start and end points
start_X, start_Y = route_X[0], route_Y[0]
start_Z = route_Z[0]
end_X, end_Y = route_X[-1], route_Y[-1]
end_Z = route_Z[-1]

ax.scatter([start_X], [start_Y], [start_Z], c='lime', s=300, marker='o',
           edgecolors='black', linewidths=2, label='Start', zorder=15)
ax.scatter([end_X], [end_Y], [end_Z], c='red', s=300, marker='^',
           edgecolors='black', linewidths=2, label='Target', zorder=15)

# Add vertical lines showing drone altitude above ground
sample_indices = np.linspace(0, len(route_X)-1, 15, dtype=int)
for idx in sample_indices:
    ground_elev = route_terrain_elev[idx]
    ax.plot([route_X[idx], route_X[idx]], 
            [route_Y[idx], route_Y[idx]], 
            [ground_elev, route_Z[idx]], 
            'b--', alpha=0.4, linewidth=1)

# Add waypoint markers along the route
waypoint_indices = np.linspace(0, len(route_X)-1, 8, dtype=int)
ax.scatter(route_X[waypoint_indices], route_Y[waypoint_indices], 
           route_Z[waypoint_indices],
           c='yellow', s=100, marker='o', edgecolors='black', 
           linewidths=1, alpha=0.8, zorder=12)

# Labels and formatting
ax.set_xlabel('Distance East-West (km)', fontsize=11, weight='bold', labelpad=10)
ax.set_ylabel('Distance North-South (km)', fontsize=11, weight='bold', labelpad=10)
ax.set_zlabel('Elevation (meters)', fontsize=11, weight='bold', labelpad=10)

title = (
    '3D Drone Flight Path - Grand Canyon Terrain\n'
    f'Route 1 (East Arc): {route1["properties"]["distance_m"]:.0f}m | '
    f'Flight Altitude: {drone_altitude_agl}m AGL'
)
ax.set_title(title, fontsize=14, weight='bold', pad=20)

# Colorbar for terrain
cbar = fig.colorbar(terrain_plot, ax=ax, shrink=0.6, aspect=20, pad=0.1)
cbar.set_label('Terrain Elevation (m)', fontsize=10, weight='bold')

# Set viewing angle for best perspective
ax.view_init(elev=25, azim=45)

# Add grid
ax.grid(True, alpha=0.3)

# Legend
ax.legend(loc='upper left', fontsize=11, framealpha=0.9)

# Add flight statistics text box
flight_stats = (
    f'FLIGHT STATISTICS\n'
    f'─────────────────\n'
    f'Total Distance: {route1["properties"]["distance_m"]:.0f}m\n'
    f'Flight Altitude: {drone_altitude_agl}m AGL\n'
    f'Start Elevation: {start_Z:.0f}m MSL\n'
    f'End Elevation: {end_Z:.0f}m MSL\n'
    f'Min Terrain: {np.nanmin(Z):.0f}m\n'
    f'Max Terrain: {np.nanmax(Z):.0f}m\n'
    f'Waypoints: {len(waypoint_indices)}'
)

# Add text annotation in 3D space
ax.text2D(0.02, 0.98, flight_stats, transform=ax.transAxes,
          fontsize=9, verticalalignment='top', family='monospace',
          bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9, 
                   edgecolor='black', linewidth=1.5))

plt.tight_layout()
plt.savefig('/mnt/user-data/outputs/drone_flight_3d.png', dpi=300, bbox_inches='tight')
print("✓ 3D flight visualization saved!")

# Create multiple viewing angles
angles = [
    (25, 45, 'perspective'),
    (60, 45, 'high_angle'),
    (10, 90, 'side_view'),
    (10, 0, 'front_view'),
]

for elev, azim, name in angles:
    fig2 = plt.figure(figsize=(16, 10))
    ax2 = fig2.add_subplot(111, projection='3d')
    
    # Plot terrain
    ax2.plot_surface(X, Y, Z, cmap='terrain', alpha=0.7,
                     linewidth=0, antialiased=True)
    
    # Plot flight path
    ax2.plot(route_X, route_Y, route_Z, 'r-', linewidth=3.5, 
            label='Drone Path', zorder=10)
    
    # Mark points
    ax2.scatter([start_X], [start_Y], [start_Z], c='lime', s=400, 
               marker='o', edgecolors='black', linewidths=2, zorder=15)
    ax2.scatter([end_X], [end_Y], [end_Z], c='red', s=400, 
               marker='^', edgecolors='black', linewidths=2, zorder=15)
    
    # Altitude reference lines
    for idx in sample_indices:
        ground_elev = route_terrain_elev[idx]
        ax2.plot([route_X[idx], route_X[idx]], 
                [route_Y[idx], route_Y[idx]], 
                [ground_elev, route_Z[idx]], 
                'b--', alpha=0.3, linewidth=1)
    
    ax2.set_xlabel('Distance E-W (km)', fontsize=10, weight='bold')
    ax2.set_ylabel('Distance N-S (km)', fontsize=10, weight='bold')
    ax2.set_zlabel('Elevation (m)', fontsize=10, weight='bold')
    ax2.set_title(f'Drone Flight - {name.replace("_", " ").title()} View', 
                 fontsize=13, weight='bold')
    ax2.view_init(elev=elev, azim=azim)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper left', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(f'/mnt/user-data/outputs/drone_flight_{name}.png', 
                dpi=250, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Saved {name} view")

print(f"\n{'='*60}")
print("DRONE FLIGHT VISUALIZATION COMPLETE")
print(f"{'='*60}")
print(f"\nGenerated views:")
print(f"  • Main perspective view")
print(f"  • High angle view (bird's eye)")
print(f"  • Side view (elevation profile)")
print(f"  • Front view")
print(f"\nAll visualizations saved to outputs/")
print(f"{'='*60}\n")
