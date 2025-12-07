#!/usr/bin/env python3
"""
Animated Drone Flight Sequence
Creates a sequence showing drone progress along the flight path
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from mpl_toolkits.mplot3d import Axes3D
from scipy.interpolate import griddata
import json

print("Generating animated drone flight sequence...")

# Load route data
with open('/mnt/user-data/outputs/routes.geojson', 'r') as f:
    routes_data = json.load(f)

route1 = routes_data['features'][0]
route_coords = route1['geometry']['coordinates']
route_lons = np.array([coord[0] for coord in route_coords])
route_lats = np.array([coord[1] for coord in route_coords])

# Terrain data
terrain_samples = [
    (-112.1, 36.1, 734.0), (-112.15, 36.05, 2067.0), (-112.05, 36.15, 1024.5),
    (-112.08, 36.08, 1196.0), (-112.12, 36.12, 1020.8), (-112.11, 36.11, 1019.9),
    (-112.1, 36.06, 1716.0), (-112.1, 36.14, 1023.0), (-112.05, 36.05, 1500.0),
    (-112.15, 36.15, 1800.0),
]

terrain_lons = np.array([s[0] for s in terrain_samples])
terrain_lats = np.array([s[1] for s in terrain_samples])
terrain_elevs = np.array([s[2] for s in terrain_samples])

# Create terrain grid
grid_lon = np.linspace(-112.15, -112.05, 80)
grid_lat = np.linspace(36.05, 36.15, 80)
grid_lon_mesh, grid_lat_mesh = np.meshgrid(grid_lon, grid_lat)
grid_elev = griddata((terrain_lons, terrain_lats), terrain_elevs,
                     (grid_lon_mesh, grid_lat_mesh), method='cubic')

# Calculate route elevations
route_terrain_elev = griddata((terrain_lons, terrain_lats), terrain_elevs,
                              (route_lons, route_lats), method='linear')
drone_altitude_agl = 100
route_elevs = route_terrain_elev + drone_altitude_agl

# Convert to km coordinates
origin_lon, origin_lat = -112.1, 36.1
lon_to_km = 111.0 * np.cos(np.radians(origin_lat))
lat_to_km = 111.0

X = (grid_lon_mesh - origin_lon) * lon_to_km
Y = (grid_lat_mesh - origin_lat) * lat_to_km
Z = grid_elev

route_X = (route_lons - origin_lon) * lon_to_km
route_Y = (route_lats - origin_lat) * lat_to_km
route_Z = route_elevs

# Create sequence of frames showing drone progress
num_frames = 12
frame_indices = np.linspace(0, len(route_X)-1, num_frames, dtype=int)

# Create composite image showing all frames
fig = plt.figure(figsize=(20, 12))

for frame_num, idx in enumerate(frame_indices):
    ax = fig.add_subplot(3, 4, frame_num+1, projection='3d')
    
    # Plot terrain
    ax.plot_surface(X, Y, Z, cmap='terrain', alpha=0.6, 
                   linewidth=0, antialiased=True)
    
    # Plot completed path (up to current position)
    if idx > 0:
        ax.plot(route_X[:idx+1], route_Y[:idx+1], route_Z[:idx+1], 
               'g-', linewidth=2.5, alpha=0.7, label='Completed')
    
    # Plot remaining path
    if idx < len(route_X)-1:
        ax.plot(route_X[idx:], route_Y[idx:], route_Z[idx:], 
               'r--', linewidth=1.5, alpha=0.4, label='Remaining')
    
    # Current drone position (larger, animated marker)
    ax.scatter([route_X[idx]], [route_Y[idx]], [route_Z[idx]], 
              c='red', s=500, marker='o', edgecolors='yellow', 
              linewidths=3, label='Drone', zorder=20)
    
    # Add drone "shadow" on ground
    ground_elev = route_terrain_elev[idx]
    ax.scatter([route_X[idx]], [route_Y[idx]], [ground_elev], 
              c='black', s=200, marker='o', alpha=0.3, zorder=1)
    
    # Vertical line from drone to ground
    ax.plot([route_X[idx], route_X[idx]], 
           [route_Y[idx], route_Y[idx]], 
           [ground_elev, route_Z[idx]], 
           'y-', linewidth=2, alpha=0.6)
    
    # Start and end markers
    ax.scatter([route_X[0]], [route_Y[0]], [route_Z[0]], 
              c='lime', s=200, marker='o', edgecolors='black', 
              linewidths=1.5, alpha=0.7, zorder=10)
    ax.scatter([route_X[-1]], [route_Y[-1]], [route_Z[-1]], 
              c='blue', s=200, marker='^', edgecolors='black', 
              linewidths=1.5, alpha=0.7, zorder=10)
    
    # Calculate progress
    progress = (idx / (len(route_X)-1)) * 100
    distance_flown = (idx / (len(route_X)-1)) * route1['properties']['distance_m']
    
    # Title with progress
    ax.set_title(f'Frame {frame_num+1}/{num_frames} | {progress:.0f}% Complete\n'
                f'{distance_flown:.0f}m / {route1["properties"]["distance_m"]:.0f}m',
                fontsize=10, weight='bold')
    
    # Minimal labels for compact view
    ax.set_xlabel('E-W (km)', fontsize=8)
    ax.set_ylabel('N-S (km)', fontsize=8)
    ax.set_zlabel('Elev (m)', fontsize=8)
    
    # Set consistent viewing angle
    ax.view_init(elev=30, azim=45)
    ax.grid(True, alpha=0.2)
    
    # Small legend
    if frame_num == 0:
        ax.legend(loc='upper left', fontsize=7, framealpha=0.8)

plt.suptitle('Drone Flight Animation Sequence - Route 1 (East Arc)\n'
            'Grand Canyon Terrain | 100m Above Ground Level',
            fontsize=15, weight='bold', y=0.98)

plt.tight_layout()
plt.savefig('/mnt/user-data/outputs/drone_animation_sequence.png', 
           dpi=300, bbox_inches='tight')
print("✓ Animation sequence saved!")

# Create a "trail" view showing drone path with position history
fig2 = plt.figure(figsize=(18, 12))
ax2 = fig2.add_subplot(111, projection='3d')

# Plot terrain
ax2.plot_surface(X, Y, Z, cmap='terrain', alpha=0.5, 
                linewidth=0, antialiased=True)

# Plot full flight path
ax2.plot(route_X, route_Y, route_Z, 'gray', linewidth=2, 
        alpha=0.3, label='Flight Path')

# Show drone positions at different time steps with fading trail
trail_positions = np.linspace(0, len(route_X)-1, 20, dtype=int)
colors_trail = plt.cm.hot(np.linspace(0, 1, len(trail_positions)))

for i, (idx, color) in enumerate(zip(trail_positions, colors_trail)):
    size = 100 + (i / len(trail_positions)) * 400  # Grow in size
    alpha = 0.3 + (i / len(trail_positions)) * 0.7  # Fade in
    
    ax2.scatter([route_X[idx]], [route_Y[idx]], [route_Z[idx]], 
               c=[color], s=size, marker='o', alpha=alpha,
               edgecolors='black', linewidths=1, zorder=10+i)

# Current position (largest)
current_idx = trail_positions[-1]
ax2.scatter([route_X[current_idx]], [route_Y[current_idx]], [route_Z[current_idx]], 
           c='red', s=600, marker='o', edgecolors='yellow', 
           linewidths=4, label='Current Position', zorder=30)

# Start and end
ax2.scatter([route_X[0]], [route_Y[0]], [route_Z[0]], 
           c='lime', s=400, marker='o', edgecolors='black', 
           linewidths=2, label='Start', zorder=25)
ax2.scatter([route_X[-1]], [route_Y[-1]], [route_Z[-1]], 
           c='blue', s=400, marker='^', edgecolors='black', 
           linewidths=2, label='Target', zorder=25)

ax2.set_xlabel('Distance East-West (km)', fontsize=12, weight='bold')
ax2.set_ylabel('Distance North-South (km)', fontsize=12, weight='bold')
ax2.set_zlabel('Elevation (meters)', fontsize=12, weight='bold')
ax2.set_title('Drone Flight Path with Motion Trail\n'
             'Color intensity shows progression (blue→yellow→red)',
             fontsize=14, weight='bold', pad=20)

ax2.view_init(elev=25, azim=50)
ax2.grid(True, alpha=0.3)
ax2.legend(loc='upper left', fontsize=11, framealpha=0.9)

plt.tight_layout()
plt.savefig('/mnt/user-data/outputs/drone_flight_trail.png', 
           dpi=300, bbox_inches='tight')
print("✓ Motion trail visualization saved!")

# Create elevation profile view
fig3, (ax_top, ax_bottom) = plt.subplots(2, 1, figsize=(18, 12))

# Top: 3D perspective
ax3d = fig3.add_subplot(2, 1, 1, projection='3d')
ax3d.plot_surface(X, Y, Z, cmap='terrain', alpha=0.6, linewidth=0)
ax3d.plot(route_X, route_Y, route_Z, 'r-', linewidth=4, label='Flight Path')
ax3d.scatter([route_X[0]], [route_Y[0]], [route_Z[0]], 
            c='lime', s=400, marker='o', edgecolors='black', linewidths=2)
ax3d.scatter([route_X[-1]], [route_Y[-1]], [route_Z[-1]], 
            c='blue', s=400, marker='^', edgecolors='black', linewidths=2)
ax3d.set_xlabel('E-W (km)', fontsize=10, weight='bold')
ax3d.set_ylabel('N-S (km)', fontsize=10, weight='bold')
ax3d.set_zlabel('Elevation (m)', fontsize=10, weight='bold')
ax3d.set_title('3D View', fontsize=12, weight='bold')
ax3d.view_init(elev=20, azim=45)
ax3d.grid(True, alpha=0.3)

# Bottom: Elevation profile
distance_along_route = np.zeros(len(route_X))
for i in range(1, len(route_X)):
    dx = route_X[i] - route_X[i-1]
    dy = route_Y[i] - route_Y[i-1]
    distance_along_route[i] = distance_along_route[i-1] + np.sqrt(dx**2 + dy**2)

# Convert to meters
distance_along_route_m = distance_along_route * 1000

ax_bottom.fill_between(distance_along_route_m, 0, route_terrain_elev, 
                       color='saddlebrown', alpha=0.6, label='Terrain')
ax_bottom.plot(distance_along_route_m, route_Z, 'r-', linewidth=3, 
              label=f'Drone Flight Path ({drone_altitude_agl}m AGL)')
ax_bottom.plot(distance_along_route_m, route_terrain_elev, 'k-', 
              linewidth=1.5, alpha=0.7, label='Ground Level')

# Fill area between drone and ground
ax_bottom.fill_between(distance_along_route_m, route_terrain_elev, route_Z,
                       color='lightblue', alpha=0.3, label='Clearance')

ax_bottom.axhline(y=route_Z[0], color='lime', linestyle='--', 
                 linewidth=1.5, alpha=0.5, label='Start Alt')
ax_bottom.axhline(y=route_Z[-1], color='blue', linestyle='--', 
                 linewidth=1.5, alpha=0.5, label='End Alt')

ax_bottom.set_xlabel('Distance Along Route (meters)', fontsize=12, weight='bold')
ax_bottom.set_ylabel('Elevation (meters)', fontsize=12, weight='bold')
ax_bottom.set_title('Elevation Profile - Side View', fontsize=12, weight='bold')
ax_bottom.grid(True, alpha=0.4, linestyle='--')
ax_bottom.legend(loc='upper right', fontsize=10, framealpha=0.9)

plt.suptitle('Drone Flight Path - 3D and Elevation Profile\n'
            f'Total Distance: {route1["properties"]["distance_m"]:.0f}m | '
            f'Altitude: {drone_altitude_agl}m AGL',
            fontsize=15, weight='bold', y=0.98)

plt.tight_layout()
plt.savefig('/mnt/user-data/outputs/drone_flight_profile.png', 
           dpi=300, bbox_inches='tight')
print("✓ Elevation profile saved!")

print(f"\n{'='*60}")
print("COMPLETE! Generated 3 drone flight visualizations:")
print(f"{'='*60}")
print("  1. drone_animation_sequence.png - 12-frame progression")
print("  2. drone_flight_trail.png - Motion trail effect")  
print("  3. drone_flight_profile.png - 3D + elevation profile")
print(f"{'='*60}\n")
