#!/usr/bin/env python3
"""
增强版产品详情爬取测试
"""

import sys
import os
import json

workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
sys.path.insert(0, workspace_path)


def test_extract_from_html():
    """测试从HTML中提取信息"""
    import requests
    from bs4 import BeautifulSoup

    url = "https://specialitycoffee.ca/product/apollons-gold-chechele-ethiopia-natural-74110-74112/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html',
    }

    print("=" * 80)
    print("测试提取产品详情")
    print("=" * 80)
    print(f"URL: {url}")
    print("=" * 80)

    response = requests.get(url, headers=headers, timeout=30)
    soup = BeautifulSoup(response.content, 'html.parser')

    # 1. 提取产品名称
    h1 = soup.find('h1')
    print(f"\n产品名称: {h1.get_text(strip=True) if h1 else '未找到'}")

    # 2. 提取价格
    price = soup.find('span', class_='woocommerce-Price-amount')
    print(f"价格: {price.get_text(strip=True) if price else '未找到'}")

    # 3. 提取meta描述
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc:
        desc = meta_desc.get('content', '')
        print(f"\nMeta描述: {desc}")

    # 4. 提取JSON-LD数据
    scripts = soup.find_all('script', type='application/ld+json')
    if scripts:
        print(f"\n找到 {len(scripts)} 个JSON-LD脚本")
        for idx, script in enumerate(scripts[:2]):  # 只显示前2个
            try:
                data = json.loads(script.string)
                print(f"\nJSON-LD #{idx+1}:")
                if isinstance(data, dict):
                    print(f"  类型: {data.get('@type')}")
                    print(f"  名称: {data.get('name')}")
                    print(f"  描述: {data.get('description', '')[:200]}")
                    
                    # 查找图片
                    if 'image' in data:
                        img = data['image']
                        if isinstance(img, dict):
                            print(f"  图片: {img.get('url', img.get('contentUrl'))}")
                        else:
                            print(f"  图片: {img}")
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            print(f"  - {item.get('@type')}: {item.get('name')}")
            except Exception as e:
                print(f"  解析失败: {e}")

    # 5. 查找产品描述区域
    desc_elements = [
        soup.find('div', class_='woocommerce-product-details__short-description'),
        soup.find('div', class_='product-description'),
        soup.find('div', {'id': 'tab-description'}),
        soup.find('div', class_='summary'),
    ]
    
    for elem in desc_elements:
        if elem:
            text = elem.get_text(strip=True)
            if len(text) > 50:
                print(f"\n找到描述 ({elem.get('class')}):")
                print(f"  {text[:300]}...")
                break

    # 6. 查找面包屑
    breadcrumbs = soup.find_all(class_='breadcrumb')
    if breadcrumbs:
        print(f"\n面包屑导航:")
        for bc in breadcrumbs[:1]:
            text = bc.get_text(strip=True)
            print(f"  {text}")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    test_extract_from_html()
