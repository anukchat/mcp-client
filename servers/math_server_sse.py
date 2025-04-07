#!/usr/bin/env python3
# servers/math_server_sse.py
"""
Math Server Example using SSE transport with resource support

This demonstrates a simple MCP server using the FastMCP class
with SSE (Server-Sent Events) transport and resource support.

Run this server with:
    python servers/math_server_sse.py
"""
import json
import time
from mcp.server import FastMCP
from mcp import Resource

# Create an MCP server with a name
mcp = FastMCP("MathSSE")

# Track calculation history and current result
calculation_history = []
current_result = None

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    result = a + b
    calculation_history.append(f"{a} + {b} = {result}")
    global current_result
    current_result = result
    
    # Update resources after calculation
    mcp.add_resource(Resource(
        uri="calc://current",
        name="Current Calculation",
        description="The result of the most recent calculation",
        text=str(current_result),
        mimeType="text/plain"
    ))
    
    mcp.add_resource(Resource(
        uri="calc://history",
        name="Calculation History",
        description="History of all calculations performed",
        text="\n".join(calculation_history),
        mimeType="text/plain"
    ))
    
    return result

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    result = a * b
    calculation_history.append(f"{a} * {b} = {result}")
    global current_result
    current_result = result
    
    # Update resources after calculation
    mcp.add_resource(Resource(
        uri="calc://current",
        name="Current Calculation",
        description="The result of the most recent calculation",
        text=str(current_result),
        mimeType="text/plain"
    ))
    
    mcp.add_resource(Resource(
        uri="calc://history",
        name="Calculation History",
        description="History of all calculations performed",
        text="\n".join(calculation_history),
        mimeType="text/plain"
    ))
    
    return result

# Register resource handlers directly using the function decorator approach
@mcp.resource("calc://history")
def get_history():
    """Resource handler for calculation history"""
    return "\n".join(calculation_history) if calculation_history else "No calculations yet"

@mcp.resource("calc://current")
def get_current_result():
    """Resource handler for current result"""
    return str(current_result) if current_result is not None else "No result yet"

@mcp.resource("calc://timestamp/{time}")
def get_timestamp_data(time):
    """Resource handler for timestamp data"""
    try:
        timestamp = int(time)
        return json.dumps({
            "timestamp": timestamp,
            "server_time": int(time),
            "message": f"Server received request for timestamp {timestamp}"
        })
    except (ValueError, TypeError):
        return None

# Initialize resources
mcp.add_resource(Resource(
    uri="calc://current",
    name="Current Calculation",
    description="The result of the most recent calculation",
    text="No result yet",
    mimeType="text/plain"
))

mcp.add_resource(Resource(
    uri="calc://history",
    name="Calculation History",
    description="History of all calculations performed",
    text="No calculations yet",
    mimeType="text/plain"
))


if __name__ == "__main__":
    print("Starting Math SSE server with resource support on http://localhost:8000")
    print("Available resources:")
    print(" - calc://current - Current calculation result")
    print(" - calc://history - History of calculations")
    print(" - calc://timestamp/{time} - Template for timestamp data")
    print("Press Ctrl+C to stop")
    mcp.run(transport="sse")