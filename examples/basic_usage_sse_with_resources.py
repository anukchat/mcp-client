#!/usr/bin/env python3
# examples/basic_usage_sse_with_resources.py

"""
Resource Demonstration Example for MCP Client with SSE transport

This example demonstrates working with MCP resources:
1. Listing available resources and templates
2. Reading resource content
3. Subscribing to resource updates
4. Using resource templates

** Make sure math_server_sse.py is running before running this example:
   python servers/math_server_sse.py

NOTE: This example uses async/await as the official MCP library is async-only.
"""

import os
import asyncio
import logging
import json
import time
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

async def demonstrate_resources():
    """Demonstrate working with resources."""
    logger.info("\n=== MCP Resources Demo with SSE ===\n")
    try:
        # Create a client with direct initialization
        client = MCPClient(
            base_url="http://localhost:8000/sse",
            transport="sse",
            timeout=30
        )
        
        async with client as mcp:
            # Step 1: List available resources and templates
            resources_result = await mcp.list_resources()
            logger.info(f"Found {len(resources_result.resources)} resources and {len(resources_result.templates or [])} templates")
            
            # Display available resources
            for resource in resources_result.resources:
                logger.info(f"Resource: {resource.name} (URI: {resource.uri})")
            
            # Display available templates
            if resources_result.templates and len(resources_result.templates) > 0:
                logger.info("Available templates:")
                for template in resources_result.templates:
                    logger.info(f"Template: {template.name} (URI Template: {template.uri_template})")
            else:
                logger.info("No resource templates available from this server")
            
            # Step 2: Call some tools to generate data for resources
            logger.info("\n--- Making calculations to update resources ---")
            await mcp.call_tool("add", {"a": 10, "b": 20})
            logger.info("Called add(10, 20)")
            
            await mcp.call_tool("multiply", {"a": 5, "b": 6})
            logger.info("Called multiply(5, 6)")
            
            # Step 3: Read resource content
            logger.info("\n--- Reading resources ---")
            try:
                # Read calculation history
                history = await mcp.read_resource("calc://history")
                for item in history.contents:
                    if item.text:
                        logger.info(f"Calculation history:\n{item.text}")
                
                # Read current result
                current = await mcp.read_resource("calc://current")
                for item in current.contents:
                    if item.text:
                        logger.info(f"Current calculation result: {item.text}")
            except Exception as e:
                logger.error(f"Error reading resources: {e}")
            
            # Step 4: Subscribe to resources for updates
            logger.info("\n--- Subscribing to resources for updates ---")
            try:
                # Check if subscription is supported
                if hasattr(mcp._mcpwire, 'subscribe_to_resource'):
                    # Subscribe to current calculation updates
                    await mcp.subscribe_to_resource("calc://current")
                    logger.info("Subscribed to current calculation updates")
                    
                    # Make another calculation to trigger the resource update
                    logger.info("Making another calculation to trigger resource update...")
                    await mcp.call_tool("multiply", {"a": 10, "b": 10})
                    logger.info("Called multiply(10, 10)")
                    
                    # Read the updated resource
                    updated = await mcp.read_resource("calc://current")
                    for item in updated.contents:
                        if item.text:
                            logger.info(f"Updated calculation result: {item.text}")
                    
                    # Read history again to see all calculations
                    history = await mcp.read_resource("calc://history")
                    for item in history.contents:
                        if item.text:
                            logger.info(f"Updated calculation history:\n{item.text}")
                            
                    # Unsubscribe when done
                    await mcp.unsubscribe_from_resource("calc://current")
                    logger.info("Unsubscribed from current calculation updates")
                else:
                    logger.warning("Resource subscription not supported by this MCP implementation")
                    
                    # Still make the calculation and read resources
                    logger.info("Making another calculation...")
                    await mcp.call_tool("multiply", {"a": 10, "b": 10})
                    logger.info("Called multiply(10, 10)")
                    
                    # Read the updated resource
                    updated = await mcp.read_resource("calc://current")
                    for item in updated.contents:
                        if item.text:
                            logger.info(f"Updated calculation result: {item.text}")
                    
                    # Read history again to see all calculations
                    history = await mcp.read_resource("calc://history")
                    for item in history.contents:
                        if item.text:
                            logger.info(f"Updated calculation history:\n{item.text}")
            except Exception as e:
                logger.error(f"Error with resource subscription: {e}")
            
            # Step 5: Use a resource template
            logger.info("\n--- Using resource templates ---")
            try:
                # Use the timestamp template
                current_timestamp = int(time.time())
                timestamp_uri = f"calc://timestamp/{current_timestamp}"
                logger.info(f"Using template with URI: {timestamp_uri}")
                
                timestamp_data = await mcp.read_resource(timestamp_uri)
                for item in timestamp_data.contents:
                    if item.text:
                        # Parse JSON response
                        data = json.loads(item.text)
                        logger.info(f"Template data: {data}")
            except Exception as e:
                logger.error(f"Error using template: {e}")
            
    except MCPConnectionError as e:
        logger.error(f"Connection error: {e}")
        logger.info("Make sure math_server_sse.py is running at http://localhost:8000")
    except MCPError as e:
        logger.error(f"MCP Client error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

if __name__ == "__main__":
    # Run the async example
    asyncio.run(demonstrate_resources()) 