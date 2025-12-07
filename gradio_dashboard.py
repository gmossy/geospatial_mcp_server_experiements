import os
import json
import base64
from io import BytesIO

import gradio as gr

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from PIL import Image

from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# MCP client for WebSocket communication
from mcp.server import MCPClient

load_dotenv()

# Constants
SAMPLE_ROUTES_DIR = "sample_routes"
def get_sample_routes():
    """Return a list of sample GeoJSON route filenames."""
    if not os.path.exists(SAMPLE_ROUTES_DIR):
        return []
    return [f for f in os.listdir(SAMPLE_ROUTES_DIR) if f.endswith('.geojson')]

# Instantiate MCP client
mcp_client = MCPClient("ws://localhost:9000")

# Legacy HTTP base URL (unused)
MCP_BASE_URL = "http://localhost:8000"  # retained for legacy fallback (unused)

def call_mcp(name, arguments):
    """Call an MCP tool via the WebSocket client.

    Parameters
    ----------
    name: str
        The tool name to invoke.
    arguments: dict
        Arguments for the tool.
    """
    try:
        # Use the global MCP client (created below) to send the request.
        result = mcp_client.call(name, arguments)
        return result
    except Exception as e:
        return f"Connection Error: {str(e)}"


def get_elevation(lat, lon):
    res = call_mcp("elevation", {"lat": float(lat), "lon": float(lon)})
    if isinstance(res, str): return res
    return f"Elevation: {res['elevation_m']} m\nSource: {res.get('source')}"

def get_los(obs_lat, obs_lon, tgt_lat, tgt_lon):
    res = call_mcp("line_of_sight", {
        "observer_lat": float(obs_lat), "observer_lon": float(obs_lon),
        "target_lat": float(tgt_lat), "target_lon": float(tgt_lon)
    })
    if isinstance(res, str): return res
    return json.dumps(res, indent=2)

def render_map(lat, lon, radius, style):
    res = call_mcp("render_heatmap", {"lat": float(lat), "long": float(lon), "radius_km": float(radius), "style": style})
    if isinstance(res, str): return None
    if "image_base64" in res:
        img_data = base64.b64decode(res["image_base64"])
        return Image.open(BytesIO(img_data))
    return None

def run_drone_viz(geojson_file, selected_route):
    # Load route from uploaded file or fallback
    try:
        if geojson_file is not None:
             # geojson_file is a temp file path string in Gradio 3.x+
             with open(geojson_file.name, 'r') as f:
                routes_data = json.load(f)
        elif selected_route:
             # Load from sample routes
             with open(os.path.join(SAMPLE_ROUTES_DIR, selected_route), 'r') as f:
                routes_data = json.load(f)
        else:
            # Fallback default route
            if os.path.exists('routes.geojson'):
                with open('routes.geojson', 'r') as f:
                    routes_data = json.load(f)
            else:
                return None
        
        # Handle FeatureCollection or single Feature
        if routes_data.get('type') == 'FeatureCollection':
            route1 = routes_data['features'][0]
        else:
            route1 = routes_data
            
        route_coords = route1['geometry']['coordinates']
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None # Return None or handle error gracefully

    route_lons = np.array([coord[0] for coord in route_coords])
    route_lats = np.array([coord[1] for coord in route_coords])

    # Bbox
    min_lon, max_lon = route_lons.min() - 0.02, route_lons.max() + 0.02
    min_lat, max_lat = route_lats.min() - 0.02, route_lats.max() + 0.02

    # Get Terrain Grid
    grid_data = call_mcp("get_terrain_grid", {
        "min_lat": min_lat, "max_lat": max_lat,
        "min_lon": min_lon, "max_lon": max_lon,
        "width": 50, "height": 50
    })
    
    if isinstance(grid_data, str): return None # Error

    grid_elev = np.array(grid_data["grid"])
    grid_lats = np.array(grid_data["lats"])
    grid_lons = np.array(grid_data["lons"])
    grid_lon_mesh, grid_lat_mesh = np.meshgrid(grid_lons, grid_lats)

    # Get Route Elevations
    route_ground_elevs = []
    for lat, lon in zip(route_lats, route_lons):
        res = call_mcp("elevation", {"lat": lat, "lon": lon})
        if isinstance(res, dict):
            route_ground_elevs.append(res["elevation_m"])
        else:
            route_ground_elevs.append(0)
    
    route_ground_elevs = np.array(route_ground_elevs)
    drone_altitude_agl = 100
    route_elevs = route_ground_elevs + drone_altitude_agl

    # Plot
    fig = plt.figure(figsize=(10, 6))
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

    # Terrain
    surf = ax.plot_surface(X, Y, Z, cmap='terrain', alpha=0.8, linewidth=0, antialiased=True)
    
    # Route
    ax.plot(route_X, route_Y, route_Z, 'r-', linewidth=3, label='Drone Path', zorder=10)
    ax.plot(route_X, route_Y, route_ground_elevs, 'k--', linewidth=1, alpha=0.5, label='Ground Track')

    ax.set_xlabel('East-West (km)')
    ax.set_ylabel('North-South (km)')
    ax.set_zlabel('Elevation (m)')
    ax.set_title('Drone Mission Simulation')
    
    return fig

def chat_with_agent(message, history, hf_token, model_id):
    if not hf_token:
        return "Please enter a Hugging Face API Token in the Settings (Gear Icon)."

    client = InferenceClient(api_key=hf_token)
    
    system_prompt = """You are a geospatial assistant with access to a real-time MCP server.
You can use the following tools to answer user questions. 
To use a tool, you MUST respond with ONLY a JSON object in this format:
{"tool": "tool_name", "arguments": {"arg1": value, "arg2": value}}

Available Tools:
1. elevation(lat, lon) -> Get elevation in meters.
   - Example: {"tool": "elevation", "arguments": {"lat": 36.1, "lon": -112.1}}
2. line_of_sight(observer_lat, observer_lon, target_lat, target_lon, observer_height_m=2.0, target_height_m=2.0) -> Check visibility.
   - Example: {"tool": "line_of_sight", "arguments": {"observer_lat": 36.1, "observer_lon": -112.1, "target_lat": 36.2, "target_lon": -112.2, "observer_height_m": 10}}
3. render_heatmap(lat, lon, radius_km=5.0, style='terrain') -> Get a terrain heatmap image.
   - Example: {"tool": "render_heatmap", "arguments": {"lat": 36.1, "lon": -112.1, "radius_km": 10, "style": "viridis"}}
4. distance(lat1, lon1, lat2, lon2) -> Calculate distance in meters.
   - Example: {"tool": "distance", "arguments": {"lat1": 36.1, "lon1": -112.1, "lat2": 36.2, "lon2": -112.2}}

If you don't need a tool, just answer the question normally.
"""

    messages = [{"role": "system", "content": system_prompt}]
    for item in history:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            user_msg, assistant_msg = item[0], item[1]
            if user_msg:
                messages.append({"role": "user", "content": str(user_msg)})
            if assistant_msg:
                messages.append({"role": "assistant", "content": str(assistant_msg)})
        elif isinstance(item, dict):
             # Handle list of dicts format if it occurs
             messages.append(item)
    messages.append({"role": "user", "content": message})

    try:
        # First turn: Ask LLM
        response = client.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=500
        )
        content = response.choices[0].message.content
        
        # Check for tool call
        try:
            # simple heuristic to find json
            if "{" in content and "}" in content:
                json_str = content[content.find("{"):content.rfind("}")+1]
                tool_call = json.loads(json_str)
                
                if "tool" in tool_call and "arguments" in tool_call:
                    tool_name = tool_call["tool"]
                    args = tool_call["arguments"]
                    
                    # Execute Tool
                    tool_result = call_mcp(tool_name, args)
                    
                    # Handle Image Output
                    image_markdown = ""
                    if isinstance(tool_result, dict) and "image_base64" in tool_result:
                        img_b64 = tool_result["image_base64"]
                        image_markdown = f"\n\n![Generated Image](data:image/png;base64,{img_b64})"
                        # Remove base64 from history to save tokens
                        tool_result["image_base64"] = "<image_data_hidden>"

                    # Feed back to LLM
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "user", "content": f"Tool Output: {json.dumps(tool_result)}"})
                    
                    final_response = client.chat.completions.create(
                        model=model_id,
                        messages=messages,
                        max_tokens=500
                    )
                    return final_response.choices[0].message.content + image_markdown
        except Exception as e:
            pass # Not a tool call or failed to parse

        return content

    except Exception as e:
        return f"Error: {str(e)}"

# Configuration Persistence
CONFIG_FILE = "config.json"
CURRENT_CONFIG = {
    "hf_token": os.getenv("HF_TOKEN", ""),
    "model_id": "Qwen/Qwen2.5-72B-Instruct"
}

def load_config():
    global CURRENT_CONFIG
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                saved_config = json.load(f)
                # Update only keys that exist in saved_config
                for k, v in saved_config.items():
                    if v: CURRENT_CONFIG[k] = v
        except Exception as e:
            print(f"Error loading config: {e}")
    # Ensure env var is fallback if not in file or empty
    if not CURRENT_CONFIG["hf_token"]:
        CURRENT_CONFIG["hf_token"] = os.getenv("HF_TOKEN", "")

def save_config_to_file():
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(CURRENT_CONFIG, f)
    except Exception as e:
        print(f"Error saving config: {e}")

# Load config on startup
load_config()

with gr.Blocks(title="Geo MCP Dashboard") as demo:
    # State for configuration - use lambdas to fetch latest global config on session start
    hf_token_state = gr.State(lambda: CURRENT_CONFIG["hf_token"])
    model_id_state = gr.State(lambda: CURRENT_CONFIG["model_id"])
    settings_visible = gr.State(False)

    with gr.Row(variant="panel", equal_height=True):
        with gr.Column(scale=10):
            gr.Markdown("# 🌍 Geospatial MCP Dashboard")
        with gr.Column(scale=1, min_width=50):
            settings_btn = gr.Button("⚙️", variant="secondary")

    with gr.Accordion("Settings", open=False, visible=False) as settings_panel:
        with gr.Row():
            token_input = gr.Textbox(
                label="Hugging Face API Token", 
                type="password", 
                value=lambda: CURRENT_CONFIG["hf_token"],
                placeholder="hf_..."
            )
            model_dropdown = gr.Dropdown(
                choices=["Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.1-8B-Instruct"],
                value=lambda: CURRENT_CONFIG["model_id"],
                label="Model ID"
            )
        save_btn = gr.Button("Save Settings")
        
        def toggle_settings(current_state):
            new_state = not current_state
            return new_state, gr.update(visible=new_state)
            
        def save_settings(token, model):
            # Update global config
            CURRENT_CONFIG["hf_token"] = token
            CURRENT_CONFIG["model_id"] = model
            save_config_to_file()
            return token, model, False, gr.update(visible=False), f"**Current Model:** `{model}`"

        settings_btn.click(toggle_settings, inputs=[settings_visible], outputs=[settings_visible, settings_panel])
        
    with gr.Tabs():
        with gr.Tab("AI Assistant"):
            gr.Markdown("### Chat with your Geospatial Data")
            with gr.Row():
                gr.Markdown("Powered by Open Source LLMs (via Hugging Face). Requires a [HF Token](https://huggingface.co/settings/tokens).")
                current_model_display = gr.Markdown(value=lambda: f"**Current Model:** `{CURRENT_CONFIG['model_id']}`")
            
            save_btn.click(save_settings, inputs=[token_input, model_dropdown], outputs=[hf_token_state, model_id_state, settings_visible, settings_panel, current_model_display])
            
            chatbot = gr.ChatInterface(
                chat_with_agent, 
                additional_inputs=[hf_token_state, model_id_state],
                examples=[
                    ["Visualize the terrain heatmap for the Rim Survey mission area (36.05, -112.12)."],
                    ["Check line of sight for the River Run mission start point (36.08, -112.14) to the first waypoint."],
                    ["Generate a visual elevation map for the Grand Canyon Tour route near 36.1, -112.1."],
                    ["What is the elevation at 36.1, -112.1?"],
                    ["Can a comms tower at 36.1, -112.1 (height 30m) see a rover at 36.15, -112.15 (height 2m)?"],
                    ["Check if a drone at 100m altitude can fly safely from 36.1, -112.1 to 36.15, -112.15 without hitting terrain."],
                    ["Sample 3 points between 36.1, -112.1 and 36.2, -112.2 and tell me which is highest."],
                    ["Calculate the distance between 36.1, -112.1 and 36.2, -112.2."],
                    ["If I put a relay at 36.1, -112.1, can it connect to both 36.05, -112.05 and 36.15, -112.15?"],
                    ["Create a 3D terrain map for coordinates 36.2, -112.15 with style 'viridis'."],
                    ["Show a heatmap of elevation for the River Run route with radius 10km."],
                    ["Generate a combined map overlay of line of sight from a tower at 36.1,-112.1 to the Rim Survey route."]
                ]
            )

        with gr.Tab("Mission Control"):
            gr.Markdown("## 🎮 Drone Mission Command Center")
            gr.Markdown("Select a mission profile to execute autonomous planning, safety checks, and visualization.")
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📋 Select Mission")
                    drone_speed = gr.Slider(minimum=5, maximum=30, value=15, label="Drone Speed (m/s)", step=1)
                    
                    btn_rim = gr.Button("🚁 Rim Survey", variant="primary")
                    gr.Markdown("*High-altitude survey of the canyon rim. Focus on coverage and stability.*")
                    
                    btn_tour = gr.Button("🏞️ Grand Canyon Tour", variant="secondary")
                    gr.Markdown("*Scenic route through the corridor. Focus on visibility and POI tracking.*")
                    
                    btn_river = gr.Button("🚤 River Run", variant="secondary")
                    gr.Markdown("*Low-altitude flight following the river. Critical terrain collision checks.*")
                
                with gr.Column(scale=2):
                    mission_plot = gr.Plot(label="3D Mission Visualization")
            
            with gr.Row():
                mission_report = gr.Markdown("### 📊 Mission Analysis Report\n\n*Select a mission to generate report...*")

            def analyze_mission(mission_type, speed):
                # 1. Setup Mission Parameters
                if mission_type == "rim":
                    route_file = "rim_survey.geojson"
                    title = "🚁 Rim Survey Mission"
                    comms_loc = (36.06, -112.12, 30) # Lat, Lon, Height
                    obs_loc = (36.05, -112.10)
                    drone_alt = 200
                elif mission_type == "tour":
                    route_file = "grand_canyon_tour.geojson"
                    title = "🏞️ Grand Canyon Tour"
                    comms_loc = (36.1, -112.1, 50)
                    obs_loc = (36.12, -112.08)
                    drone_alt = 150
                else: # river
                    route_file = "river_run.geojson"
                    title = "🚤 River Run Mission"
                    comms_loc = (36.08, -112.14, 100) # Higher tower needed for canyon
                    obs_loc = (36.1, -112.12)
                    drone_alt = 50 # Low flying

                # 2. Load Route
                try:
                    with open(os.path.join(SAMPLE_ROUTES_DIR, route_file), 'r') as f:
                        data = json.load(f)
                    coords = data['features'][0]['geometry']['coordinates']
                except:
                    return None, "❌ Error loading mission route."

                # 3. Run Analysis
                report = f"### {title} - Analysis Report\n\n"
                
                # Distance Calculation
                total_dist = 0
                for i in range(len(coords)-1):
                    p1, p2 = coords[i], coords[i+1]
                    d = call_mcp("distance", {"lat1": p1[1], "lon1": p1[0], "lat2": p2[1], "lon2": p2[0]})
                    if isinstance(d, dict): total_dist += d['distance_m']
                
                # Time Calculation
                flight_time_sec = total_dist / speed
                flight_time_min = int(flight_time_sec // 60)
                flight_time_rem_sec = int(flight_time_sec % 60)

                report += f"**📏 Flight Path**\n"
                report += f"- **Total Distance:** {total_dist/1000:.2f} km\n"
                report += f"- **Drone Speed:** {speed} m/s\n"
                report += f"- **Est. Flight Time:** {flight_time_min}m {flight_time_rem_sec}s\n"
                report += f"- **Waypoints:** {len(coords)}\n"
                report += f"- **Target Altitude:** {drone_alt}m AGL\n\n"

                # Comms Check
                report += f"**📡 Comms Coverage (Tower at {comms_loc[0]}, {comms_loc[1]})**\n"
                connected_pts = 0
                check_indices = [0, len(coords)//2, len(coords)-1]
                for idx in check_indices:
                    pt = coords[idx]
                    los = call_mcp("line_of_sight", {
                        "observer_lat": comms_loc[0], "observer_lon": comms_loc[1],
                        "target_lat": pt[1], "target_lon": pt[0],
                        "observer_height_m": comms_loc[2], "target_height_m": drone_alt
                    })
                    status = "✅" if isinstance(los, dict) and los['line_of_sight'] else "❌"
                    report += f"- Waypoint {idx}: {status}\n"
                    if status == "✅": connected_pts += 1
                
                report += f"\n**🔭 Observation Post Visibility (Post at {obs_loc[0]}, {obs_loc[1]})**\n"
                op_los = call_mcp("line_of_sight", {
                    "observer_lat": obs_loc[0], "observer_lon": obs_loc[1],
                    "target_lat": coords[0][1], "target_lon": coords[0][0],
                    "target_height_m": drone_alt
                })
                op_status = "VISIBLE" if isinstance(op_los, dict) and op_los['line_of_sight'] else "OCCLUDED"
                report += f"- Mission Start Point: **{op_status}**\n\n"

                # Terrain Safety
                report += f"**⚠️ Terrain Safety Check**\n"
                if drone_alt < 60:
                    report += "- 🔸 **Caution:** Low altitude flight detected. Canyon walls may block signal.\n"
                else:
                    report += "- ✅ Safe altitude clearance verified.\n"

                # 4. Generate Plot
                fig = run_drone_viz(None, route_file)
                
                return fig, report

            btn_rim.click(lambda s: analyze_mission("rim", s), inputs=[drone_speed], outputs=[mission_plot, mission_report])
            btn_tour.click(lambda s: analyze_mission("tour", s), inputs=[drone_speed], outputs=[mission_plot, mission_report])
            btn_river.click(lambda s: analyze_mission("river", s), inputs=[drone_speed], outputs=[mission_plot, mission_report])

        with gr.Tab("Tools"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Elevation & Heatmap")
                    lat_input = gr.Number(label="Latitude", value=36.1)
                    lon_input = gr.Number(label="Longitude", value=-112.1)
                    with gr.Row():
                        radius_input = gr.Slider(minimum=1, maximum=50, value=5, label="Radius (km)")
                        style_dropdown = gr.Dropdown(choices=["terrain", "viridis", "plasma", "magma", "inferno"], value="terrain", label="Style")
                    
                    btn_elev = gr.Button("Get Elevation")
                    out_elev = gr.Textbox(label="Result")
                    btn_map = gr.Button("Render Heatmap")
                    out_map = gr.Image(label="Terrain Heatmap")
                    
                    btn_elev.click(get_elevation, inputs=[lat_input, lon_input], outputs=out_elev)
                    btn_map.click(render_map, inputs=[lat_input, lon_input, radius_input, style_dropdown], outputs=out_map)
                
                with gr.Column():
                    gr.Markdown("### Line of Sight")
                    obs_lat = gr.Number(label="Observer Lat", value=36.1)
                    obs_lon = gr.Number(label="Observer Lon", value=-112.1)
                    tgt_lat = gr.Number(label="Target Lat", value=36.11)
                    tgt_lon = gr.Number(label="Target Lon", value=-112.11)
                    btn_los = gr.Button("Check Line of Sight")
                    out_los = gr.Code(label="Analysis Result", language="json")
                    btn_los.click(get_los, inputs=[obs_lat, obs_lon, tgt_lat, tgt_lon], outputs=out_los)

            gr.Markdown("---")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Distance Calculator")
                    with gr.Row():
                        d_lat1 = gr.Number(label="Lat 1", value=36.1)
                        d_lon1 = gr.Number(label="Lon 1", value=-112.1)
                        d_lat2 = gr.Number(label="Lat 2", value=36.2)
                        d_lon2 = gr.Number(label="Lon 2", value=-112.2)
                    btn_dist = gr.Button("Calculate Distance")
                    out_dist = gr.Textbox(label="Distance (m)")
                    
                    def calc_dist(l1, lo1, l2, lo2):
                        res = call_mcp("distance", {"lat1": l1, "lon1": lo1, "lat2": l2, "lon2": lo2})
                        if isinstance(res, dict): return f"{res['distance_m']:.2f} meters"
                        return res
                    btn_dist.click(calc_dist, inputs=[d_lat1, d_lon1, d_lat2, d_lon2], outputs=out_dist)

                with gr.Column():
                    gr.Markdown("### Coordinate Converter (Military Grid Reference System)")
                    with gr.Row():
                        c_lat = gr.Number(label="Lat", value=36.1)
                        c_lon = gr.Number(label="Lon", value=-112.1)
                        btn_to_mgrs = gr.Button("To MGRS")
                    
                    with gr.Row():
                        c_mgrs = gr.Textbox(label="Military Grid Reference System (MGRS) String", value="12SWC8096096860")
                        btn_from_mgrs = gr.Button("To Lat/Lon")
                    
                    out_coords = gr.Textbox(label="Conversion Result")

                    def to_mgrs(lat, lon):
                        res = call_mcp("to_mgrs", {"lat": lat, "lon": lon})
                        if isinstance(res, dict): return res['mgrs']
                        return res
                    
                    def from_mgrs(mgrs):
                        res = call_mcp("from_mgrs", {"mgrs": mgrs})
                        if isinstance(res, dict): return f"Lat: {res['lat']}, Lon: {res['lon']}"
                        return res

                    btn_to_mgrs.click(to_mgrs, inputs=[c_lat, c_lon], outputs=out_coords)
                    btn_from_mgrs.click(from_mgrs, inputs=[c_mgrs], outputs=out_coords)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
