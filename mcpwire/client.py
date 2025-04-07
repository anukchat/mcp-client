# mcpwire/mcpwire/client.py

"""
Core MCPClient class for interacting with an MCP server.
Uses the official MCP library and langchain-mcp-adapters.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List, Union, Type, TypeVar, Mapping, Literal
from pathlib import Path
from contextlib import AsyncExitStack
from types import TracebackType

from pydantic import BaseModel

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.prompts import load_mcp_prompt
from langchain_mcp_adapters.tools import load_mcp_tools

from .exceptions import (
    MCPConnectionError, MCPAPIError, MCPTimeoutError, MCPDataError, MCPError
)
from .models import ServerMetadata, ListResourcesResponse, Resource, ResourceTemplate, ReadResourceResponse, ResourceContent

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)
DEFAULT_TIMEOUT = 60
DEFAULT_CONFIG_FILENAME = "mcp.json"
DEFAULT_ENCODING = "utf-8"
DEFAULT_ENCODING_ERROR_HANDLER: Literal["strict", "ignore", "replace"] = "strict"
DEFAULT_HTTP_TIMEOUT = 5
DEFAULT_SSE_READ_TIMEOUT = 60 * 5

class StdioConnection(dict):
    """Configuration for stdio connection to MCP server."""
    transport: Literal["stdio"]
    command: str
    """The executable to run to start the server."""
    args: List[str]
    """Command line arguments to pass to the executable."""
    env: Optional[Dict[str, str]] = None
    """The environment to use when spawning the process."""
    cwd: Optional[Union[str, Path]] = None
    """The working directory to use when spawning the process."""
    encoding: str = DEFAULT_ENCODING
    """The text encoding used when sending/receiving messages to the server."""
    encoding_error_handler: Literal["strict", "ignore", "replace"] = DEFAULT_ENCODING_ERROR_HANDLER
    """
    The text encoding error handler.
    See https://docs.python.org/3/library/codecs.html#codec-base-classes for
    explanations of possible values
    """
    session_kwargs: Optional[Dict[str, Any]] = None
    """Additional keyword arguments to pass to the ClientSession"""

class SSEConnection(dict):
    """Configuration for SSE connection to MCP server."""
    transport: Literal["sse"]
    url: str
    """The URL of the SSE endpoint to connect to."""
    headers: Optional[Dict[str, Any]] = None
    """HTTP headers to send to the SSE endpoint"""
    timeout: float = DEFAULT_HTTP_TIMEOUT
    """HTTP timeout"""
    sse_read_timeout: float = DEFAULT_SSE_READ_TIMEOUT
    """SSE read timeout"""
    session_kwargs: Optional[Dict[str, Any]] = None
    """Additional keyword arguments to pass to the ClientSession"""

class MCPClient:
    """
    Client for interacting with a Model Context Protocol (MCP) server.
    Uses the official MCP library and langchain-mcp-adapters.
    
    This client maintains backward compatibility with the previous API
    while using the modern MCP implementation underneath.
    """
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        api_key: Optional[str] = None,
        default_headers: Optional[Mapping[str, str]] = None,
        default_parameters: Optional[Mapping[str, Any]] = None,
        _config_default_headers: Optional[Mapping[str, str]] = None,
        _config_default_parameters: Optional[Mapping[str, Any]] = None,
        transport: str = "http",
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
    ):
        self.transport = transport
        self.command = command
        self.args = args or []
        self.base_url = base_url.rstrip('/') if base_url else None
        self.timeout = timeout
        
        # Store default parameters
        self.default_parameters = {}
        if _config_default_parameters:
            self.default_parameters.update(_config_default_parameters)
        if default_parameters:
            self.default_parameters.update(default_parameters)
            
        # Process API key
        resolved_api_key = None
        if isinstance(api_key, str):
            if api_key.startswith("env:"):
                env_var_name = api_key.split(":", 1)[1]
                resolved_api_key = os.getenv(env_var_name)
                if not resolved_api_key:
                    logger.warning(f"API key environment variable '{env_var_name}' specified but not found.")
                else:
                    logger.debug(f"Loaded API key from environment variable '{env_var_name}'.")
            else:
                resolved_api_key = api_key
        
        # Process headers
        self.headers = {}
        if _config_default_headers:
            self.headers.update(_config_default_headers)
        if default_headers:
            self.headers.update(default_headers)
        if resolved_api_key:
            self.headers["Authorization"] = f"Bearer {resolved_api_key}"
            
        # Initialize MCP client
        self._mcpwire = None
        self._exit_stack = None
        
        logger.info(f"MCPClient initialized (Transport: {self.transport})")
        if self.base_url:
            logger.info(f"Base URL: {self.base_url}")
        
    @classmethod
    def _find_config_file(cls, config_path: Optional[str] = None) -> Optional[Path]:
        """ Finds the MCP configuration file. """
        potential_paths = []
        if config_path:
            potential_paths.append(Path(config_path).resolve())
        else:
            potential_paths.append(Path.cwd() / DEFAULT_CONFIG_FILENAME)
            try:
                home_dir = Path.home()
                potential_paths.append(home_dir / f".{DEFAULT_CONFIG_FILENAME}")
                potential_paths.append(home_dir / ".config" / "mcp" / DEFAULT_CONFIG_FILENAME)
            except RuntimeError:
                 logger.warning("Could not determine home directory for config search.")

        for path in potential_paths:
            try:
                if path.is_file():
                    logger.debug(f"Found configuration file at: {path}")
                    return path
            except OSError as e:
                logger.debug(f"Could not access potential config path {path}: {e}")
                continue

        logger.debug(f"Configuration file '{DEFAULT_CONFIG_FILENAME}' not found in specified or standard locations.")
        return None

    @classmethod
    def from_config(
        cls,
        server_name: Optional[str] = None,
        config_path: Optional[str] = None,
        **kwargs
    ) -> 'MCPClient':
        """
        Creates an MCPClient instance by loading configuration from a JSON file.
        
        Args:
            server_name: The name (alias) of the server configuration to load.
                         If None, uses "default_server" from the file or "default".
            config_path: Optional explicit path to the configuration file.
                         If None, searches in standard locations.
            **kwargs: Additional keyword arguments passed directly to the
                      MCPClient constructor, overriding values loaded from
                      the config file.
        
        Returns: An initialized MCPClient instance.
        Raises: FileNotFoundError, ValueError, KeyError, MCPDataError, OSError, MCPError
        """
        logger.info(f"Attempting to load MCP configuration (Server: {server_name or 'default'}, Path: {config_path or 'search'})")

        found_config_path = cls._find_config_file(config_path)
        if not found_config_path:
            raise FileNotFoundError(f"MCP configuration file not found at '{config_path}' or in standard locations.")

        logger.info(f"Loading MCP configuration from: {found_config_path}")

        try:
            with open(found_config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise MCPDataError(f"Invalid JSON in configuration file '{found_config_path}': {e}") from e
        except OSError as e:
            raise OSError(f"Could not read configuration file '{found_config_path}': {e}") from e
        except Exception as e:
             raise MCPError(f"Unexpected error loading config file '{found_config_path}': {e}") from e

        # Determine target server name
        target_server_name = server_name
        if not target_server_name:
            target_server_name = config_data.get("default_server")
            if not target_server_name:
                if "default" in config_data.get("servers", {}):
                     target_server_name = "default"
                else:
                    raise ValueError(f"No server_name specified and no 'default_server' key or 'default' server found in '{found_config_path}'.")
            logger.info(f"Using default server configuration: '{target_server_name}'")

        # Get the specific server's configuration
        servers_dict = config_data.get("servers")
        if not isinstance(servers_dict, dict):
             raise MCPDataError(f"Missing or invalid 'servers' dictionary in '{found_config_path}'.")

        server_config = servers_dict.get(target_server_name)
        if not isinstance(server_config, dict):
            raise KeyError(f"Server configuration '{target_server_name}' not found or is not a valid dictionary in '{found_config_path}'.")
        logger.info(f"Loaded configuration for server: '{target_server_name}'")

        # Extract configuration values from JSON
        base_url = server_config.get("base_url")
        transport = server_config.get("transport", "http").lower()
        command = server_config.get("command")
        args = server_config.get("args")

        if transport == "stdio":
            if not command:
                raise MCPDataError(f"Missing 'command' for stdio transport in server '{target_server_name}'.")
            if not isinstance(command, str):
                raise MCPDataError(f"Invalid 'command' format for stdio transport in server '{target_server_name}'. Expected a string.")
            if args is not None and not isinstance(args, list):
                raise MCPDataError(f"Invalid 'args' format for stdio transport in server '{target_server_name}'. Expected a list.")
            base_url = None # Base URL is not relevant for stdio
        elif transport in ["http", "sse"]:
            if not base_url or not isinstance(base_url, str):
                raise MCPDataError(f"Missing or invalid 'base_url' (string) for server '{target_server_name}' with transport '{transport}'.")
        else:
            raise ValueError(f"Unsupported transport protocol '{transport}' for server '{target_server_name}'.")
            
        # Extract values from config
        api_key_from_conf = server_config.get("api_key")
        timeout_from_conf = server_config.get("timeout")
        config_default_headers = server_config.get("default_headers")
        config_default_parameters = server_config.get("default_parameters")

        # Validate types from config
        if config_default_headers is not None and not isinstance(config_default_headers, dict):
             logger.warning(f"Invalid 'default_headers' format for server '{target_server_name}'. Expected a dictionary, got {type(config_default_headers)}. Ignoring.")
             config_default_headers = None
        if config_default_parameters is not None and not isinstance(config_default_parameters, dict):
             logger.warning(f"Invalid 'default_parameters' format for server '{target_server_name}'. Expected a dictionary, got {type(config_default_parameters)}. Ignoring.")
             config_default_parameters = None

        # Prepare arguments for __init__
        init_kwargs = {
            "base_url": kwargs.get("base_url", base_url),
            "timeout": kwargs.get("timeout", timeout_from_conf) or DEFAULT_TIMEOUT,
            "api_key": kwargs.get("api_key", api_key_from_conf),
            "_config_default_headers": config_default_headers,
            "_config_default_parameters": config_default_parameters,
            "default_headers": kwargs.get("default_headers"),
            "default_parameters": kwargs.get("default_parameters"),
            "transport": kwargs.get("transport", transport),
            "command": kwargs.get("command", command),
            "args": kwargs.get("args", args),
        }

        # Filter out None values for kwargs that shouldn't be passed if not provided
        filtered_kwargs = {}
        for k, v in init_kwargs.items():
            if v is not None:
                filtered_kwargs[k] = v
            elif k in ["timeout"] or (init_kwargs.get("transport") == "http" and k == "base_url") or (init_kwargs.get("transport") == "stdio" and k == "command"):
                filtered_kwargs[k] = v # Keep essential ones even if None

        # Create the client instance
        return cls(**filtered_kwargs)
        
    async def _initialize(self):
        """Initialize the MCP client for use."""
        if self._exit_stack is None:
            self._exit_stack = AsyncExitStack()
            
            if self.transport == "stdio":
                # Create stdio connection
                env = {}
                if "PATH" not in env:
                    env["PATH"] = os.environ.get("PATH", "")
                
                server_params = StdioServerParameters(
                    command=self.command,
                    args=self.args,
                    env=env,
                    encoding=DEFAULT_ENCODING,
                    encoding_error_handler=DEFAULT_ENCODING_ERROR_HANDLER,
                )
                
                stdio_transport = await self._exit_stack.enter_async_context(stdio_client(server_params))
                read, write = stdio_transport
                session = await self._exit_stack.enter_async_context(ClientSession(read, write))
                
                # Initialize the session
                await session.initialize()
                self._mcpwire = session
                
            elif self.transport == "sse":
                # Create SSE connection
                if not self.base_url:
                    raise MCPConnectionError("Base URL is required for SSE transport")
                    
                sse_transport = await self._exit_stack.enter_async_context(
                    sse_client(self.base_url, self.headers, DEFAULT_HTTP_TIMEOUT, DEFAULT_SSE_READ_TIMEOUT)
                )
                read, write = sse_transport
                session = await self._exit_stack.enter_async_context(ClientSession(read, write))
                
                # Initialize the session
                await session.initialize()
                self._mcpwire = session
            
            elif self.transport == "http":
                raise ValueError("HTTP transport is not supported by the official MCP library. Use 'sse' instead.")
            
            else:
                raise ValueError(f"Unsupported transport protocol: {self.transport}")
    
    async def list_tools(self) -> List[BaseTool]:
        """List all available tools."""
        await self._initialize()
        return await load_mcp_tools(self._mcpwire)
        
    async def get_prompt(self, prompt_name: str, arguments: Optional[Dict[str, Any]] = None) -> List[Union[HumanMessage, AIMessage]]:
        """Get a prompt from the MCP server."""
        await self._initialize()
        return await load_mcp_prompt(self._mcpwire, prompt_name, arguments)
        
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool."""
        await self._initialize()
        return await self._mcpwire.call_tool(tool_name, arguments)
        
    async def get_server_metadata(self) -> ServerMetadata:
        """Get metadata from the MCP server."""
        await self._initialize()
        # Convert MCP server metadata to our ServerMetadata format
        metadata = await self._mcpwire.get_server_info()
        # Note: This is a simplified version, full implementation would need to map
        # all fields from MCP's ServerInfo to our ServerMetadata model
        return ServerMetadata(
            id=metadata.id,
            name=metadata.name,
            version=metadata.version,
            description=metadata.description
        )
        
    async def list_resources(self) -> ListResourcesResponse:
        """
        List all available resources and resource templates from the MCP server.
        
        Returns:
            ListResourcesResponse: Object containing lists of resources and templates.
            
        Raises:
            MCPConnectionError: If connection to the server fails.
            MCPAPIError: If the server returns an error response.
            MCPTimeoutError: If the request times out.
        """
        await self._initialize()
        try:
            response = await self._mcpwire.list_resources()
            
            # Convert to our response format
            return ListResourcesResponse(
                resources=[
                    Resource(
                        uri=str(resource.uri),  # Convert URI to string to avoid validation issues
                        name=resource.name,
                        description=resource.description,
                        mime_type=getattr(resource, "mimeType", None) or getattr(resource, "mime_type", None)
                    ) for resource in response.resources or []
                ],
                templates=[
                    ResourceTemplate(
                        uri_template=template.uri_template,
                        name=template.name,
                        description=template.description,
                        mime_type=getattr(template, "mimeType", None) or getattr(template, "mime_type", None)
                    ) for template in getattr(response, 'templates', []) or []
                ]
            )
        except Exception as e:
            logger.error(f"Error listing resources: {e}")
            raise MCPAPIError(f"Failed to list resources: {e}") from e
    
    async def read_resource(self, uri: str) -> ReadResourceResponse:
        """
        Read the content of a resource by its URI.
        
        Args:
            uri: The URI of the resource to read.
            
        Returns:
            ReadResourceResponse: Object containing the resource contents.
            
        Raises:
            MCPConnectionError: If connection to the server fails.
            MCPAPIError: If the server returns an error response.
            MCPTimeoutError: If the request times out.
        """
        await self._initialize()
        try:
            response = await self._mcpwire.read_resource(uri)
            
            # Convert to our response format
            contents = []
            for content in response.contents:
                # Handle different content types from the MCP library
                contents.append(ResourceContent(
                    uri=str(content.uri),
                    mime_type=getattr(content, "mimeType", None) or getattr(content, "mime_type", None),
                    text=getattr(content, "text", None),
                    blob=getattr(content, "blob", None)
                ))
            
            return ReadResourceResponse(contents=contents)
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}")
            raise MCPAPIError(f"Failed to read resource {uri}: {e}") from e
    
    async def subscribe_to_resource(self, uri: str) -> None:
        """
        Subscribe to updates for a resource.
        
        Note: This is implemented as a no-op if the underlying MCP client 
        does not support resource subscription.
        
        Args:
            uri: The URI of the resource to subscribe to.
            
        Raises:
            MCPConnectionError: If connection to the server fails.
            MCPAPIError: If the server returns an error response.
            MCPTimeoutError: If the request times out.
        """
        await self._initialize()
        try:
            if hasattr(self._mcpwire, 'subscribe_to_resource'):
                await self._mcpwire.subscribe_to_resource(uri)
            else:
                logger.warning(f"Resource subscription not supported by this MCP implementation")
        except Exception as e:
            logger.error(f"Error subscribing to resource {uri}: {e}")
            raise MCPAPIError(f"Failed to subscribe to resource {uri}: {e}") from e
    
    async def unsubscribe_from_resource(self, uri: str) -> None:
        """
        Unsubscribe from updates for a resource.
        
        Note: This is implemented as a no-op if the underlying MCP client 
        does not support resource subscription.
        
        Args:
            uri: The URI of the resource to unsubscribe from.
            
        Raises:
            MCPConnectionError: If connection to the server fails.
            MCPAPIError: If the server returns an error response.
            MCPTimeoutError: If the request times out.
        """
        await self._initialize()
        try:
            if hasattr(self._mcpwire, 'unsubscribe_from_resource'):
                await self._mcpwire.unsubscribe_from_resource(uri)
            else:
                logger.warning(f"Resource subscription not supported by this MCP implementation")
        except Exception as e:
            logger.error(f"Error unsubscribing from resource {uri}: {e}")
            raise MCPAPIError(f"Failed to unsubscribe from resource {uri}: {e}") from e
        
    async def close(self):
        """Close the MCP client."""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self._mcpwire = None
            
    async def __aenter__(self):
        """Enable use of the client as an async context manager."""
        await self._initialize()
        return self
        
    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType]
    ):
        """Ensure the client is closed when exiting the context manager."""
        await self.close()
        
    def __enter__(self):
        """
        Backward compatibility for synchronous context manager usage.
        Note: This can't work with the async MCP client and will raise an error.
        """
        raise RuntimeError(
            "The MCPClient using the official MCP library only supports async context manager usage. "
            "Please use 'async with MCPClient(...) as client:' instead."
        )
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Backward compatibility for synchronous context manager usage."""
        pass
        
class MultiServerMCPClient:
    """
    Client for connecting to multiple MCP servers and loading tools from them.
    This is a wrapper around langchain_mcp_adapters.client.MultiServerMCPClient.
    """
    def __init__(self, connections: Optional[Dict[str, Union[StdioConnection, SSEConnection]]] = None):
        """
        Initialize a MultiServerMCPClient with MCP servers connections.
        
        Args:
            connections: A dictionary mapping server names to connection configurations.
                Each configuration can be either a StdioConnection or SSEConnection.
                If None, no initial connections are established.
        """
        from langchain_mcp_adapters.client import MultiServerMCPClient as LangchainMultiServerMCPClient
        self._mcpwire = LangchainMultiServerMCPClient(connections)
        
    async def connect_to_server(self, server_name: str, **kwargs):
        """Connect to an MCP server."""
        await self._mcpwire.connect_to_server(server_name, **kwargs)
        
    def get_tools(self):
        """Get all tools from all connected servers."""
        return self._mcpwire.get_tools()
        
    async def get_prompt(self, server_name: str, prompt_name: str, arguments: Optional[Dict[str, Any]] = None):
        """Get a prompt from a specific server."""
        return await self._mcpwire.get_prompt(server_name, prompt_name, arguments)
    
    def get_server(self, server_name: str):
        """
        Get a server by name.
        
        Args:
            server_name: The name of the server to get.
            
        Returns:
            The server session if found, None otherwise.
        """
        return self._mcpwire.get_server(server_name)
    
    async def list_resources(self, server_name: str) -> ListResourcesResponse:
        """
        List resources from a specific server.
        
        Args:
            server_name: The name of the server to get resources from.
            
        Returns:
            ListResourcesResponse: Object containing lists of resources and templates.
            
        Raises:
            ValueError: If the server is not found.
            MCPAPIError: If the server returns an error.
        """
        server = self.get_server(server_name)
        if not server:
            raise ValueError(f"Server '{server_name}' not found.")
        
        try:
            response = await server.list_resources()
            
            # Convert to our response format
            return ListResourcesResponse(
                resources=[
                    Resource(
                        uri=str(resource.uri),  # Convert URI to string to avoid validation issues
                        name=resource.name,
                        description=resource.description,
                        mime_type=getattr(resource, "mimeType", None) or getattr(resource, "mime_type", None)
                    ) for resource in response.resources or []
                ],
                templates=[
                    ResourceTemplate(
                        uri_template=template.uri_template,
                        name=template.name,
                        description=template.description,
                        mime_type=getattr(template, "mimeType", None) or getattr(template, "mime_type", None)
                    ) for template in getattr(response, 'templates', []) or []
                ]
            )
        except Exception as e:
            logger.error(f"Error listing resources from server {server_name}: {e}")
            raise MCPAPIError(f"Failed to list resources from server {server_name}: {e}") from e
    
    async def read_resource(self, server_name: str, uri: str) -> ReadResourceResponse:
        """
        Read a resource from a specific server.
        
        Args:
            server_name: The name of the server to read the resource from.
            uri: The URI of the resource to read.
            
        Returns:
            ReadResourceResponse: Object containing the resource contents.
            
        Raises:
            ValueError: If the server is not found.
            MCPAPIError: If the server returns an error.
        """
        server = self.get_server(server_name)
        if not server:
            raise ValueError(f"Server '{server_name}' not found.")
        
        try:
            response = await server.read_resource(uri)
            
            # Convert to our response format
            contents = []
            for content in response.contents:
                # Handle different content types from the MCP library
                contents.append(ResourceContent(
                    uri=str(content.uri),
                    mime_type=getattr(content, "mimeType", None) or getattr(content, "mime_type", None),
                    text=getattr(content, "text", None),
                    blob=getattr(content, "blob", None)
                ))
            
            return ReadResourceResponse(contents=contents)
        except Exception as e:
            logger.error(f"Error reading resource {uri} from server {server_name}: {e}")
            raise MCPAPIError(f"Failed to read resource {uri} from server {server_name}: {e}") from e
    
    async def subscribe_to_resource(self, server_name: str, uri: str) -> None:
        """
        Subscribe to updates for a specific resource on a specific server.
        
        Args:
            server_name: The name of the server.
            uri: The URI of the resource to subscribe to.
            
        Raises:
            ValueError: If the server is not found.
            MCPAPIError: If the server returns an error.
        """
        server = self.get_server(server_name)
        if not server:
            raise ValueError(f"Server '{server_name}' not found.")
        
        try:
            await server.subscribe_to_resource(uri)
            logger.debug(f"Subscribed to resource: {uri} on server {server_name}")
        except Exception as e:
            logger.error(f"Error subscribing to resource {uri} on server {server_name}: {e}")
            raise MCPAPIError(f"Failed to subscribe to resource {uri} on server {server_name}: {e}") from e
    
    async def unsubscribe_from_resource(self, server_name: str, uri: str) -> None:
        """
        Unsubscribe from updates for a specific resource on a specific server.
        
        Args:
            server_name: The name of the server.
            uri: The URI of the resource to unsubscribe from.
            
        Raises:
            ValueError: If the server is not found.
            MCPAPIError: If the server returns an error.
        """
        server = self.get_server(server_name)
        if not server:
            raise ValueError(f"Server '{server_name}' not found.")
        
        try:
            await server.unsubscribe_from_resource(uri)
            logger.debug(f"Unsubscribed from resource: {uri} on server {server_name}")
        except Exception as e:
            logger.error(f"Error unsubscribing from resource {uri} on server {server_name}: {e}")
            raise MCPAPIError(f"Failed to unsubscribe from resource {uri} on server {server_name}: {e}") from e
        
    async def __aenter__(self):
        """Enter async context."""
        return await self._mcpwire.__aenter__()
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        await self._mcpwire.__aexit__(exc_type, exc_val, exc_tb)