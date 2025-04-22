#!/usr/bin/env python3
"""
Script to configure the Elasticsearch MCP server in the Claude MCP settings file.
"""
import json
import os
import sys

def main():
    # Get the ES_CLOUD_ID and ES_API_KEY from command line arguments
    if len(sys.argv) != 3:
        print("Error: ES_CLOUD_ID and ES_API_KEY must be provided as command line arguments.")
        print("Example usage:")
        print("  python configure_mcp_server.py your_cloud_id your_api_key")
        sys.exit(1)
    
    es_cloud_id = sys.argv[1]
    es_api_key = sys.argv[2]
    
    # Path to the Claude MCP settings file
    settings_path = os.path.expanduser("~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json")
    
    # Check if the settings file exists
    if not os.path.exists(settings_path):
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(settings_path), exist_ok=True)
        
        # Create a new settings file with the Elasticsearch MCP server
        settings = {
            "mcpServers": {
                "elasticsearch": {
                    "command": "python",
                    "args": [os.path.abspath("es_mcp_server.py")],
                    "env": {
                        "ES_CLOUD_ID": es_cloud_id,
                        "ES_API_KEY": es_api_key
                    },
                    "disabled": False,
                    "autoApprove": []
                }
            }
        }
    else:
        # Load the existing settings file
        try:
            with open(settings_path, "r") as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Failed to parse the settings file at {settings_path}")
            sys.exit(1)
        
        # Add or update the Elasticsearch MCP server
        if "mcpServers" not in settings:
            settings["mcpServers"] = {}
        
        settings["mcpServers"]["elasticsearch"] = {
            "command": "python",
            "args": [os.path.abspath("es_mcp_server.py")],
            "env": {
                "ES_CLOUD_ID": es_cloud_id,
                "ES_API_KEY": es_api_key
            },
            "disabled": False,
            "autoApprove": []
        }
    
    # Write the settings file
    try:
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=2)
        print(f"Successfully configured the Elasticsearch MCP server in {settings_path}")
        print("Please restart VS Code to apply the changes.")
    except Exception as e:
        print(f"Error: Failed to write the settings file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
