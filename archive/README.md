# Geospatial MCP Server & AI Assistant

A powerful Model Context Protocol (MCP) server for geospatial analysis, featuring a real-time AI Assistant, 3D terrain visualization, and drone mission planning capabilities.

![Drone Mission](drone_flight_real_data.png)

## 🌍 Features

*   **Geospatial Tools**:
    *   `elevation`: Get elevation at any coordinate (uses DTED/SRTM data).
    *   `line_of_sight`: Calculate visibility between two points over terrain.
    *   `render_heatmap`: Generate visual elevation heatmaps.
    *   `distance`: Calculate great-circle distances.
    *   `get_terrain_grid`: Fetch raw elevation grids for 3D rendering.
    *   `to_mgrs` / `from_mgrs`: Coordinate conversion.
*   **AI Assistant**:
    *   Chat with your data using open-source LLMs (via Hugging Face).
    *   Ask questions like "Can I see point B from point A?" or "Plan a drone route."
    *   Visual responses (heatmaps displayed directly in chat).
*   **3D Visualization**:
    *   Interactive 3D plots of terrain and drone flight paths.
    *   Support for custom GeoJSON route uploads.
*   **MCP Compliant**:
    *   Implements the Model Context Protocol.
    *   Can be connected to Claude Desktop or other MCP clients via `bridge.py`.

## 🚀 Getting Started

### Prerequisites

*   Docker (recommended) OR Python 3.11+
*   A Hugging Face API Token (free) for the AI Assistant.

### Quick Start (Docker)

1.  **Clone the repository**:
    ```bash
    git clone <your-repo-url>
    cd geo-mcp-server
    ```

2.  **Configure Environment**:
    Create a `.env` file in the root directory:
    ```bash
    HF_TOKEN=hf_YourHuggingFaceTokenHere
    ```

3.  **Build and Run**:
    ```bash
    make build
    make run
    ```

4.  **Access the Dashboard**:
    Open [http://localhost:7860](http://localhost:7860) in your browser.

### Local Development

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Install System Libraries** (if needed for GDAL/Rasterio):
    *   Ubuntu: `apt-get install gdal-bin libgdal-dev`
    *   MacOS: `brew install gdal`

3.  **Run Server**:
    ```bash
    ./start.sh
    ```

## 📂 Project Structure

*   `server.py`: The core FastAPI server implementing the MCP tools.
*   `gradio_dashboard.py`: The web UI with AI Assistant and 3D visualization.
*   `bridge.py`: An MCP Stdio adapter for connecting to Claude Desktop.
*   `dted/`: Directory for storing elevation data (DTED/SRTM files).
*   `sample_routes/`: Example GeoJSON files for drone missions.
*   `scripts/`: Utilities for downloading data and testing.

## 🤖 AI Assistant

The dashboard includes a "AI Assistant" tab powered by `Qwen/Qwen2.5-72B-Instruct` (via Hugging Face). It can reason about geospatial data and call tools to answer complex queries.

**Example Queries:**
*   "What is the elevation at 36.1, -112.1?"
*   "Check if a drone at 100m altitude can fly safely from 36.1, -112.1 to 36.15, -112.15."
*   "Show me a terrain heatmap around 36.1, -112.1."

## 🔌 Connecting to Claude Desktop

You can use this server as a tool provider for Claude Desktop.

1.  Ensure the server is running (e.g., via Docker or locally).
2.  Configure Claude Desktop to use `bridge.py` (requires `uv` or python environment):
    ```json
    "geo-server": {
      "command": "python",
      "args": ["/path/to/geo-mcp-server/bridge.py"]
    }
    ```
    *Note: The bridge currently assumes the HTTP server is running at localhost:8000.*

## 🗺️ Data Sources

The server uses DTED (Digital Terrain Elevation Data) or SRTM data.
*   Place `.dt2` or `.hgt` files in the `dted/` directory.
*   Use `scripts/download_aws_terrain.py` to fetch data from AWS Open Data.

## 📄 License

[MIT License](LICENSE)
