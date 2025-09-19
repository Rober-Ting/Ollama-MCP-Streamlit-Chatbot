import os
import json
import asyncio
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

async def test_csv_operations():
    print("Testing CSV file operations via stdio...")
    
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
                
                # Test 1: Create a test CSV file
                print("\n1. Creating test CSV file:")
                try:
                    csv_content = """name,age,city
John,30,New York
Alice,25,London
Bob,35,Paris"""
                    result = await session.call_tool("write_file", {
                        "path": "test_data.csv",
                        "content": csv_content
                    })
                    print("Response:", result)
                except Exception as e:
                    print(f"Error creating CSV file: {str(e)}")
                
                # Test 2: Get CSV file info
                print("\n2. Getting CSV file info:")
                try:
                    result = await session.call_tool("get_file_info", {"path": "test_data.csv"})
                    print("Response:", result)
                except Exception as e:
                    print(f"Error getting file info: {str(e)}")
                
                # Test 3: Read the CSV file
                print("\n3. Reading CSV file:")
                try:
                    result = await session.call_tool("read_file", {"path": "test_data.csv"})
                    print("Response:", result)
                except Exception as e:
                    print(f"Error reading file: {str(e)}")
                
                # Test 4: Edit CSV file with dry run
                print("\n4. Editing CSV file (dry run):")
                try:
                    result = await session.call_tool("edit_file", {
                        "path": "test_data.csv",
                        "edits": [
                            {
                                "oldText": "Bob,35,Paris",
                                "newText": "Bob,36,Paris"
                            }
                        ],
                        "dryRun": True
                    })
                    print("Response (dry run):", result)
                except Exception as e:
                    print(f"Error editing file (dry run): {str(e)}")
                
                # Test 5: Edit CSV file for real
                print("\n5. Editing CSV file (actual changes):")
                try:
                    result = await session.call_tool("edit_file", {
                        "path": "test_data.csv",
                        "edits": [
                            {
                                "oldText": "Bob,35,Paris",
                                "newText": "Bob,36,Paris"
                            }
                        ],
                        "dryRun": False
                    })
                    print("Response (actual changes):", result)
                except Exception as e:
                    print(f"Error editing file: {str(e)}")
                
                # Test 6: Add new row to CSV
                print("\n6. Adding new row to CSV:")
                try:
                    result = await session.call_tool("edit_file", {
                        "path": "test_data.csv",
                        "edits": [
                            {
                                "oldText": "Bob,36,Paris",
                                "newText": "Bob,36,Paris\nCharlie,28,Berlin"
                            }
                        ],
                        "dryRun": False
                    })
                    print("Response:", result)
                except Exception as e:
                    print(f"Error adding new row: {str(e)}")
                
                # Test 7: Update multiple rows
                print("\n7. Updating multiple rows:")
                try:
                    result = await session.call_tool("edit_file", {
                        "path": "test_data.csv",
                        "edits": [
                            {
                                "oldText": "John,30,New York",
                                "newText": "John,31,New York"
                            },
                            {
                                "oldText": "Alice,25,London",
                                "newText": "Alice,26,London"
                            }
                        ],
                        "dryRun": False
                    })
                    print("Response:", result)
                except Exception as e:
                    print(f"Error updating rows: {str(e)}")
                
                # Test 8: Search for CSV files
                print("\n8. Searching for CSV files:")
                try:
                    result = await session.call_tool("search_files", {
                        "path": ".",
                        "pattern": ".csv",
                        "excludePatterns": ["__pycache__"]
                    })
                    print("Response:", result)
                except Exception as e:
                    print(f"Error searching files: {str(e)}")
                
                # Test 9: Create backup of CSV
                print("\n9. Creating backup of CSV:")
                try:
                    result = await session.call_tool("read_file", {"path": "test_data.csv"})
                    if result and hasattr(result, 'content'):
                        backup_result = await session.call_tool("write_file", {
                            "path": "test_data_backup.csv",
                            "content": result.content
                        })
                        print("Backup created successfully")
                except Exception as e:
                    print(f"Error creating backup: {str(e)}")
    
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
        loop.run_until_complete(test_csv_operations())
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