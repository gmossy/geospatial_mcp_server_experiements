# Drone Mission Simulation

This experiment demonstrates how the **Geospatial MCP Server** can power complex, real-world downstream applications like 3D mission planning.

## What is this?

This is a full-stack demonstration that:
1.  **Defines a Flight Path**: A drone route (GeoJSON) flying over the Grand Canyon.
2.  **Fetches Real Terrain**: The application queries the MCP Server for real elevation data (DTED/SRTM) under the flight path.
3.  **Visualizes in 3D**: It generates a 3D visualization of the drone's trajectory relative to the terrain, calculating ground clearance and line-of-sight.

## How to Run

### 1. Ensure Server is Running
The Geo MCP Server must be running with elevation data loaded.
```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```

### 2. Run the Visualization
You have two options:

**Option A: Command Line (Static Image)**
Generates a high-quality PNG image of the mission.
```bash
python run_drone_experiment.py
```
*Output: `drone_flight_real_data.png`*

**Option B: Gradio Dashboard (Interactive)**
Launches a web UI to run the simulation interactively.
```bash
python gradio_dashboard.py
```
*Open `http://localhost:7860` -> "Drone Mission" tab.*

## How it Works

1.  **Client**: The script (or Gradio UI) reads `routes.geojson` to get the flight path (lat/lon coordinates).
2.  **MCP Call (Terrain)**: It calls `get_terrain_grid` on the MCP server.
    - The server looks up the relevant GeoTIFF tiles in its `dted/` directory.
    - It resamples the elevation data into a grid and returns it.
3.  **MCP Call (Elevation)**: It calls `elevation` for each waypoint to calculate the exact ground height below the drone.
4.  **Rendering**: The client uses `matplotlib` to render the 3D surface and the flight path vector, showing the drone's altitude (AGL) relative to the rugged terrain.
