import json
import os

CONFIG_PATH = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")

# The configuration we want to add
NEW_SERVER_CONFIG = {
    "command": "/Users/gmossy/.pyenv/versions/3.13.9/bin/python",
    "args": [
        "/Users/gmossy/CascadeProjects/geo-mcp-server/bridge.py"
    ]
}

def main():
    if not os.path.exists(CONFIG_PATH):
        print(f"Config file not found at {CONFIG_PATH}")
        # Create it?
        config = {"mcpServers": {}}
    else:
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError:
            print("Error decoding JSON. Backing up and starting fresh?")
            return

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    print(f"Adding 'geo-mcp' to {CONFIG_PATH}...")
    config["mcpServers"]["geo-mcp"] = NEW_SERVER_CONFIG

    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)
    
    print("Success! Please restart Claude Desktop.")

if __name__ == "__main__":
    main()
