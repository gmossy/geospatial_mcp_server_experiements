#!/bin/bash

# Start the real MCP server (WebSocket) in background
python -m mcp.server &

# Wait for the MCP server to be ready (adjust if needed)
sleep 5

# Start Gradio Dashboard UI
python gradio_dashboard.py
