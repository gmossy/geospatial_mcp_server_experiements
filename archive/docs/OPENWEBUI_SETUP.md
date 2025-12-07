# OpenWebUI Integration

You can use OpenWebUI (formerly Ollama WebUI) to visualize this data, but it requires adding a custom **Tool**.

## 1. Prerequisites
- OpenWebUI running (usually on port 3000).
- This Geo MCP Server running on port 8000.
- **Important**: If OpenWebUI is running in Docker, it cannot see `localhost:8000`. You must use `http://host.docker.internal:8000` in the tool script.

## 2. Add the Tool
1.  Open OpenWebUI.
2.  Go to **Workspace** -> **Tools**.
3.  Click **"+"** (Create Tool).
4.  **Name**: `Geo Tools`
5.  **Description**: `Tools for geospatial analysis, elevation, and terrain visualization.`
6.  **Content**: Copy and paste the code from `openwebui_tools.py`.
    - *Note*: Check the `MCP_BASE_URL` variable at the top of the script. If using Docker, ensure it is `http://host.docker.internal:8000`.

## 3. Enable the Tool
1.  Go to a **New Chat**.
2.  Select a model (e.g., Llama 3, GPT-4o).
3.  Look for the **Tools** menu (usually a `+` or `#` icon) and enable "Geo Tools".

## 4. Visualize
Ask questions like:
> "Render a heatmap of the terrain at 36.1, -112.1"

OpenWebUI will execute the Python function, get the base64 image from your server, and render it as an image in the chat!
