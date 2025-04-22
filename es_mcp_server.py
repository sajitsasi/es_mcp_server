from typing import Any, Dict, List, Optional
import json
import os
import sys
from elasticsearch import Elasticsearch
from mcp.server.fastmcp import FastMCP, Context
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from dataclasses import dataclass
import logging

logger = logging.getLogger("elasticsearch-mcp-server")
logging.basicConfig(level=logging.INFO)


@dataclass 
class ElasticsearchContext:
    client: Elasticsearch

@asynccontextmanager
async def elasticsearch_lifespan(server: FastMCP) -> AsyncIterator[ElasticsearchContext]:
    es_cloud_id = os.environ.get("ES_CLOUD_ID", "")
    es_api_key = os.environ.get("ES_API_KEY", "")

    if not es_cloud_id or not es_api_key:
        raise ValueError("ES_CLOUD_ID and ES_API_KEY environment variables are required")
    
    es_client = Elasticsearch(
        cloud_id=es_cloud_id,
        api_key=es_api_key
    )
    logger.info("Connected to Elasticsearch")

    try:
        if not es_client.ping():
            raise ConnectionError("Elasticsearch cluster is not reachable")
        
        yield ElasticsearchContext(client=es_client)
    finally:
        await es_client.close()
        logger.info("Elasticsearch client closed")


# Initialize FastMCP server
mcp = FastMCP("elasticsearch-mcp-server", lifespan=elasticsearch_lifespan)

@mcp.tool()
async def list_indices(ctx: Context) -> str:
    try:
        es = ctx.request_context.lifespan_context.client
        indices = es.cat.indices(format="json")
        
        indices_info = [
            {
                "index": index.get("index"),
                "health": index.get("health"),
                "status": index.get("status"),
                "docsCount": index.get("docs.count")
            }
            for index in indices
        ]
        
        return f"Found {len(indices_info)} indices\n\n{json.dumps(indices_info, indent=2)}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def get_mappings(index: str, ctx: Context) -> str:
    try:
        es = ctx.request_context.lifespan_context.client
        mapping_response = es.indices.get_mapping(index=index)
        
        mappings = mapping_response.get(index, {}).get('mappings', {})
        
        return f"Mappings for index: {index}\n\n{json.dumps(mappings, indent=2)}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
async def search(ctx: Context, index: str, query_body: Dict[str, Any]) -> str:
    """Perform an Elasticsearch search with the provided query DSL. Highlights are always enabled.
    
    Args:
        index: Name of the Elasticsearch index to search
        query_body: Complete Elasticsearch query DSL object that can include query, size, from, sort, etc.
    """
    try:
        # Get mappings to identify text fields for highlighting
        es = ctx.request_context.lifespan_context.client
        mapping_response = es.indices.get_mapping(index=index)
        index_mappings = mapping_response.get(index, {}).get('mappings', {})
        
        search_request = {
            "index": index,
            **query_body
        }
        
        # Always do highlighting if there are text fields
        if 'properties' in index_mappings:
            text_fields = {}
            
            # Find all text fields for highlighting
            for field_name, field_data in index_mappings['properties'].items():
                if field_data.get('type') == 'text' or 'dense_vector' in field_data:
                    text_fields[field_name] = {}
            
            if text_fields:
                search_request["highlight"] = {
                    "fields": text_fields,
                    "pre_tags": ["<em>"],
                    "post_tags": ["</em>"]
                }
        
        result = es.search(**search_request)
        
        # Extract the 'from' parameter from query_body, defaulting to 0 if not provided
        from_value = query_body.get('from', 0)
        
        # Begin building the response
        total_hits = result['hits']['total']['value'] if isinstance(result['hits']['total'], dict) else result['hits']['total']
        response = [f"Total results: {total_hits}, showing {len(result['hits']['hits'])} from position {from_value}"]
        
        # Format each hit
        for hit in result['hits']['hits']:
            highlighted_fields = hit.get('highlight', {})
            source_data = hit.get('_source', {})
            
            hit_text = []
            
            # Add highlighted fields
            for field, highlights in highlighted_fields.items():
                if highlights and len(highlights) > 0:
                    hit_text.append(f"{field} (highlighted): {' ... '.join(highlights)}")
            
            # Add source fields that weren't highlighted
            for field, value in source_data.items():
                if field not in highlighted_fields:
                    hit_text.append(f"{field}: {json.dumps(value)}")
            
            response.append("\n".join(hit_text))
        
        return "\n\n---\n\n".join(response)
    except Exception as e:
        return f"Error: {str(e)}"

# Add a tool to perform a search with simple query syntax
@mcp.tool()
async def search_with_query_string(
    index_name: str, 
    query_text: str, 
    fields: str = "_source", 
    size: int = 10, 
    from_: int = 0,
    ctx: Context = None
) -> str:
    """
    Search an index with a simple query string and pagination.
    
    Args:
        index_name: The name of the index to search
        query_text: Free text search query
        fields: Comma-separated list of fields to return (default: all)
        size: Number of results to return (default: 10)
        from_: Starting offset for pagination (default: 0)
    """
    try:
        es = ctx.request_context.lifespan_context.client
        query = {
            "query": {
                "query_string": {
                    "query": query_text
                }
            },
            "size": size,
            "from": from_
        }
        
        # Handle fields parameter
        if fields and fields != "_source":
            query["_source"] = fields.split(",")
            
        results = es.search(index=index_name, body=query)  # No await needed
        
        # Format the results in a readable way
        hits = results["hits"]["hits"]
        total = results["hits"]["total"]["value"]
        
        formatted = f"Found {total} documents. Showing {from_ + 1}-{min(from_ + size, total)}:\n\n"
        
        for i, hit in enumerate(hits, 1):
            formatted += f"Result {from_ + i}. Score: {hit['_score']}\n"
            formatted += f"ID: {hit['_id']}\n"
            formatted += "Content:\n"
            formatted += json.dumps(hit["_source"], indent=2) + "\n\n"
            
        return formatted
    except Exception as e:
        return f"Error searching index {index_name}: {str(e)}"

# Add a tool to get index statistics  
@mcp.tool()
async def get_index_stats(index_name: str, ctx: Context) -> str:
    """
    Get statistics for a specific index.
    
    Args:
        index_name: The name of the index to get statistics for
    """
    try:
        es = ctx.request_context.lifespan_context.client
        stats = es.indices.stats(index=index_name)  # No await needed
        
        # Format the stats for readability
        formatted = f"Statistics for index: {index_name}\n\n"
        formatted += f"Documents: {stats['_all']['primaries']['docs']['count']}\n"
        formatted += f"Size: {stats['_all']['primaries']['store']['size_in_bytes'] / 1024 / 1024:.2f} MB\n"
        formatted += f"Indexing operations: {stats['_all']['primaries']['indexing']['index_total']}\n"
        formatted += f"Search operations: {stats['_all']['primaries']['search']['query_total']}\n"
        
        return formatted
    except Exception as e:
        return f"Error getting stats for index {index_name}: {str(e)}"


#TODO: Add mcp.resources for other operations like creating, deleting, and updating indices

# Add resources for index and mapping information
@mcp.resource("elasticsearch://index/{index_name}", name="Elasticsearch Index Information", description="Get information about a specific Elasticsearch index")
async def get_index_resource(index_name: str) -> str:
    """
    Resource to get information about a specific Elasticsearch index.
    
    Args:
        index_name: The name of the index to get information for
    """
    ctx = mcp.get_context()
    try:
        es = ctx.request_context.lifespan_context.client
        
        # Check if index exists
        if not es.indices.exists(index=index_name):
            return f"Index '{index_name}' does not exist"
        
        # Get index information
        index_info = es.indices.get(index=index_name)
        stats = es.indices.stats(index=index_name)
        
        # Combine information
        result = {
            "name": index_name,
            "settings": index_info.get(index_name, {}).get("settings", {}),
            "stats": {
                "docs_count": stats['_all']['primaries']['docs']['count'],
                "size_bytes": stats['_all']['primaries']['store']['size_in_bytes'],
                "size_mb": round(stats['_all']['primaries']['store']['size_in_bytes'] / 1024 / 1024, 2)
            }
        }
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error retrieving index information: {str(e)}"

@mcp.resource("elasticsearch://mapping/{index_name}", name="Elasticsearch Mapping Information", description="Get mapping information for a specific Elasticsearch index")
async def get_mapping_resource(index_name: str) -> str:
    """
    Resource to get mapping information for a specific Elasticsearch index.
    
    Args:
        index_name: The name of the index to get mapping information for
    """
    ctx = mcp.get_context()
    try:
        es = ctx.request_context.lifespan_context.client
        
        # Check if index exists
        if not es.indices.exists(index=index_name):
            return f"Index '{index_name}' does not exist"
        
        # Get mapping information
        mapping_response = es.indices.get_mapping(index=index_name)
        mappings = mapping_response.get(index_name, {}).get('mappings', {})
        
        # Add some additional metadata
        result = {
            "index": index_name,
            "mappings": mappings,
            "field_count": len(mappings.get("properties", {})) if "properties" in mappings else 0,
            "field_types": {}
        }
        
        # Count field types
        if "properties" in mappings:
            for field_name, field_data in mappings["properties"].items():
                field_type = field_data.get("type", "unknown")
                if field_type in result["field_types"]:
                    result["field_types"][field_type] += 1
                else:
                    result["field_types"][field_type] = 1
        
        return json.dumps(result, indent=2)
    except Exception as e:
        return f"Error retrieving mapping information: {str(e)}"

@mcp.resource("elasticsearch://indices", name="Elasticsearch Indices List", description="List all Elasticsearch indices")
async def list_indices_resource() -> str:
    """
    Resource to list all Elasticsearch indices.
    """
    ctx = mcp.get_context()
    try:
        es = ctx.request_context.lifespan_context.client
        indices = es.cat.indices(format="json")
        
        indices_info = [
            {
                "index": index.get("index"),
                "health": index.get("health"),
                "status": index.get("status"),
                "docs_count": index.get("docs.count"),
                "size": index.get("store.size")
            }
            for index in indices
        ]
        
        return json.dumps(indices_info, indent=2)
    except Exception as e:
        return f"Error listing indices: {str(e)}"

if __name__ == "__main__":
    # Run the server
    mcp.run(transport="stdio")
