#!/usr/bin/env python3
"""
测试 Meta 描述提取功能（使用真实URL）
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tools.coffee.coffee_updater import scrape_product_detail

def test_with_real_url():
    """使用真实 URL 测试"""
    print("=" * 80)
    print("测试 Meta 描述提取功能")
    print("=" * 80)

    # 真实的产品 URL
    test_url = "https://specialitycoffee.ca/product/apollons-gold-chechele-ethiopia-natural-74110-74112/"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    print(f"\n测试 URL: {test_url}")
    print("-" * 80)

    product_info = scrape_product_detail(test_url, headers, "https://specialitycoffee.ca/")

    if product_info:
        print("\n✅ 成功提取产品信息！")

        print("\n--- 基本信息 ---")
        print(f"产品名称: {product_info.get('product_name')}")
        print(f"品牌: {product_info.get('roaster_brand')}")
        print(f"价格: {product_info.get('price_range')}")
        print(f"产品链接: {product_info.get('source_url')}")

        print("\n--- 描述信息 ---")
        desc = product_info.get('tasting_notes') or ''
        print(f"描述（前300字符）: {desc[:300]}...")
        print(f"描述长度: {len(desc)} 字符")

        print("\n--- 结构化信息 ---")
        print(f"国家: {product_info.get('origin_country')}")
        print(f"产区: {product_info.get('origin_region')}")
        print(f"海拔: {product_info.get('altitude')}")
        print(f"处理法: {product_info.get('processing_method')}")
        print(f"豆种: {product_info.get('bean_variety')}")
        print(f"烘焙度: {product_info.get('roast_level')}")
        print(f"风味标签: {product_info.get('flavor_tags', [])}")

        # 验证关键字段
        print("\n--- 验证结果 ---")
        checks = {
            '产品名称': product_info.get('product_name') is not None,
            '描述信息': product_info.get('tasting_notes') is not None and len(product_info['tasting_notes']) > 50,
            '国家': product_info.get('origin_country') is not None,
            '产区': product_info.get('origin_region') is not None,
            '处理法': product_info.get('processing_method') is not None,
        }

        all_passed = True
        for field, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {field}")
            if not passed:
                all_passed = False

        print("\n" + "=" * 80)
        if all_passed:
            print("✅ 所有关键字段验证通过！")
        else:
            print("⚠️  部分字段验证失败，可能需要进一步优化提取逻辑。")
        print("=" * 80)

        return all_passed
    else:
        print("\n❌ 未能提取产品信息")
        print("=" * 80)
        return False


if __name__ == '__main__':
    success = test_with_real_url()
    sys.exit(0 if success else 1)
