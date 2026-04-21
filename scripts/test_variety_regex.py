#!/usr/bin/env python3
"""
调试豆种提取逻辑
"""

import re

# 实际描述文本
description = "Apollon's Gold Chechele Ethiopia natural coffee from Yirgacheffe with rambutan, mango and blueberry notes. Varieties 74110 & 74112."

print("原始描述:", description)
print()

# 测试不同的正则表达式
patterns = [
    (r'\b(74\d{2})\b', '单数字模式'),
    (r'(?:variety|varieties|variety:|varieties:)\s*(?:[\w\s]*?)(\d{5})', 'Variety 后跟数字'),
    (r'(\d{5})', '任意5位数字'),
    (r'(?:[^a-z]|^)(741\d{2})(?:[^a-z]|$)', '精确匹配741xx'),
]

for pattern, desc in patterns:
    match = re.search(pattern, description, re.IGNORECASE)
    if match:
        print(f"✅ {desc}: {pattern}")
        print(f"   匹配结果: {match.groups()}")
        # 查找所有匹配
        all_matches = re.findall(pattern, description, re.IGNORECASE)
        print(f"   所有匹配: {all_matches}")
    else:
        print(f"❌ {desc}: {pattern}")
    print()

# 尝试更复杂的模式
print("测试更复杂的模式:")
match = re.search(r'Varieties?\s*[:&]?\s*(\d{5})', description, re.IGNORECASE)
if match:
    print(f"匹配成功: {match.groups()}")
else:
    print("匹配失败")

# 尝试使用 lookahead/lookbehind
print()
print("测试查找所有5位数字:")
numbers = re.findall(r'\b\d{5}\b', description)
print(f"找到的数字: {numbers}")
