#!/usr/bin/env python3
"""
Test script for Elasticsearch MCP resources.
This script demonstrates how to access the MCP resources we've added to the Elasticsearch MCP server.
"""
import json
import os
import sys
import subprocess
import time
from typing import Dict, Any

# Function to pretty print JSON responses
def print_json_response(response: str) -> None:
    try:
        data = json.loads(response)
        print(json.dumps(data, indent=2))
    except json.JSONDecodeError:
        print(response)

def main():
    # Check if ES_CLOUD_ID and ES_API_KEY environment variables are set
    es_cloud_id = os.environ.get("ES_CLOUD_ID")
    es_api_key = os.environ.get("ES_API_KEY")
    
    if not es_cloud_id or not es_api_key:
        print("Error: ES_CLOUD_ID and ES_API_KEY environment variables must be set.")
        print("Example usage:")
        print("  ES_CLOUD_ID=your_cloud_id ES_API_KEY=your_api_key python test_es_resources.py")
        sys.exit(1)
    
    # Start the MCP server in a separate process
    print("Starting Elasticsearch MCP server...")
    server_process = subprocess.Popen(
        ["python", "es_mcp_server.py"],
        env={**os.environ, "ES_CLOUD_ID": es_cloud_id, "ES_API_KEY": es_api_key},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Give the server a moment to start up
    time.sleep(2)
    
    # Check if the server started successfully
    if server_process.poll() is not None:
        print("Error: Failed to start the MCP server.")
        stdout, stderr = server_process.communicate()
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        sys.exit(1)
    
    print("Server started successfully!")
    print("\nNOTE: This is a demonstration script. In a real scenario, you would:")
    print("1. Run the MCP server in one terminal")
    print("2. Use the MCP client or Claude's access_mcp_resource tool to access the resources\n")
    
    # Simulate accessing resources (this won't actually work in this script)
    print("To test the resources with Claude, you would use the access_mcp_resource tool like this:")
    print("\n1. List all indices:")
    print("   <access_mcp_resource>")
    print("   <server_name>elasticsearch-mcp-server</server_name>")
    print("   <uri>elasticsearch://indices</uri>")
    print("   </access_mcp_resource>")
    
    print("\n2. Get information about a specific index (replace 'your_index_name'):")
    print("   <access_mcp_resource>")
    print("   <server_name>elasticsearch-mcp-server</server_name>")
    print("   <uri>elasticsearch://index/your_index_name</uri>")
    print("   </access_mcp_resource>")
    
    print("\n3. Get mapping for a specific index (replace 'your_index_name'):")
    print("   <access_mcp_resource>")
    print("   <server_name>elasticsearch-mcp-server</server_name>")
    print("   <uri>elasticsearch://mapping/your_index_name</uri>")
    print("   </access_mcp_resource>")
    
    # Clean up
    print("\nTerminating the server...")
    server_process.terminate()
    server_process.wait()
    print("Server terminated.")

if __name__ == "__main__":
    main()
