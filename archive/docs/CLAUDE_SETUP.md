# Claude Desktop Setup

To connect Claude Desktop to your running Geo MCP Server, you need to configure it to use the `bridge.py` script. This script acts as a bridge between Claude (stdio) and your running server (HTTP).

## 1. Locate your Python

You need the full path to the Python executable where you installed the dependencies.
Based on your environment, it is likely:
`/Users/gmossy/.pyenv/versions/3.13.9/bin/python`

## 2. Edit Config

Open (or create) your Claude Desktop config file:
`~/Library/Application Support/Claude/claude_desktop_config.json`

Add the following entry:

```json
{
  "mcpServers": {
    "geo-mcp": {
      "command": "/Users/gmossy/.pyenv/versions/3.13.9/bin/python",
      "args": [
        "/Users/gmossy/CascadeProjects/geo-mcp-server/bridge.py"
      ]
    }
  }
}
```

## 3. Restart Claude

Restart the Claude Desktop app. It should now connect to your running server via the bridge.

**Note**: Ensure your local server is running (`uvicorn server:app ...`) before using Claude, as the bridge connects to `localhost:8000`.
