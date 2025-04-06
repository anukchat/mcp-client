# mcp-python-client/tests/test_client.py

"""
Unit tests for the MCPClient.

Requires pytest and pytest-asyncio:
  pip install pytest pytest-asyncio pytest-mock aioresponses
"""

import pytest
import json
import os
import asyncio
from pathlib import Path
from unittest.mock import patch, mock_open, AsyncMock, MagicMock

import pytest_asyncio
from aioresponses import aioresponses

from mcp_client import (
    MCPClient,
    MultiServerMCPClient,
    MCPAPIError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPDataError,
    MCPError,
    ServerMetadata
)
from langchain_core.messages import HumanMessage, AIMessage

# --- Test Fixtures ---

MOCK_SERVER_URL = "http://mock-mcp-server.test/v1"
MOCK_API_KEY = "test-api-key"
DEFAULT_TIMEOUT_VAL = 60

@pytest_asyncio.fixture
async def mock_client():
    """Provides a mocked MCPClient instance with patched _initialize method."""
    client = MCPClient(base_url=MOCK_SERVER_URL, transport="sse", api_key=MOCK_API_KEY, timeout=5)
    # Create a mock for the _mcp_client attribute
    client._mcp_client = AsyncMock()
    client._exit_stack = AsyncMock()
    client._initialized = True
    
    # Set up a context manager for the client
    yield client
    
    # Clean up the client after the test
    if hasattr(client, "_exit_stack") and client._exit_stack:
        await client._exit_stack.aclose()

@pytest_asyncio.fixture
async def mock_multi_client():
    """Provides a mocked MultiServerMCPClient instance."""
    # Create a mock for the underlying _mcp_client
    mock_mcp_client = AsyncMock()
    
    # Create the MultiServerMCPClient instance
    multi_client = MultiServerMCPClient()
    multi_client._mcp_client = mock_mcp_client
    
    yield multi_client

@pytest.fixture
def sample_config_dict() -> dict:
    """Provides a sample configuration dictionary."""
    return {
        "default_server": "local",
        "servers": {
            "local": {
                "base_url": "http://localhost:8000",
                "transport": "sse",
                "api_key": None,
                "timeout": 30,
                "description": "Local Test Server"
            },
            "remote": {
                "base_url": "https://remote-mcp.test",
                "transport": "sse",
                "api_key": "remote-key-123",
                "description": "Remote Test Server" # Uses default timeout
            },
            "env_key_server": {
                "base_url": "https://env-key.test",
                "transport": "sse",
                "api_key": "env:MCP_TEST_API_KEY",
                "timeout": 90
            },
            "stdio_server": {
                "transport": "stdio",
                "command": "python",
                "args": ["-m", "mcp.server.cli"],
                "timeout": 60
            }
        }
    }

@pytest.fixture
def mock_config_file(tmp_path: Path, sample_config_dict: dict) -> Path:
    """Creates a temporary config file for testing from_config."""
    config_file = tmp_path / "test_mcp.json"
    with open(config_file, 'w') as f:
        json.dump(sample_config_dict, f)
    return config_file

# --- Test Cases ---

# == Basic Client Tests ==

def test_client_initialization():
    """Test that the client initializes with the correct parameters."""
    client = MCPClient(base_url=MOCK_SERVER_URL, transport="sse", api_key=MOCK_API_KEY, timeout=5)
    assert client.base_url == MOCK_SERVER_URL
    assert client.transport == "sse"
    assert client.timeout == 5
    assert "Authorization" in client.headers
    assert client.headers["Authorization"] == f"Bearer {MOCK_API_KEY}"

def test_client_initialization_no_api_key():
    """Test client initialization without an API key."""
    client = MCPClient(base_url=MOCK_SERVER_URL, transport="sse")
    assert "Authorization" not in client.headers

def test_client_initialization_env_api_key_found(monkeypatch):
    """Test that env var api_key is resolved correctly."""
    api_key_value = "key-from-environment"
    monkeypatch.setenv("MCP_TEST_KEY", api_key_value)
    client = MCPClient(base_url=MOCK_SERVER_URL, transport="sse", api_key="env:MCP_TEST_KEY")
    assert client.headers["Authorization"] == f"Bearer {api_key_value}"

def test_client_initialization_env_api_key_not_found(monkeypatch):
    """Test behavior when env var for api_key is not found."""
    monkeypatch.delenv("MCP_MISSING_KEY", raising=False)
    client = MCPClient(base_url=MOCK_SERVER_URL, transport="sse", api_key="env:MCP_MISSING_KEY")
    assert "Authorization" not in client.headers

def test_client_initialization_http_transport():
    """Test that HTTP transport raises an error."""
    with pytest.raises(ValueError, match="HTTP transport is not supported"):
        MCPClient(base_url=MOCK_SERVER_URL, transport="http")

# == from_config Tests ==

def test_from_config_loads_specific_server(mock_config_file: Path):
    """Test loading a specific server from configuration."""
    client = MCPClient.from_config(server_name="remote", config_path=str(mock_config_file))
    assert client.base_url == "https://remote-mcp.test"
    assert client.transport == "sse"
    assert client.timeout == DEFAULT_TIMEOUT_VAL

def test_from_config_loads_default_server(mock_config_file: Path):
    """Test loading the default server from configuration."""
    client = MCPClient.from_config(config_path=str(mock_config_file))
    assert client.base_url == "http://localhost:8000"
    assert client.transport == "sse"
    assert client.timeout == 30

def test_from_config_loads_stdio_server(mock_config_file: Path):
    """Test loading a stdio server from configuration."""
    client = MCPClient.from_config(server_name="stdio_server", config_path=str(mock_config_file))
    assert client.transport == "stdio"
    assert client.command == "python"
    assert client.args == ["-m", "mcp.server.cli"]
    assert client.timeout == 60

def test_from_config_loads_env_key(mock_config_file: Path, monkeypatch):
    """Test loading a server with an env var API key."""
    api_key_value = "actual-env-key-456"
    monkeypatch.setenv("MCP_TEST_API_KEY", api_key_value)
    client = MCPClient.from_config(server_name="env_key_server", config_path=str(mock_config_file))
    assert client.headers["Authorization"] == f"Bearer {api_key_value}"

def test_from_config_file_not_found():
    """Test error when config file is not found."""
    with pytest.raises(FileNotFoundError):
        MCPClient.from_config(config_path="non_existent_file.json")

def test_from_config_invalid_json(tmp_path: Path):
    """Test error with invalid JSON in config file."""
    invalid_json_path = tmp_path / "invalid.json"
    with open(invalid_json_path, 'w') as f:
        f.write("{invalid json")
    with pytest.raises(MCPDataError, match="Invalid JSON"):
        MCPClient.from_config(config_path=str(invalid_json_path))

@patch("mcp_client.client.Path.home")
@patch("mcp_client.client.Path.cwd")
def test_find_config_file_search_order(mock_cwd, mock_home, tmp_path: Path):
    """Test the search order for the config file."""
    # Setup mock paths
    cwd_path = tmp_path / "cwd"
    home_path = tmp_path / "home"
    config_home_path = home_path / ".config" / "mcp"
    cwd_path.mkdir()
    home_path.mkdir()
    config_home_path.mkdir(parents=True)

    mock_cwd.return_value = cwd_path
    mock_home.return_value = home_path

    # Create files in different locations
    cwd_file = cwd_path / "mcp.json"; cwd_file.touch()
    home_dot_file = home_path / ".mcp.json"; home_dot_file.touch()
    xdg_config_file = config_home_path / "mcp.json"; xdg_config_file.touch()

    # 1. Explicit path
    explicit_path = tmp_path / "explicit.json"; explicit_path.touch()
    assert MCPClient._find_config_file(config_path=str(explicit_path)) == explicit_path.resolve()

    # 2. CWD
    assert MCPClient._find_config_file() == cwd_file # Should find in CWD first
    cwd_file.unlink() # Remove CWD file

    # 3. Home dot file
    assert MCPClient._find_config_file() == home_dot_file
    home_dot_file.unlink() # Remove home dot file

    # 4. XDG config file
    assert MCPClient._find_config_file() == xdg_config_file
    xdg_config_file.unlink() # Remove XDG file

    # 5. Not found
    assert MCPClient._find_config_file() is None

# == Async Client Method Tests ==

@pytest.mark.asyncio
async def test_initialize_method(monkeypatch):
    """Test the _initialize method for SSE transport."""
    # Mock the AsyncExitStack, stdio_client, and ClientSession
    mock_exit_stack = AsyncMock()
    mock_sse_client = AsyncMock()
    mock_client_session = AsyncMock()
    
    read_mock = MagicMock()
    write_mock = MagicMock()
    mock_sse_client.return_value.__aenter__.return_value = (read_mock, write_mock)
    mock_client_session.return_value.__aenter__.return_value = mock_client_session
    mock_client_session.initialize = AsyncMock()
    
    monkeypatch.setattr("mcp_client.client.AsyncExitStack", lambda: mock_exit_stack)
    monkeypatch.setattr("mcp_client.client.sse_client", mock_sse_client)
    monkeypatch.setattr("mcp_client.client.ClientSession", lambda *args, **kwargs: mock_client_session)
    
    # Create and initialize client
    client = MCPClient(base_url=MOCK_SERVER_URL, transport="sse")
    await client._initialize()
    
    # Check that the correct methods were called
    mock_sse_client.assert_called_once()
    mock_client_session.initialize.assert_called_once()
    assert client._mcp_client == mock_client_session

@pytest.mark.asyncio
async def test_get_server_metadata(mock_client):
    """Test getting server metadata."""
    # Setup mock return value
    metadata_mock = MagicMock()
    metadata_mock.id = "test-server-id"
    metadata_mock.name = "Test Server"
    metadata_mock.version = "1.0.0"
    metadata_mock.description = "A test server"
    mock_client._mcp_client.get_server_info.return_value = metadata_mock
    
    # Call the method
    result = await mock_client.get_server_metadata()
    
    # Check the result
    mock_client._mcp_client.get_server_info.assert_called_once()
    assert result.id == "test-server-id"
    assert result.name == "Test Server"
    assert result.version == "1.0.0"
    assert result.description == "A test server"

@pytest.mark.asyncio
async def test_list_tools(mock_client, monkeypatch):
    """Test listing tools from the server."""
    # Setup mock for load_mcp_tools
    mock_tools = [MagicMock()]
    mock_load_tools = AsyncMock(return_value=mock_tools)
    monkeypatch.setattr("mcp_client.client.load_mcp_tools", mock_load_tools)
    
    # Call the method
    result = await mock_client.list_tools()
    
    # Check the result
    mock_load_tools.assert_called_once_with(mock_client._mcp_client)
    assert result == mock_tools

@pytest.mark.asyncio
async def test_get_prompt(mock_client, monkeypatch):
    """Test getting a prompt from the server."""
    # Setup mock for load_mcp_prompt
    mock_messages = [HumanMessage(content="Hello"), AIMessage(content="Hi")]
    mock_load_prompt = AsyncMock(return_value=mock_messages)
    monkeypatch.setattr("mcp_client.client.load_mcp_prompt", mock_load_prompt)
    
    # Call the method
    result = await mock_client.get_prompt("test_prompt", {"param": "value"})
    
    # Check the result
    mock_load_prompt.assert_called_once_with(mock_client._mcp_client, "test_prompt", {"param": "value"})
    assert result == mock_messages

@pytest.mark.asyncio
async def test_call_tool(mock_client):
    """Test calling a tool on the server."""
    # Setup mock return value
    mock_result = {"result": "success"}
    mock_client._mcp_client.call_tool.return_value = mock_result
    
    # Call the method
    result = await mock_client.call_tool("test_tool", {"param": "value"})
    
    # Check the result
    mock_client._mcp_client.call_tool.assert_called_once_with("test_tool", {"param": "value"})
    assert result == mock_result

@pytest.mark.asyncio
async def test_client_as_async_context_manager(monkeypatch):
    """Test using the client as an async context manager."""
    # Create mocks
    mock_initialize = AsyncMock()
    mock_close = AsyncMock()
    
    # Create a client and patch its methods
    client = MCPClient(base_url=MOCK_SERVER_URL, transport="sse")
    client._initialize = mock_initialize
    client.close = mock_close
    
    # Use the client as a context manager
    async with client as c:
        assert c == client
        mock_initialize.assert_called_once()
        mock_close.assert_not_called()
    
    # Check that close was called after the context
    mock_close.assert_called_once()

def test_client_as_sync_context_manager():
    """Test that using the client as a sync context manager raises an error."""
    client = MCPClient(base_url=MOCK_SERVER_URL, transport="sse")
    with pytest.raises(RuntimeError, match="only supports async context manager usage"):
        with client:
            pass

# == MultiServerMCPClient Tests ==

@pytest.mark.asyncio
async def test_multi_client_connect_to_server(mock_multi_client):
    """Test connecting to a server with MultiServerMCPClient."""
    # Call the connect_to_server method
    await mock_multi_client.connect_to_server(
        "test_server",
        transport="stdio",
        command="python",
        args=["-m", "test"]
    )
    
    # Check that the underlying connect_to_server was called
    mock_multi_client._mcp_client.connect_to_server.assert_called_once_with(
        "test_server",
        transport="stdio",
        command="python",
        args=["-m", "test"]
    )

@pytest.mark.asyncio
async def test_multi_client_get_tools(mock_multi_client):
    """Test getting tools from MultiServerMCPClient."""
    # Setup mock return value
    mock_tools = [MagicMock(), MagicMock()]
    mock_multi_client._mcp_client.get_tools.return_value = mock_tools
    
    # Call the get_tools method
    result = mock_multi_client.get_tools()
    
    # Check the result
    mock_multi_client._mcp_client.get_tools.assert_called_once()
    assert result == mock_tools

@pytest.mark.asyncio
async def test_multi_client_get_prompt(mock_multi_client):
    """Test getting a prompt from MultiServerMCPClient."""
    # Setup mock return value
    mock_messages = [HumanMessage(content="Hello"), AIMessage(content="Hi")]
    mock_multi_client._mcp_client.get_prompt.return_value = mock_messages
    
    # Call the get_prompt method
    result = await mock_multi_client.get_prompt("server_name", "prompt_name", {"param": "value"})
    
    # Check the result
    mock_multi_client._mcp_client.get_prompt.assert_called_once_with("server_name", "prompt_name", {"param": "value"})
    assert result == mock_messages

@pytest.mark.asyncio
async def test_multi_client_as_async_context_manager(mock_multi_client):
    """Test using MultiServerMCPClient as an async context manager."""
    # Setup mock return values
    mock_multi_client._mcp_client.__aenter__.return_value = mock_multi_client._mcp_client
    
    # Use the client as a context manager
    async with mock_multi_client as client:
        assert client == mock_multi_client._mcp_client
        mock_multi_client._mcp_client.__aenter__.assert_called_once()
    
    # Check that __aexit__ was called
    mock_multi_client._mcp_client.__aexit__.assert_called_once()

# == Error Handling Tests ==

@pytest.mark.asyncio
async def test_mcp_connection_error(monkeypatch):
    """Test handling of connection errors."""
    # Setup mocks to raise connection error
    mock_exit_stack = AsyncMock()
    mock_sse_client = AsyncMock()
    mock_sse_client.side_effect = MCPConnectionError("Connection failed")
    
    monkeypatch.setattr("mcp_client.client.AsyncExitStack", lambda: mock_exit_stack)
    monkeypatch.setattr("mcp_client.client.sse_client", mock_sse_client)
    
    # Create client and attempt to initialize
    client = MCPClient(base_url=MOCK_SERVER_URL, transport="sse")
    with pytest.raises(MCPConnectionError, match="Connection failed"):
        await client._initialize()

@pytest.mark.asyncio
async def test_missing_base_url_for_sse():
    """Test that missing base_url for SSE raises an error."""
    client = MCPClient(transport="sse", base_url=None)
    with pytest.raises(MCPConnectionError, match="Base URL is required for SSE transport"):
        await client._initialize()

