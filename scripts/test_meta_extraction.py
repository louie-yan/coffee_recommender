#!/usr/bin/env python3
"""
测试 Meta 描述提取功能
验证爬虫能否从 Meta 描述中提取完整的咖啡信息
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tools.coffee.coffee_updater import scrape_product_detail, extract_coffee_info_from_description

def test_meta_description_extraction():
    """测试 Meta 描述提取"""
    print("=" * 80)
    print("测试 Meta 描述提取功能")
    print("=" * 80)

    # 测试 URL
    test_url = "https://specialitycoffee.ca/product/yirgacheffe-74110-74112-natural/"

    # 模拟浏览器头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    print(f"\n测试 URL: {test_url}")
    print("-" * 80)

    # 提取产品详情
    product_info = scrape_product_detail(test_url, headers, "https://specialitycoffee.ca/")

    if product_info:
        print("\n✅ 成功提取产品信息！")
        print("\n产品名称:", product_info.get('product_name'))
        print("品牌:", product_info.get('roaster_brand'))
        print("价格:", product_info.get('price_range'))
        print("描述摘要:", (product_info.get('tasting_notes') or '')[:200] + '...' if product_info.get('tasting_notes') else '无')

        print("\n--- 结构化信息 ---")
        print("国家:", product_info.get('origin_country'))
        print("产区:", product_info.get('origin_region'))
        print("处理法:", product_info.get('processing_method'))
        print("豆种:", product_info.get('bean_variety'))
        print("风味标签:", product_info.get('flavor_tags', []))

        # 验证关键字段
        print("\n--- 验证结果 ---")
        checks = {
            '产品名称': product_info.get('product_name') is not None,
            '描述信息': product_info.get('tasting_notes') is not None and len(product_info['tasting_notes']) > 50,
            '国家': product_info.get('origin_country') is not None,
            '处理法': product_info.get('processing_method') is not None,
            '豆种': product_info.get('bean_variety') is not None,
            '风味标签': len(product_info.get('flavor_tags', [])) > 0
        }

        all_passed = True
        for field, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {field}")
            if not passed:
                all_passed = False

        print("\n" + "=" * 80)
        if all_passed:
            print("✅ 所有字段验证通过！Meta 描述提取功能正常。")
        else:
            print("❌ 部分字段验证失败，需要进一步优化。")
        print("=" * 80)

        return all_passed
    else:
        print("\n❌ 未能提取产品信息")
        print("=" * 80)
        return False


def test_direct_extraction():
    """测试直接从描述文本提取信息"""
    print("\n" + "=" * 80)
    print("测试描述文本解析功能")
    print("=" * 80)

    # 模拟 Meta 描述文本
    sample_description = "Yirgacheffe 74110 & 74112 Natural. 100% Heirloom. From Ethiopia, Yirgacheffe region. Natural process. Flavor notes: rambutan, mango, blueberry and sweet floral aroma."

    print(f"\n测试描述文本:\n{sample_description}")
    print("-" * 80)

    extracted = extract_coffee_info_from_description(sample_description, "Yirgacheffe 74110 & 74112 Natural")

    print("\n提取结果:")
    print("国家:", extracted.get('origin_country'))
    print("产区:", extracted.get('origin_region'))
    print("处理法:", extracted.get('processing_method'))
    print("豆种:", extracted.get('bean_variety'))
    print("风味标签:", extracted.get('flavor_tags', []))

    # 验证
    print("\n--- 验证结果 ---")
    expected = {
        'origin_country': 'Ethiopia',
        'origin_region': 'Yirgacheffe',
        'processing_method': 'Natural',
        'bean_variety': '74110 & 74112'
    }

    all_passed = True
    for field, expected_value in expected.items():
        actual_value = extracted.get(field)
        if expected_value.lower() in str(actual_value).lower():
            print(f"✅ {field}: {actual_value}")
        else:
            print(f"❌ {field}: 期望 '{expected_value}', 实际 '{actual_value}'")
            all_passed = False

    print("=" * 80)
    return all_passed


if __name__ == '__main__':
    # 测试 1: 直接文本解析
    test1_passed = test_direct_extraction()

    # 测试 2: 实际网页爬取
    test2_passed = test_meta_description_extraction()

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"测试 1 (文本解析): {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"测试 2 (网页爬取): {'✅ 通过' if test2_passed else '❌ 失败'}")
    print("=" * 80)
