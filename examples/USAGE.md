# MCP Client Usage Guide

This guide provides detailed usage instructions for the MCP client library, which has been updated to use the official MCP library and langchain-mcp-adapters.

## Basic Usage

### Installation

```bash
pip install mcpwire
```

### Async Nature of the API

Starting with version 0.4.1, the client API is asynchronous, requiring the use of `async/await` syntax:

```python
import asyncio
from mcpwire import MCPClient

async def main():
    client = MCPClient(base_url="http://localhost:8000", transport="sse")
    async with client as mcp:
        metadata = await mcp.get_server_metadata()
        print(f"Connected to: {metadata.name}")

# Run the async function
asyncio.run(main())
```

### Configuration

There are two ways to initialize the client:

1. **Direct Initialization**:

```python
from mcpwire import MCPClient

client = MCPClient(
    base_url="http://localhost:8000",
    transport="sse", # "sse" or "stdio", not "http" 
    timeout=30,
    api_key="your-api-key-or-env:ENV_VAR_NAME"
)
```

2. **From Configuration File**:

```python
from mcpwire import MCPClient

client = MCPClient.from_config(server_name="local")
```

### Server Configuration File (mcp.json)

Example configuration file:

```json
{
  "default_server": "local",
  "servers": {
    "local": {
      "base_url": "http://localhost:8000",
      "transport": "sse",
      "api_key": null,
      "timeout": 60,
      "description": "Local development server",
      "resources": {
        "enabled": true,
        "auto_subscribe": ["file:///workspace/shared/*"],
        "default_templates": [
          {
            "uri_template": "file:///workspace/{path}",
            "name": "Workspace File",
            "description": "Access files in the workspace directory"
          },
          {
            "uri_template": "db://customers/{customer_id}",
            "name": "Customer Record",
            "description": "Access customer data from the database",
            "mime_type": "application/json"
          }
        ]
      }
    },
    "stdio_server": {
      "transport": "stdio",
      "command": "python",
      "args": ["-m", "mcp.server.cli"],
      "timeout": 60,
      "description": "Local stdio server",
      "resources": {
        "enabled": false
      }
    }
  }
}
```

### Core Operations

#### Getting Server Metadata

```python
metadata = await mcp.get_server_metadata()
print(f"Server: {metadata.name} v{metadata.version}")
```

#### Listing Tools

```python
tools = await mcp.list_tools()
for tool in tools:
    print(f"Tool: {tool.name} - {tool.description}")
```

#### Getting Prompts

```python
messages = await mcp.get_prompt("hello_world", {})
for msg in messages:
    print(f"[{msg.type}] {msg.content}")
```

#### Calling Tools

```python
result = await mcp.call_tool("search", {"query": "MCP protocol"})
print(f"Tool result: {result}")
```

### Working with Resources

Version 0.5.1 adds comprehensive support for MCP resources. Here's how to use them:

#### Listing Resources and Templates

```python
# List available resources and templates
resources_result = await mcp.list_resources()
print(f"Found {len(resources_result.resources)} resources")
print(f"Found {len(resources_result.templates)} templates")

# Display available resources
for resource in resources_result.resources:
    print(f"Resource: {resource.name} (URI: {resource.uri})")
    
# Display available templates
for template in resources_result.templates:
    print(f"Template: {template.name} (URI Template: {template.uri_template})")
```

#### Reading Resource Content

```python
# Read a specific resource
content = await mcp.read_resource("file:///workspace/document.txt")

for item in content.contents:
    if item.text:  # Text resource
        print(f"Text content: {item.text}")
    elif item.blob:  # Binary resource (base64 encoded)
        # For binary resources
        import base64
        binary_data = base64.b64decode(item.blob)
        print(f"Binary content: {len(binary_data)} bytes")
```

#### Subscribing to Resource Updates

```python
# Subscribe to a resource to receive updates
resource_uri = "file:///workspace/document.txt"
await mcp.subscribe_to_resource(resource_uri)

# ... Use the resource ...

# Unsubscribe when no longer needed
await mcp.unsubscribe_from_resource(resource_uri)
```

#### Using Resource Templates

```python
# For a template like "file:///workspace/{path}"
file_uri = "file:///workspace/documents/report.pdf"
file_content = await mcp.read_resource(file_uri)

# For a template like "db://customers/{customer_id}"
customer_uri = "db://customers/12345"
customer_data = await mcp.read_resource(customer_uri)
```

## MultiServerMCPClient

The library includes a `MultiServerMCPClient` that allows connecting to multiple MCP servers:

```python
from mcpwire import MultiServerMCPClient

connections = {
    "math": {
        "transport": "stdio",
        "command": "python",
        "args": ["-m", "mcp.server.cli"],
    },
    "search": {
        "transport": "sse",
        "url": "http://localhost:8000/sse",
    }
}

async with MultiServerMCPClient(connections) as multi_client:
    all_tools = multi_client.get_tools()
    print(f"Total tools from all servers: {len(all_tools)}")
    
    # Add another server
    await multi_client.connect_to_server(
        "local",
        transport="stdio", 
        command="python",
        args=["-m", "mcp.server.cli"]
    )
    
    # Get a prompt from a specific server
    messages = await multi_client.get_prompt(
        server_name="math", 
        prompt_name="calculate", 
        arguments={"expression": "2+2"}
    )
    
    # Working with resources from multiple servers
    math_resources = await multi_client.list_resources("math")
    print(f"Math server has {len(math_resources.resources)} resources")
    
    # Read a resource from a specific server
    if math_resources.resources:
        math_resource_uri = math_resources.resources[0].uri
        math_content = await multi_client.read_resource("math", math_resource_uri)
        print(f"Read math resource: {math_resource_uri}")
        
        # Subscribe and unsubscribe
        await multi_client.subscribe_to_resource("math", math_resource_uri)
        await multi_client.unsubscribe_from_resource("math", math_resource_uri)
```

## Integration with LangChain

The library makes it easy to integrate with LangChain:

```python
from mcpwire import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate

# Set up connections
connections = {
    "math": {"transport": "stdio", "command": "python", "args": ["-m", "mcp.server.cli"]},
    "search": {"transport": "sse", "url": "http://localhost:8000/sse"}
}

async with MultiServerMCPClient(connections) as multi_client:
    # Get tools
    mcp_tools = multi_client.get_tools()
    
    # Set up LangChain components
    llm = ChatOpenAI(temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant with access to various tools."),
        ("human", "{input}"),
    ])
    
    # Create the agent
    agent = create_openai_tools_agent(llm, mcp_tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=mcp_tools, verbose=True)
    
    # Run the agent
    result = await agent_executor.ainvoke({"input": "Calculate 25 squared"})
    print(result["output"])
```

## Error Handling

The library provides several exception types for handling different error cases:

```python
from mcpwire import (
    MCPError,             # Base exception
    MCPConnectionError,   # Connection issues
    MCPTimeoutError,      # Request timeouts
    MCPAPIError,          # Server API errors
    MCPDataError          # Data validation errors
)

try:
    async with MCPClient(...) as mcp:
        await mcp.get_server_metadata()
except MCPConnectionError as e:
    print(f"Connection error: {e}")
except MCPTimeoutError as e:
    print(f"Timeout error: {e}")
except MCPAPIError as e:
    print(f"API error (Status {e.status_code}): {e}")
except MCPDataError as e:
    print(f"Data validation error: {e}")
except MCPError as e:
    print(f"General MCP error: {e}")
```

## Migration from v0.4.1 to v0.5.1

Version 0.5.1 adds comprehensive support for MCP Resources:

1. **Resource API**: New methods for working with resources (`list_resources()`, `read_resource()`, etc.)
2. **Configuration**: Added resource configuration options in mcp.json
3. **Resource Templates**: Support for URI templates to access dynamic resources
4. **Resource Subscriptions**: Subscribe to resource updates with `subscribe_to_resource()`
5. **MultiServer Resources**: Access resources from multiple servers with MultiServerMCPClient

## Migration from v0.3.0 to v0.4.1

The main changes when migrating from v0.3.0 to v0.4.1:

1. **Async API**: All methods are now async and require `await`.
2. **Context Manager**: Use `async with` instead of `with`.
3. **Transport Change**: HTTP transport is deprecated; use SSE instead.
4. **New Features**: Added MultiServerMCPClient for connecting to multiple servers.
5. **Integration**: Direct integration with langchain-mcp-adapters.

For detailed examples, see the `examples/` directory.
