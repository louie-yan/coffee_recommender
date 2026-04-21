#!/usr/bin/env python3
"""
简化版爬虫测试 - 只测试一个产品
"""

import sys
import os

workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
sys.path.insert(0, workspace_path)
sys.path.insert(0, os.path.join(workspace_path, 'src'))

def test_single_product():
    """测试爬取单个产品"""
    from tools.coffee.coffee_updater import scrape_product_detail
    from coze_coding_utils.log.write_log import request_context
    from coze_coding_utils.runtime_ctx.context import new_context

    # 设置测试URL
    test_url = "https://specialitycoffee.ca/product/apollons-gold-chechele-ethiopia-natural-74110-74112/"

    print("=" * 80)
    print("测试爬取单个产品")
    print("=" * 80)
    print(f"目标URL: {test_url}")
    print("=" * 80)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
    }

    try:
        print("\n正在爬取产品详情...")
        product_info = scrape_product_detail(test_url, headers, "https://specialitycoffee.ca")

        if product_info:
            print("\n✅ 成功获取产品信息\n")
            print(f"品牌: {product_info.get('roaster_brand')}")
            print(f"产品名称: {product_info.get('product_name')}")
            print(f"豆种: {product_info.get('bean_variety')}")
            print(f"产地: {product_info.get('origin_country')}")
            print(f"产区: {product_info.get('origin_region')}")
            print(f"海拔: {product_info.get('altitude')}")
            print(f"烘焙度: {product_info.get('roast_level')}")
            print(f"处理法: {product_info.get('processing_method')}")
            print(f"风味标签: {', '.join(product_info.get('flavor_tags', []))}")
            print(f"价格: {product_info.get('price_range')}")
            print(f"图片: {product_info.get('image_url')}")

            tasting_notes = product_info.get('tasting_notes', '')
            if tasting_notes:
                print(f"\n品尝笔记:")
                print(f"  {tasting_notes[:300]}{'...' if len(tasting_notes) > 300 else ''}")

            print(f"\n来源: {product_info.get('source_url')}")

            # 验证数据来源
            print("\n" + "=" * 80)
            print("数据来源验证")
            print("=" * 80)

            product_name = product_info.get('product_name', '')
            brand = product_info.get('roaster_brand', '')

            if '明谦' in brand or '埃塞俄比亚耶加雪菲' in product_name:
                print("⚠️  检测到示例数据")
            elif 'APOLLON' in product_name.upper() or 'Chechele' in product_name:
                print("✅ 检测到真实爬取的数据")
            else:
                print("⚠️  数据来源未知")

        else:
            print("❌ 未能获取产品信息")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    test_single_product()
