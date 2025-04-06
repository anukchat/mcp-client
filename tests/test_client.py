# mcp-python-client/tests/test_client.py

"""
Unit tests for the MCPClient.

Requires pytest and requests-mock:
  pip install pytest requests-mock
"""

import pytest
import requests
import json
import os
from pathlib import Path
from unittest.mock import patch, mock_open # For mocking file operations

from requests_mock import Mocker as RequestsMocker # Alias for clarity

from mcp_client import (
    MCPClient,
    PromptRequest,
    PromptMessage,
    PromptResponse,
    AssistantMessageResponse,
    ToolCall,
    ServerMetadata,
    ListToolsResponse,
    ToolDefinition,
    ToolParameterSchema,
    ToolParameterProperty,
    MCPAPIError,
    MCPConnectionError,
    MCPTimeoutError,
    MCPDataError,
    MCPError
)

# --- Test Fixtures ---

MOCK_SERVER_URL = "http://mock-mcp-server.test/v1" # Use a base path
MOCK_API_KEY = "test-api-key"
DEFAULT_TIMEOUT_VAL = 60 # Match client default

@pytest.fixture
def direct_client() -> MCPClient:
    """Provides an MCPClient instance initialized directly."""
    return MCPClient(base_url=MOCK_SERVER_URL, api_key=MOCK_API_KEY, timeout=5)

@pytest.fixture
def mock_prompt_request() -> PromptRequest:
    """Provides a sample PromptRequest object."""
    return PromptRequest(
        messages=[PromptMessage(role="user", content="Hello there!")]
    )

@pytest.fixture
def sample_config_dict() -> dict:
    """Provides a sample configuration dictionary."""
    return {
        "default_server": "local",
        "servers": {
            "local": {
                "base_url": "http://localhost:8000",
                "api_key": None,
                "timeout": 30,
                "description": "Local Test Server"
            },
            "remote": {
                "base_url": "https://remote-mcp.test",
                "api_key": "remote-key-123",
                "description": "Remote Test Server" # Uses default timeout
            },
             "env_key_server": {
                "base_url": "https://env-key.test",
                "api_key": "env:MCP_TEST_API_KEY",
                "timeout": 90
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

# == Direct Initialization Tests ==

def test_direct_client_initialization(direct_client: MCPClient):
    """Test direct init with correct base URL, headers, and timeout."""
    assert direct_client.base_url == MOCK_SERVER_URL # Should not have trailing slash stored
    assert direct_client.timeout == 5
    assert direct_client._session.headers["Accept"] == "application/json"
    assert direct_client._session.headers["Authorization"] == f"Bearer {MOCK_API_KEY}"

def test_direct_client_initialization_no_api_key():
    """Test direct init without an API key."""
    client_no_key = MCPClient(base_url=MOCK_SERVER_URL)
    assert "Authorization" not in client_no_key._session.headers

def test_direct_client_initialization_env_api_key_found(monkeypatch):
    """Test direct init resolves api_key from environment variable."""
    api_key_value = "key-from-environment"
    monkeypatch.setenv("MCP_DIRECT_TEST_KEY", api_key_value)
    client = MCPClient(base_url=MOCK_SERVER_URL, api_key="env:MCP_DIRECT_TEST_KEY")
    assert client._session.headers["Authorization"] == f"Bearer {api_key_value}"

def test_direct_client_initialization_env_api_key_not_found(monkeypatch):
    """Test direct init when env var for api_key is missing."""
    # Ensure the env var is not set
    monkeypatch.delenv("MCP_DIRECT_MISSING_KEY", raising=False)
    client = MCPClient(base_url=MOCK_SERVER_URL, api_key="env:MCP_DIRECT_MISSING_KEY")
    # Expect no Authorization header if env var is missing
    assert "Authorization" not in client._session.headers

def test_direct_client_initialization_empty_base_url():
    """Test that direct init fails with an empty base URL."""
    with pytest.raises(ValueError, match="base_url cannot be empty"):
        MCPClient(base_url="")

# == from_config Initialization Tests ==

def test_from_config_loads_specific_server(mock_config_file: Path):
    """Test loading a specific server config from the file."""
    client = MCPClient.from_config(server_name="remote", config_path=str(mock_config_file))
    assert isinstance(client, MCPClient)
    assert client.base_url == "https://remote-mcp.test"
    assert client._session.headers["Authorization"] == "Bearer remote-key-123"
    assert client.timeout == DEFAULT_TIMEOUT_VAL # Uses default timeout

def test_from_config_loads_default_server(mock_config_file: Path):
    """Test loading the default server specified in the file."""
    client = MCPClient.from_config(config_path=str(mock_config_file)) # No server_name specified
    assert isinstance(client, MCPClient)
    assert client.base_url == "http://localhost:8000"
    assert "Authorization" not in client._session.headers # api_key is null
    assert client.timeout == 30

def test_from_config_loads_env_key(mock_config_file: Path, monkeypatch):
    """Test loading config where API key comes from environment variable."""
    api_key_value = "actual-env-key-456"
    monkeypatch.setenv("MCP_TEST_API_KEY", api_key_value)
    client = MCPClient.from_config(server_name="env_key_server", config_path=str(mock_config_file))
    assert isinstance(client, MCPClient)
    assert client.base_url == "https://env-key.test"
    assert client._session.headers["Authorization"] == f"Bearer {api_key_value}"
    assert client.timeout == 90

def test_from_config_override_timeout(mock_config_file: Path):
    """Test overriding timeout via kwargs when using from_config."""
    client = MCPClient.from_config(server_name="local", config_path=str(mock_config_file), timeout=100)
    assert client.timeout == 100 # Kwarg overrides config value (30)

def test_from_config_file_not_found():
    """Test error handling when config file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        MCPClient.from_config(config_path="non_existent_mcp.json")

def test_from_config_invalid_json(tmp_path: Path):
    """Test error handling for invalid JSON format."""
    invalid_json_path = tmp_path / "invalid.json"
    with open(invalid_json_path, 'w') as f:
        f.write("{invalid json")
    with pytest.raises(MCPDataError, match="Invalid JSON"):
        MCPClient.from_config(config_path=str(invalid_json_path))

def test_from_config_missing_servers_key(tmp_path: Path):
    """Test error handling when 'servers' key is missing."""
    config_file = tmp_path / "missing_servers.json"
    with open(config_file, 'w') as f:
        json.dump({"default_server": "local"}, f)
    with pytest.raises(MCPDataError, match="Missing or invalid 'servers' dictionary"):
        MCPClient.from_config(config_path=str(config_file))

def test_from_config_server_name_not_found(mock_config_file: Path):
    """Test error handling when specified server name doesn't exist."""
    with pytest.raises(KeyError, match="'unknown_server' not found"):
        MCPClient.from_config(server_name="unknown_server", config_path=str(mock_config_file))

def test_from_config_missing_base_url(tmp_path: Path):
    """Test error handling when base_url is missing for a server."""
    config_file = tmp_path / "missing_url.json"
    with open(config_file, 'w') as f:
        json.dump({"servers": {"bad_server": {"api_key": "123"}}}, f)
    with pytest.raises(MCPDataError, match="Missing or invalid 'base_url'"):
        MCPClient.from_config(server_name="bad_server", config_path=str(config_file))

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


# == API Method Tests (using direct_client fixture) ==
# These tests remain largely the same, just ensure they use a client instance

def test_get_server_metadata_success(direct_client: MCPClient, requests_mock: RequestsMocker):
    """Test successful retrieval of server metadata."""
    mock_metadata = {"mcpVersion": "1.0"}
    expected_url = f"{MOCK_SERVER_URL}/" # Assumes metadata is at root
    requests_mock.get(expected_url, json=mock_metadata, status_code=200)
    metadata = direct_client.get_server_metadata()
    assert isinstance(metadata, ServerMetadata)
    assert metadata.mcp_version == "1.0"

def test_get_server_metadata_api_error(direct_client: MCPClient, requests_mock: RequestsMocker):
    """Test handling of API error when fetching metadata."""
    requests_mock.get(f"{MOCK_SERVER_URL}/", status_code=500, json={"error": "Server meltdown"})
    with pytest.raises(MCPAPIError) as excinfo:
        direct_client.get_server_metadata()
    assert excinfo.value.status_code == 500

def test_send_prompt_success(direct_client: MCPClient, requests_mock: RequestsMocker, mock_prompt_request: PromptRequest):
    """Test successfully sending a prompt and receiving a valid response."""
    mock_response_data = {
        "message": {"role": "assistant", "content": "General Kenobi!"},
        "session_id": "sess_abc123",
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8}
    }
    requests_mock.post(f"{MOCK_SERVER_URL}/prompt", json=mock_response_data, status_code=200)
    response = direct_client.send_prompt(mock_prompt_request)
    assert isinstance(response, PromptResponse)
    assert response.message.content == "General Kenobi!"

def test_send_prompt_api_error(direct_client: MCPClient, requests_mock: RequestsMocker, mock_prompt_request: PromptRequest):
    """Test handling of API error during prompt sending."""
    requests_mock.post(f"{MOCK_SERVER_URL}/prompt", status_code=400, json={"detail": "Invalid request"})
    with pytest.raises(MCPAPIError) as excinfo:
        direct_client.send_prompt(mock_prompt_request)
    assert excinfo.value.status_code == 400

def test_send_prompt_timeout(direct_client: MCPClient, requests_mock: RequestsMocker, mock_prompt_request: PromptRequest):
    """Test handling of a request timeout."""
    requests_mock.post(f"{MOCK_SERVER_URL}/prompt", exc=requests.exceptions.Timeout)
    with pytest.raises(MCPTimeoutError):
        direct_client.send_prompt(mock_prompt_request)

def test_send_prompt_connection_error(direct_client: MCPClient, requests_mock: RequestsMocker, mock_prompt_request: PromptRequest):
    """Test handling of a connection error."""
    requests_mock.post(f"{MOCK_SERVER_URL}/prompt", exc=requests.exceptions.ConnectionError)
    with pytest.raises(MCPConnectionError):
        direct_client.send_prompt(mock_prompt_request)

def test_list_tools_success(direct_client: MCPClient, requests_mock: RequestsMocker):
    """Test successfully listing available tools."""
    mock_tool_data = {"tools": [{"name": "get_weather", "parameters": {"type": "object", "properties": {}}}]}
    requests_mock.get(f"{MOCK_SERVER_URL}/tools", json=mock_tool_data, status_code=200)
    tools = direct_client.list_tools()
    assert isinstance(tools, list)
    assert len(tools) == 1
    assert tools[0].name == "get_weather"

def test_list_tools_404_returns_empty(direct_client: MCPClient, requests_mock: RequestsMocker):
    """Test that a 404 on /tools returns an empty list gracefully."""
    requests_mock.get(f"{MOCK_SERVER_URL}/tools", status_code=404)
    tools = direct_client.list_tools()
    assert tools == []

# --- Add more tests ---
# - Test list_resources (success, 404, other errors)
# - Test get_resource (success, 404, other errors)
# - Test client used as context manager (__enter__, __exit__, close)
# - Test parsing of tool calls with arguments
# - Test sending tool results back

