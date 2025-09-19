import os
import json
import asyncio
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

async def test_filesystem_stdio():
    print("Testing filesystem operations via stdio...")
    
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="npx",
        args=["@modelcontextprotocol/server-filesystem", os.path.abspath(os.getcwd())],
        env=None
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()
                
                # List available tools
                try:
                    tools = await session.list_tools()
                    print("\nAvailable tools:")
                    
                    if tools and hasattr(tools, 'tools'):
                        # Print each tool with its name and description
                        for tool in tools.tools:
                            print(f"\n- {tool.name}")
                            print(f"  Description: {tool.description}")
                            if tool.inputSchema:
                                print("  Parameters:")
                                for param, schema in tool.inputSchema.get('properties', {}).items():
                                    required = param in tool.inputSchema.get('required', [])
                                    print(f"    - {param}: {schema.get('type', 'unknown')} {'(required)' if required else '(optional)'}")
                    else:
                        print("No tools available")
                except Exception as e:
                    print(f"Error listing tools: {str(e)}")
                    return
                
                # Test 1: List allowed directories
                print("\n1. Listing allowed directories:")
                try:
                    result = await session.call_tool("list_allowed_directories", {})
                    print("Response:", result)
                except Exception as e:
                    print(f"Error listing allowed directories: {str(e)}")
                
                # Test 2: Create a test directory
                print("\n2. Creating test directory:")
                try:
                    result = await session.call_tool("create_directory", {"path": "test_dir"})
                    print("Response:", result)
                except Exception as e:
                    print(f"Error creating directory: {str(e)}")
                
                # Test 3: Create a test file
                print("\n3. Creating test file:")
                try:
                    result = await session.call_tool("write_file", {
                        "path": "test_dir/test_stdio.txt",
                        "content": "This is a test file created via stdio mode."
                    })
                    print("Response:", result)
                except Exception as e:
                    print(f"Error creating file: {str(e)}")
                
                # Test 4: Get file info
                print("\n4. Getting file info:")
                try:
                    result = await session.call_tool("get_file_info", {"path": "test_dir/test_stdio.txt"})
                    print("Response:", result)
                except Exception as e:
                    print(f"Error getting file info: {str(e)}")
                
                # Test 5: Read the test file
                print("\n5. Reading test file:")
                try:
                    result = await session.call_tool("read_file", {"path": "test_dir/test_stdio.txt"})
                    print("Response:", result)
                except Exception as e:
                    print(f"Error reading file: {str(e)}")
                
                # Test 6: List directory contents
                print("\n6. Listing directory contents:")
                try:
                    result = await session.call_tool("list_directory", {"path": "test_dir"})
                    print("Response:", result)
                except Exception as e:
                    print(f"Error listing directory: {str(e)}")
                
                # Test 7: Get directory tree
                print("\n7. Getting directory tree:")
                try:
                    result = await session.call_tool("directory_tree", {"path": "."})
                    print("Response:", result)
                except Exception as e:
                    print(f"Error getting directory tree: {str(e)}")
                
                # Test 8: Search for files
                print("\n8. Searching for files:")
                try:
                    result = await session.call_tool("search_files", {
                        "path": ".",
                        "pattern": "test",
                        "excludePatterns": ["__pycache__"]
                    })
                    print("Response:", result)
                except Exception as e:
                    print(f"Error searching files: {str(e)}")
                
                # Test 9: Edit file with dry run
                print("\n9. Editing file (dry run):")
                try:
                    result = await session.call_tool("edit_file", {
                        "path": "test_dir/test_stdio.txt",
                        "edits": [
                            {
                                "oldText": "Line 2 of the test file.",
                                "newText": "This line has been modified."
                            },
                            {
                                "oldText": "Line 3 of the test file.",
                                "newText": "This is a new line added to the file."
                            }
                        ],
                        "dryRun": True
                    })
                    print("Response (dry run):", result)
                except Exception as e:
                    print(f"Error editing file (dry run): {str(e)}")
                
                # Test 10: Edit file for real
                print("\n10. Editing file (actual changes):")
                try:
                    result = await session.call_tool("edit_file", {
                        "path": "test_dir/test_stdio.txt",
                        "edits": [
                            {
                                "oldText": "Line 2 of the test file.",
                                "newText": "This line has been modified."
                            },
                            {
                                "oldText": "Line 3 of the test file.",
                                "newText": "This is a new line added to the file."
                            }
                        ],
                        "dryRun": False
                    })
                    print("Response (actual changes):", result)
                except Exception as e:
                    print(f"Error editing file: {str(e)}")
                
                # Clean up
                print("\nCleaning up...")
                try:
                    # Move the test file to root directory
                    await session.call_tool("move_file", {
                        "source": "test_dir/test_stdio.txt",
                        "destination": "test_stdio.txt"
                    })
                    print("Moved test file to root directory")
                except Exception as e:
                    print(f"Error during cleanup: {str(e)}")
    
    except Exception as e:
        print(f"Error in main execution: {str(e)}")
    finally:
        # Ensure all resources are properly closed
        await asyncio.sleep(0.1)  # Give time for pending operations to complete

def main():
    try:
        # Create and set a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run the test
        loop.run_until_complete(test_filesystem_stdio())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Error running test: {str(e)}")
    finally:
        try:
            # Clean up the event loop
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

if __name__ == "__main__":
    main() 