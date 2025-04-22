# Elasticsearch MCP Server

This project implements an MCP (Model Context Protocol) server for Elasticsearch, providing tools and resources to interact with Elasticsearch clusters.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

### Tools
- `list_indices`: Lists all indices in the Elasticsearch cluster
- `get_mappings`: Gets the mappings for a specific index
- `search`: Performs an Elasticsearch search with a provided query DSL
- `search_with_query_string`: Performs a search with a simple query string
- `get_index_stats`: Gets statistics for a specific index

### Resources
- `elasticsearch://indices`: Lists all Elasticsearch indices
- `elasticsearch://index/{index_name}`: Gets detailed information about a specific index
- `elasticsearch://mapping/{index_name}`: Gets mapping information for a specific index

## Prerequisites

- Python 3.7+
- Elasticsearch Python client
- MCP SDK
- Elasticsearch cluster credentials (Cloud ID and API Key)

## Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/elasticsearch-mcp-server.git
   cd elasticsearch-mcp-server
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Copy the example environment file: `cp .env.example .env`
   - Edit the `.env` file and add your Elasticsearch credentials
   
   Or set them directly in your shell:
   ```
   export ES_CLOUD_ID=your_elasticsearch_cloud_id
   export ES_API_KEY=your_elasticsearch_api_key
   ```

## Testing the MCP Resources

### Option 1: Using the Test Script

We've provided a test script that starts the MCP server and provides instructions for testing:

```bash
# Make the script executable if needed
chmod +x test_es_mcp.sh

# Run the test script
ES_CLOUD_ID=your_cloud_id ES_API_KEY=your_api_key ./test_es_mcp.sh
```

The script will:
1. Start the MCP server in the background
2. Provide instructions for testing the resources
3. Keep the server running until you press Ctrl+C

### Option 2: Manual Testing

1. Start the MCP server:
   ```bash
   ES_CLOUD_ID=your_cloud_id ES_API_KEY=your_api_key python es_mcp_server.py
   ```

2. In Claude, use the `access_mcp_resource` tool to access the resources:

   a. List all indices:
   ```
   <access_mcp_resource>
   <server_name>elasticsearch-mcp-server</server_name>
   <uri>elasticsearch://indices</uri>
   </access_mcp_resource>
   ```

   b. Get information about a specific index:
   ```
   <access_mcp_resource>
   <server_name>elasticsearch-mcp-server</server_name>
   <uri>elasticsearch://index/your_index_name</uri>
   </access_mcp_resource>
   ```

   c. Get mapping for a specific index:
   ```
   <access_mcp_resource>
   <server_name>elasticsearch-mcp-server</server_name>
   <uri>elasticsearch://mapping/your_index_name</uri>
   </access_mcp_resource>
   ```

### Option 3: Using the Python Test Script

We've also provided a Python test script that demonstrates how to access the resources:

```bash
ES_CLOUD_ID=your_cloud_id ES_API_KEY=your_api_key python test_es_resources.py
```

## Resource Details

### `elasticsearch://indices`

Returns a JSON array of all indices in the Elasticsearch cluster, including:
- Index name
- Health status
- Status
- Document count
- Size

### `elasticsearch://index/{index_name}`

Returns detailed information about a specific index, including:
- Index name
- Settings
- Statistics (document count, size in bytes and MB)

### `elasticsearch://mapping/{index_name}`

Returns mapping information for a specific index, including:
- Complete mapping definition
- Field count
- Field type distribution

## Error Handling

All resources include proper error handling and validation:
- If an index doesn't exist, the resource will return an appropriate error message
- If there's an issue connecting to Elasticsearch, the resource will return an error message
- All exceptions are caught and returned as readable error messages

## Contributing

Contributions are welcome! Here's how you can contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Submit a pull request

## GitHub Repository

This project is ready to be uploaded to GitHub. The repository includes:

- `.gitignore` file to exclude sensitive information and logs
- `.env.example` file to guide users on setting up their environment variables
- `requirements.txt` file to list dependencies
- `LICENSE` file with the MIT License
- Comprehensive documentation in the README.md

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
