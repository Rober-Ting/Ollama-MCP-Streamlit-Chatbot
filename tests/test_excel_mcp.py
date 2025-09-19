#!/usr/bin/env python3
"""
測試 Excel MCP Server 的獨立腳本
"""

import asyncio
import os
from mcpclient_manager import MCPClientManager

async def test_excel_mcp():
    """測試 Excel MCP Server 連線和基本功能"""
    
    # 測試檔案路徑
    test_file = r"D:\Robert\ML\AI Agent related file\AI ideas.xlsx"
    
    print(f"測試 Excel MCP Server")
    print(f"測試檔案: {test_file}")
    print(f"檔案存在: {os.path.exists(test_file)}")
    
    if os.path.exists(test_file):
        print(f"檔案大小: {os.path.getsize(test_file)} bytes")
    
    try:
        print("\n1. 建立 MCP 連線...")
        async with MCPClientManager("excel") as client:
            print("✓ MCP 連線建立成功")
            
            print("\n2. 取得可用工具...")
            tools = await client.get_available_tools()
            print(f"✓ 找到 {len(tools)} 個工具:")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
            
            print("\n3. 測試 excel_describe_sheets 工具...")
            result = await client.call_tool("excel_describe_sheets", {
                "fileAbsolutePath": test_file
            })
            print(f"✓ 工具執行成功:")
            print(f"結果: {result}")
            
    except Exception as e:
        print(f"✗ 錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_excel_mcp()) 