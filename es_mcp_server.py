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
import math
from dotenv import load_dotenv

logger = logging.getLogger("elasticsearch-mcp-server")
logging.basicConfig(level=logging.INFO)


@dataclass
class ElasticsearchContext:
    client: Elasticsearch

@asynccontextmanager
async def elasticsearch_lifespan(server: FastMCP) -> AsyncIterator[ElasticsearchContext]:
    # Check for MCP_SERVER_CWD and load .env file from there if it exists
    mcp_server_cwd = os.environ.get("MCP_SERVER_CWD")
    if mcp_server_cwd:
        custom_env_path = os.path.join(mcp_server_cwd, '.env')
        if os.path.exists(custom_env_path):
            logger.info(f"Found .env file at {custom_env_path}, loading variables.")
            load_dotenv(dotenv_path=custom_env_path, override=True)
        else:
            logger.info(f".env file not found at {custom_env_path}. Using pre-existing environment variables.")
    else:
        # Optionally, you could still load a .env file from the default location (current working directory)
        # if MCP_SERVER_CWD is not set, but the request was specific to MCP_SERVER_CWD.
        # load_dotenv(override=True) # This would load .env from CWD if present
        logger.info("MCP_SERVER_CWD not set. Using pre-existing environment variables or default .env location.")

    es_cloud_id = os.environ.get("ES_CLOUD_ID", "")
    es_api_key = os.environ.get("ES_API_KEY", "")

    if not es_cloud_id or not es_api_key:
        logger.error("ES_CLOUD_ID and ES_API_KEY environment variables are required but not found.")
        raise ValueError("ES_CLOUD_ID and ES_API_KEY environment variables are required but not found.")
    
    es_client = Elasticsearch(
        cloud_id=es_cloud_id,
        api_key=es_api_key
    )
    logger.info("Attempting to connect to Elasticsearch...")

    try:
        if not es_client.ping():
            logger.error("Elasticsearch cluster is not reachable.")
            raise ConnectionError("Elasticsearch cluster is not reachable")
        logger.info("Successfully connected to Elasticsearch.")
        yield ElasticsearchContext(client=es_client)
    finally:
        await es_client.close()
        logger.info("Elasticsearch client closed.")


# Initialize FastMCP server
mcp = FastMCP("elasticsearch-mcp-server", lifespan=elasticsearch_lifespan)

# --- Tools remain the same ---
@mcp.tool()
async def list_indices(ctx: Context, page: Optional[int] = 1, page_size: Optional[int] = 10) -> str:
    try:
        current_page_size = page_size if page_size is not None and page_size > 0 else 10
        current_page = page if page is not None and page > 0 else 1

        es = ctx.request_context.lifespan_context.client
        all_indices = es.cat.indices(format="json", h="index,health,status,docs.count,store.size", s="index:asc") 
        
        if not all_indices:
            return "No indices found."

        total_indices = len(all_indices)
        total_pages = math.ceil(total_indices / current_page_size)
        current_page = max(1, min(current_page, total_pages if total_pages > 0 else 1))
        
        start_index = (current_page - 1) * current_page_size
        end_index = start_index + current_page_size
        paginated_indices = all_indices[start_index:end_index]

        indices_info = [
            {
                "index": index.get("index"),
                "health": index.get("health"),
                "status": index.get("status"),
                "docs_count": index.get("docs.count"),
                "size": index.get("store.size")
            }
            for index in paginated_indices
        ]
        response_data = {
            "total_indices": total_indices,
            "current_page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "indices_on_page": len(indices_info),
            "indices": indices_info
        }
        return f"Showing page {current_page} of {total_pages} ({len(indices_info)} of {total_indices} total indices)\n\n{json.dumps(response_data, indent=2)}"
    except Exception as e:
        logger.error(f"Error in list_indices tool: {str(e)}", exc_info=True)
        return f"Error listing indices: {str(e)}"

@mcp.tool()
async def get_mappings(index: str, ctx: Context) -> str: 
    try:
        es = ctx.request_context.lifespan_context.client
        mapping_response = es.indices.get_mapping(index=index)
        mappings = mapping_response.get(index, {}).get('mappings', {})
        return f"Mappings for index: {index}\n\n{json.dumps(mappings, indent=2)}"
    except Exception as e:
        logger.error(f"Error in get_mappings tool for index {index}: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"

@mcp.tool()
async def search(ctx: Context, index: str, query_body: Dict[str, Any]) -> str: 
    try:
        es = ctx.request_context.lifespan_context.client
        mapping_response = es.indices.get_mapping(index=index) 
        index_mappings = mapping_response.get(index, {}).get('mappings', {})
        search_request = {"index": index, **query_body}
        if 'properties' in index_mappings: 
            text_fields = {}
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
        from_value = query_body.get('from', 0) 
        total_hits = result['hits']['total']['value'] if isinstance(result['hits']['total'], dict) else result['hits']['total'] 
        response = [f"Total results: {total_hits}, showing {len(result['hits']['hits'])} from position {from_value}"]
        for hit in result['hits']['hits']: 
            highlighted_fields = hit.get('highlight', {}) 
            source_data = hit.get('_source', {}) 
            hit_text = []
            for field, highlights in highlighted_fields.items():
                if highlights and len(highlights) > 0:
                    hit_text.append(f"{field} (highlighted): {' ... '.join(highlights)}") 
            for field, value in source_data.items():
                if field not in highlighted_fields:
                    hit_text.append(f"{field}: {json.dumps(value)}") 
            response.append("\n".join(hit_text))
        return "\n\n---\n\n".join(response)
    except Exception as e:
        logger.error(f"Error in search tool for index {index}: {str(e)}", exc_info=True)
        return f"Error: {str(e)}"

@mcp.tool()
async def search_with_query_string( 
    index_name: str, 
    query_text: str, 
    fields: str = "_source", 
    size: int = 10, 
    from_: int = 0,
    ctx: Context = None 
) -> str:
    try:
        es = ctx.request_context.lifespan_context.client
        query = {
            "query": {"query_string": {"query": query_text}}, 
            "size": size, 
            "from": from_ 
        }
        if fields and fields != "_source": 
            query["_source"] = fields.split(",")
        results = es.search(index=index_name, body=query) 
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
        logger.error(f"Error in search_with_query_string for index {index_name}: {str(e)}", exc_info=True)
        return f"Error searching index {index_name}: {str(e)}"

@mcp.tool()
async def get_index_stats(index_name: str, ctx: Context) -> str: 
    try:
        es = ctx.request_context.lifespan_context.client
        stats = es.indices.stats(index=index_name) 
        formatted = f"Statistics for index: {index_name}\n\n"
        formatted += f"Documents: {stats['_all']['primaries']['docs']['count']}\n" 
        formatted += f"Size: {stats['_all']['primaries']['store']['size_in_bytes'] / 1024 / 1024:.2f} MB\n" 
        formatted += f"Indexing operations: {stats['_all']['primaries']['indexing']['index_total']}\n" 
        formatted += f"Search operations: {stats['_all']['primaries']['search']['query_total']}\n" 
        return formatted
    except Exception as e:
        logger.error(f"Error in get_index_stats for index {index_name}: {str(e)}", exc_info=True)
        return f"Error getting stats for index {index_name}: {str(e)}"

# --- Resources ---
@mcp.resource("elasticsearch://index/{index_name}", name="Elasticsearch Index Information", description="Get information about a specific Elasticsearch index")
async def get_index_resource(index_name: str) -> str: 
    ctx = mcp.get_context() 
    try:
        if not hasattr(ctx, 'request_context') or not hasattr(ctx.request_context, 'lifespan_context'):
            logger.error("Context is not properly initialized in get_index_resource.")
            return json.dumps({"error": "Internal server error: Context not initialized"}, indent=2)
        es = ctx.request_context.lifespan_context.client
        if not es.indices.exists(index=index_name): 
            return f"Index '{index_name}' does not exist"
        index_info = es.indices.get(index=index_name) 
        stats = es.indices.stats(index=index_name) 
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
        logger.error(f"Error in get_index_resource for index {index_name}: {str(e)}", exc_info=True)
        return json.dumps({"error": f"Error retrieving index information: {str(e)}"}, indent=2)

@mcp.resource("elasticsearch://mapping/{index_name}", name="Elasticsearch Mapping Information", description="Get mapping information for a specific Elasticsearch index")
async def get_mapping_resource(index_name: str) -> str: 
    ctx = mcp.get_context() 
    try:
        if not hasattr(ctx, 'request_context') or not hasattr(ctx.request_context, 'lifespan_context'):
            logger.error("Context is not properly initialized in get_mapping_resource.")
            return json.dumps({"error": "Internal server error: Context not initialized"}, indent=2)
        es = ctx.request_context.lifespan_context.client
        if not es.indices.exists(index=index_name): 
            return f"Index '{index_name}' does not exist"
        mapping_response = es.indices.get_mapping(index=index_name) 
        mappings = mapping_response.get(index_name, {}).get('mappings', {}) 
        result = {
            "index": index_name,
            "mappings": mappings, 
            "field_count": len(mappings.get("properties", {})) if "properties" in mappings else 0, 
            "field_types": {} 
        }
        if "properties" in mappings: 
            for field_name, field_data in mappings["properties"].items():
                field_type = field_data.get("type", "unknown") 
                result["field_types"][field_type] = result["field_types"].get(field_type, 0) + 1
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error in get_mapping_resource for index {index_name}: {str(e)}", exc_info=True)
        return json.dumps({"error": f"Error retrieving mapping information: {str(e)}"}, indent=2)

@mcp.resource("elasticsearch://indices", name="Elasticsearch Indices List", description="List all Elasticsearch indices with pagination")
async def list_indices_resource() -> str: 
    ctx = mcp.get_context() 
    page = 1
    page_size = 10
    try:
        if not hasattr(ctx, 'request_context') or \
           not hasattr(ctx.request_context, 'lifespan_context') or \
           not hasattr(ctx.request_context.lifespan_context, 'client'):
            logger.error("Context or Elasticsearch client is not properly initialized in list_indices_resource.")
            return json.dumps({"error": "Internal server error: Context or ES client not initialized"}, indent=2)

        params_source = None
        if hasattr(ctx.request_context, 'tool_input') and isinstance(ctx.request_context.tool_input, dict):
            params_source = ctx.request_context.tool_input
        
        if params_source:
            raw_page = params_source.get('page')
            raw_page_size = params_source.get('page_size')
            if raw_page is not None:
                try: page = int(raw_page)
                except (ValueError, TypeError): logger.warning(f"Invalid 'page' parameter value: {raw_page}. Using default: {page}")
            if raw_page_size is not None:
                try: page_size = int(raw_page_size)
                except (ValueError, TypeError): logger.warning(f"Invalid 'page_size' parameter value: {raw_page_size}. Using default: {page_size}")
        
        if page_size <= 0:
            logger.warning(f"Non-positive 'page_size' parameter value {page_size} received. Resetting to default 10.")
            page_size = 10
        if page <= 0:
            logger.warning(f"Non-positive 'page' parameter value {page} received. Resetting to default 1.")
            page = 1
            
        es = ctx.request_context.lifespan_context.client
        all_indices = es.cat.indices(format="json", h="index,health,status,docs.count,store.size", s="index:asc") 

        if not all_indices:
            return json.dumps({
                "total_indices": 0, "current_page": page, "page_size": page_size,
                "total_pages": 0, "indices_on_page": 0, "indices": []
            }, indent=2)

        total_indices = len(all_indices)
        total_pages = math.ceil(total_indices / page_size)
        current_page = max(1, min(page, total_pages if total_pages > 0 else 1))
        start_index = (current_page - 1) * page_size
        end_index = start_index + page_size
        paginated_indices = all_indices[start_index:end_index]
        
        indices_info = [
            {"index": index.get("index"), "health": index.get("health"), "status": index.get("status"),
             "docs_count": index.get("docs.count"), "size": index.get("store.size")}
            for index in paginated_indices
        ]
        response_data = {
            "total_indices": total_indices, "current_page": current_page, "page_size": page_size,
            "total_pages": total_pages, "indices_on_page": len(indices_info), "indices": indices_info
        }
        return json.dumps(response_data, indent=2)
    except Exception as e:
        logger.error(f"Error in list_indices_resource: {str(e)}", exc_info=True) 
        return json.dumps({"error": f"Error listing indices: {str(e)}"}, indent=2)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the Elasticsearch MCP server")
    parser.add_argument(
        "--transport",
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="Transport to use for FastMCP (e.g. 'stdio' or 'sse')",
    )
    args = parser.parse_args()

    mcp.run(transport=args.transport)
