# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2023-05-15

### Added
- Complete support for MCP Resources API
- Added `list_resources()` method to get available resources and templates
- Added `read_resource(uri)` method to read resource content
- Added `subscribe_to_resource(uri)` and `unsubscribe_from_resource(uri)` methods
- Added support for resource templates
- Added resource configuration in mcp.json
- Added comprehensive examples for working with resources
- Added troubleshooting guide for common resource-related issues

### Changed
- Updated models to align with the MCP Resources specification
- Enhanced MultiServerMCPClient to support resources
- Improved error handling for resource operations
- Updated tests to cover resource functionality
- Updated documentation with resource usage examples

## [0.4.1] - 2023-04-06

### Added
- Migrated to official MCP library and langchain-mcp-adapters
- Added MultiServerMCPClient for connecting to multiple MCP servers
- Added async support for all client methods
- Added GitHub Actions workflows for CI/CD
- Added comprehensive examples for the new async API
- Added CHANGELOG.md to track changes

### Changed
- All client methods are now async and require `await`
- Context manager usage now requires `async with` instead of `with`
- Replaced custom HTTP handling with official MCP SSE transport
- Updated documentation to reflect the new async API
- Updated examples to demonstrate async usage

### Removed
- Removed support for HTTP transport (use SSE instead)
- Removed synchronous API (use async methods with `await` instead)

## [0.3.0] - 2023-03-15

### Added
- Enhanced configuration from mcp.json
- Support for stdio transport for local process communication
- Default parameters and headers for requests

### Changed
- Improved error handling and validation
- Updated documentation

## [0.2.0] - 2023-02-01

### Added
- Support for sending prompts to the MCP server
- Support for listing tools from the MCP server
- Support for listing resources from the MCP server
- Support for getting server metadata

### Changed
- Improved error handling
- Updated documentation

## [0.1.0] - 2023-01-15

### Added
- Initial release of the MCP client
- Basic support for the MCP protocol
- Support for authentication via API key 