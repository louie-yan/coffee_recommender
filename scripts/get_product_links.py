#!/usr/bin/env python3
"""
获取真实的产品列表和链接
"""

import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

url = "https://specialitycoffee.ca/product-category/filter/"

try:
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')

    # 查找所有产品链接
    product_links = []

    # 查找带有 product 类别的 a 标签
    for link in soup.find_all('a', href=True):
        href = link.get('href', '')
        if '/product/' in href and href not in [l[0] for l in product_links]:
            link_text = link.get_text(strip=True)
            if link_text:  # 只保存有文本的链接
                product_links.append((href, link_text))

    print(f"找到 {len(product_links)} 个产品链接：\n")
    for i, (href, text) in enumerate(product_links[:10], 1):
        print(f"{i}. {text}")
        print(f"   URL: {href}")
        print()

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
