#!/usr/bin/env python3
"""
测试多个产品的 Meta 描述提取
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tools.coffee.coffee_updater import scrape_product_detail

def test_multiple_products():
    """测试多个产品"""
    test_urls = [
        "https://specialitycoffee.ca/product/apollons-gold-chechele-ethiopia-natural-74110-74112/",
        "https://specialitycoffee.ca/product/april-organic-kayon-mountain-ethiopia-natural-heirloom/",
        "https://specialitycoffee.ca/product/april-tadesse-espresso-ethiopia-krume-74158/",
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    results = []

    for i, url in enumerate(test_urls, 1):
        print(f"\n{'='*80}")
        print(f"测试产品 {i}/{len(test_urls)}")
        print(f"{'='*80}")
        print(f"URL: {url}")
        print("-" * 80)

        product_info = scrape_product_detail(url, headers, "https://specialitycoffee.ca/")

        if product_info:
            print("\n✅ 提取成功")
            print(f"产品名称: {product_info.get('product_name')}")
            print(f"描述: {product_info.get('tasting_notes', '')[:200]}...")
            print(f"国家: {product_info.get('origin_country')}")
            print(f"产区: {product_info.get('origin_region')}")
            print(f"处理法: {product_info.get('processing_method')}")
            print(f"豆种: {product_info.get('bean_variety')}")
            print(f"风味标签: {product_info.get('flavor_tags', [])}")

            # 检查关键字段
            success = all([
                product_info.get('product_name'),
                product_info.get('tasting_notes'),
                product_info.get('origin_country')
            ])

            results.append({
                'url': url,
                'success': success,
                'info': product_info
            })
        else:
            print("\n❌ 提取失败")
            results.append({
                'url': url,
                'success': False,
                'info': None
            })

    # 总结
    print(f"\n{'='*80}")
    print("测试总结")
    print(f"{'='*80}")
    successful = sum(1 for r in results if r['success'])
    print(f"成功: {successful}/{len(results)}")

    if successful == len(results):
        print("\n✅ 所有测试通过！Meta 描述提取功能正常。")
        return True
    else:
        print(f"\n⚠️  {len(results) - successful} 个测试失败")
        return False


if __name__ == '__main__':
    success = test_multiple_products()
    sys.exit(0 if success else 1)
