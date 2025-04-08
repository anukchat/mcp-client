#!/usr/bin/env python3
# examples/with_langchain.py

"""
Example demonstrating how to use LangChain with MCPWire tools to answer user questions.

This example shows:
1. Setting up an MCPWire client
2. Loading tools from the MCP server
3. Creating a LangChain agent that can use these tools
4. Using the agent to answer user questions
"""

import asyncio
import logging
import os
import json
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from mcpwire import MCPClient, MCPError

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main function to demonstrate using MCPWire tools with LangChain."""
    logger.info("\n=== LangChain with MCPWire Tools Example ===\n")
    
    client = None
    try:
        # Load the client from config
        client = MCPClient.from_config()
        
        # Get available tools from the MCP server
        logger.info("Loading tools from MCP server...")
        tools = await client.list_tools()
        logger.info(f"Loaded {len(tools)} tools from the server")
        
        # Initialize the Gemini model
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-001",
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=0
        )
        
        # Bind tools to the model
        llm_with_tools = llm.bind_tools(tools)
        
        # Example questions to demonstrate the capabilities
        questions = [
            "List me all the available tools for me ?",
            "Multiply 10 and 25",
        ]
        
        # Process each question
        for question in questions:
            logger.info(f"\nQuestion: {question}")
            try:
                # Get the model's response
                response = await llm_with_tools.ainvoke([HumanMessage(content=question)])
                
                # Check if there is a function call in the response
                if hasattr(response, 'additional_kwargs') and 'function_call' in response.additional_kwargs:
                    function_call = response.additional_kwargs['function_call']
                    tool_name = function_call['name']
                    tool_args = json.loads(function_call['arguments'])
                    logger.info(f"Calling tool: {tool_name} with args: {tool_args}")
                    
                    # Call the tool and get the result
                    result = await client.call_tool(tool_name, tool_args)
                    
                    # Extract the actual result from the response
                    if hasattr(result, 'content') and result.content:
                        tool_result = result.content[0].text if result.content[0].type == 'text' else str(result.content[0])
                    else:
                        tool_result = str(result)
                    
                    # Create a human-readable answer
                    if tool_name == 'multiply':
                        answer = f"The result of multiplying {tool_args['a']} and {tool_args['b']} is {tool_result}"
                    elif tool_name == 'add':
                        answer = f"The result of adding {tool_args['a']} and {tool_args['b']} is {tool_result}"
                    else:
                        answer = f"Tool {tool_name} result: {tool_result}"
                    
                    logger.info(f"Answer: {answer}")
                else:
                    logger.info(f"Answer: {response.content}")
                    
            except Exception as e:
                logger.error(f"Error processing question: {e}")
                
    except MCPError as e:
        logger.error(f"MCP Error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # Clean up the client
        if client:
            try:
                await client.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error cleaning up client: {e}")

if __name__ == "__main__":
    asyncio.run(main())
