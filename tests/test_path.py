#!/usr/bin/env python3
"""
測試不同格式的檔案路徑
"""

import os

# 測試不同的路徑格式
test_paths = [
    r"D:\Robert\ML\AI Agent related files\AI Ideas.xlsx",  # 原始路徑（反斜線）
    r"D:\Robert\ML\AI Agent related file\AI ideas.xlsx",   # 你提到的路徑
    "D:/Robert/ML/AI Agent related files/AI Ideas.xlsx",   # 正斜線格式
    "D:/Robert/ML/AI Agent related file/AI ideas.xlsx",    # 你提到的正斜線格式
    r"D:\Robert\ML\AI Agent related files\AI Ideas.xlsx",  # 原始路徑
]

print("測試不同格式的檔案路徑:")
print("=" * 50)

for i, path in enumerate(test_paths, 1):
    exists = os.path.exists(path)
    print(f"{i}. {path}")
    print(f"   存在: {exists}")
    if exists:
        try:
            size = os.path.getsize(path)
            print(f"   大小: {size} bytes")
        except Exception as e:
            print(f"   錯誤: {e}")
    print()

# 測試路徑正規化
print("路徑正規化測試:")
print("=" * 50)

for path in test_paths:
    normalized = os.path.normpath(path)
    print(f"原始: {path}")
    print(f"正規化: {normalized}")
    print(f"絕對路徑: {os.path.abspath(path)}")
    print() 