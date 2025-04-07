#!/usr/bin/env python3
# examples/basic_usage_sse.py

"""
Basic Usage Example for MCP Client with SSE transport

This example demonstrates:
1. Creating a client directly or loading from configuration file
2. Using the client to interact with an SSE-based MCP server
3. Working with MCP resources (listing, reading, subscribing)

** Make sure your math_server_sse.py is running before running this example:
   python servers/math_server_sse.py

NOTE: This example uses async/await as the official MCP library is async-only.
"""

import os
import asyncio
import logging
import base64
from typing import Dict, Any, Optional

from mcpwire import (
    MCPClient,
    MCPError,
    MCPAPIError,
    MCPConnectionError,
    MCPTimeoutError
)

# Set up logging - helps trace what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def example_direct_initialization():
    """Example: Creating a client directly."""
    logger.info("\n=== Example: Direct Initialization with SSE ===\n")
    try:
        # Create a client with direct initialization
        client = MCPClient(
            base_url="http://localhost:8000/sse",
            transport="sse",
            timeout=30,
            api_key=None  # Optional API key
        )
        
        async with client as mcp:
            # List available tools
            tools = await mcp.list_tools()
            logger.info(f"Server provides {len(tools)} tools")
            for tool in tools:
                logger.info(f"Tool: {tool.name} - {tool.description}")
            
            # Call the add tool from math_server_sse.py
            try:
                result = await mcp.call_tool("add", {"a": 5, "b": 7})
                logger.info(f"Result of add(5, 7): {result}")
            except Exception as e:
                logger.error(f"Error calling 'add' tool: {e}")
            
            # Call the multiply tool from math_server_sse.py
            try:
                result = await mcp.call_tool("multiply", {"a": 6, "b": 8})
                logger.info(f"Result of multiply(6, 8): {result}")
            except Exception as e:
                logger.error(f"Error calling 'multiply' tool: {e}")
    
    except MCPConnectionError as e:
        logger.error(f"Connection error: {e}")
        logger.info("Make sure math_server_sse.py is running at http://localhost:8000")
    except MCPError as e:
        logger.error(f"MCP Client error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

async def example_config_file_initialization():
    """Example: Loading client config from mcp.json."""
    logger.info("\n=== Example: Config File Initialization with SSE ===\n")
    try:
        # Load configuration from mcp.json file
        client = MCPClient.from_config(server_name="math_sse")
        
        async with client as mcp:
            # Get server metadata
            try:
                metadata = await mcp.get_server_metadata()
                logger.info(f"Connected to server from config: {metadata.name} v{metadata.version}")
            except Exception as e:
                logger.error(f"Error getting server metadata: {e}")
                logger.info("Continuing with tool listing...")
            
            # List available tools
            tools = await mcp.list_tools()
            logger.info(f"Server provides {len(tools)} tools")
            
            # Call tools
            for tool in tools:
                logger.info(f"Found tool: {tool.name} - {tool.description}")
                
            # Try to call some tools
            try:
                result = await mcp.call_tool("add", {"a": 10, "b": 20})
                logger.info(f"Result of add(10, 20): {result}")
            except Exception as e:
                logger.error(f"Error calling 'add' tool: {e}")
            
    except FileNotFoundError:
        logger.error("mcp.json file not found in standard locations.")
        logger.info("Create an mcp.json file in the current directory or ~/.mcp.json")
    except KeyError as e:
        logger.error(f"Server configuration not found: {e}")
    except MCPError as e:
        logger.error(f"MCP Client error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

async def run_all_examples():
    """Run all examples in sequence."""
    try:
        await example_direct_initialization()
        await example_config_file_initialization()
    except Exception as e:
        logger.error(f"Error running examples: {e}", exc_info=True)

if __name__ == "__main__":
    # Run the async examples
    asyncio.run(run_all_examples())

