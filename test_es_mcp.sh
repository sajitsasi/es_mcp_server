#!/bin/bash
# Test script for Elasticsearch MCP resources

# Check if ES_CLOUD_ID and ES_API_KEY are provided
if [ -z "$MCP_SERVER_CWD" ]; then 
  if [ -z "$ES_CLOUD_ID" ] || [ -z "$ES_API_KEY" ]; then
    echo "Error: ES_CLOUD_ID and ES_API_KEY environment variables must be set."
    echo "Usage: ES_CLOUD_ID=your_cloud_id ES_API_KEY=your_api_key ./test_es_mcp.sh"
    exit 1
  fi
else
  echo "Using vars from ${MCP_SERVER_CWD}/.env..."
fi

# Function to clean up on exit
cleanup() {
    echo "Cleaning up..."
    # Kill the MCP server if it's running
    if [ ! -z "$SERVER_PID" ]; then
        kill $SERVER_PID 2>/dev/null
        echo "MCP server stopped."
    fi
    exit 0
}

# Set up trap to clean up on exit
trap cleanup EXIT INT TERM

# Start the MCP server in the background
echo "Starting Elasticsearch MCP server..."
python es_mcp_server.py > es_mcp_server.log 2>&1 &
SERVER_PID=$!

# Wait a moment for the server to start
sleep 2

# Check if the server started successfully
if ! ps -p $SERVER_PID > /dev/null; then
    echo "Error: Failed to start the MCP server. Check es_mcp_server.log for details."
    cat es_mcp_server.log
    exit 1
fi

echo "Server started successfully with PID: $SERVER_PID"
echo "Server logs are being written to es_mcp_server.log"

# Instructions for testing with Claude
echo ""
echo "To test the resources with Claude, you would use the access_mcp_resource tool like this:"
echo ""
echo "1. List all indices:"
echo "   <access_mcp_resource>"
echo "   <server_name>elasticsearch-mcp-server</server_name>"
echo "   <uri>elasticsearch://indices</uri>"
echo "   </access_mcp_resource>"
echo ""
echo "2. Get information about a specific index (replace 'your_index_name'):"
echo "   <access_mcp_resource>"
echo "   <server_name>elasticsearch-mcp-server</server_name>"
echo "   <uri>elasticsearch://index/your_index_name</uri>"
echo "   </access_mcp_resource>"
echo ""
echo "3. Get mapping for a specific index (replace 'your_index_name'):"
echo "   <access_mcp_resource>"
echo "   <server_name>elasticsearch-mcp-server</server_name>"
echo "   <uri>elasticsearch://mapping/your_index_name</uri>"
echo "   </access_mcp_resource>"
echo ""

# Keep the script running to maintain the server
echo "The MCP server is running. Press Ctrl+C to stop the server and exit."
echo ""

# Wait for user to press Ctrl+C
while true; do
    sleep 1
done
