#!/usr/bin/env python3
"""
Script to check the available methods of the FastMCP class.
"""
from mcp.server.fastmcp import FastMCP
import inspect

# Create a FastMCP instance
mcp = FastMCP("test-server")

# Print all methods of the FastMCP class
print("Available methods of FastMCP:")
for name, method in inspect.getmembers(mcp, predicate=inspect.ismethod):
    if not name.startswith('_'):  # Skip private methods
        print(f"- {name}")

# Print all attributes of the FastMCP class
print("\nAvailable attributes of FastMCP:")
for name, attr in inspect.getmembers(mcp):
    if not name.startswith('_') and not inspect.ismethod(attr):  # Skip private attributes and methods
        print(f"- {name}")

# Check if there's a method for defining resources
resource_methods = [name for name, method in inspect.getmembers(mcp, predicate=inspect.ismethod) 
                   if 'resource' in name.lower()]
print("\nMethods related to resources:")
for method in resource_methods:
    print(f"- {method}")
    # Try to get the method's signature
    try:
        method_obj = getattr(mcp, method)
        signature = inspect.signature(method_obj)
        print(f"  Signature: {signature}")
    except Exception as e:
        print(f"  Error getting signature: {e}")
