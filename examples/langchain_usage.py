#!/usr/bin/env python3
# examples/langchain_usage.py

"""
Example showing how to use the MCP client with LangChain.

This example demonstrates:
1. Using MultiServerMCPClient to load tools from MCP servers
2. Integrating those tools with LangChain
3. Building a simple LangChain agent that uses MCP tools
"""

import os
import asyncio
import logging
from typing import List, Dict, Any

# Import MCP client
from mcp_client import (
    MultiServerMCPClient,
    MCPConnectionError,
    MCPError
)

# Import LangChain components
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent
from langchain.agents.agent_types import AgentType
from langchain.agents import AgentExecutor

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_langchain_example():
    """Run the LangChain with MCP tools example."""
    logger.info("\n=== LangChain + MCP Integration Example ===\n")
    
    # Set up MCP client connections
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
    
    # Collect tools and build LangChain agent
    try:
        async with MultiServerMCPClient(connections) as multi_client:
            # Get all MCP tools
            mcp_tools = multi_client.get_tools()
            logger.info(f"Loaded {len(mcp_tools)} tools from MCP servers")
            
            # Load OpenAI API key from environment (or set it manually)
            openai_api_key = os.environ.get("OPENAI_API_KEY")
            if not openai_api_key:
                logger.error("OPENAI_API_KEY environment variable not set")
                logger.info("Set OPENAI_API_KEY to run this example")
                return
            
            # Create LangChain agent with MCP tools
            llm = ChatOpenAI(temperature=0)
            
            # Create an agent with the tools
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant with access to various tools."),
                ("human", "{input}"),
            ])
            
            # Create the agent
            agent = create_openai_tools_agent(llm, mcp_tools, prompt)
            agent_executor = AgentExecutor(agent=agent, tools=mcp_tools, verbose=True)
            
            # Run some examples
            questions = [
                "What's 25 squared plus the square root of 16?",
                "What's the weather like in San Francisco?",
                "Search for information about the Model Context Protocol (MCP)"
            ]
            
            for question in questions:
                try:
                    logger.info(f"\n--- Query: {question} ---")
                    result = await agent_executor.ainvoke({"input": question})
                    logger.info(f"Agent response: {result['output']}")
                except Exception as e:
                    logger.error(f"Error during agent execution: {e}")
    
    except MCPConnectionError as e:
        logger.error(f"Error connecting to MCP servers: {e}")
        logger.info("Make sure the required MCP servers are running")
    except MCPError as e:
        logger.error(f"MCP error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

if __name__ == "__main__":
    # Run the example
    asyncio.run(run_langchain_example())
