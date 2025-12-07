#!/bin/bash

# Start MCP Server in background
uvicorn server:app --host 0.0.0.0 --port 8000 &

# Wait for server to be ready
sleep 5

# Start Gradio Dashboard
python gradio_dashboard.py
