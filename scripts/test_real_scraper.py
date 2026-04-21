#!/usr/bin/env python3
"""
直接测试爬虫，验证是否能从真实网站爬取数据
"""

import sys
import os
import json

workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
sys.path.insert(0, workspace_path)
sys.path.insert(0, os.path.join(workspace_path, 'src'))

def test_scraper():
    """测试爬虫"""
    from tools.coffee.coffee_updater import scrape_coffee_products

    print("=" * 80)
    print("开始测试爬虫...")
    print("目标网站: https://specialitycoffee.ca/product-category/filter/")
    print("=" * 80)

    try:
        # 爬取产品
        print("\n正在爬取产品列表...")
        products = scrape_coffee_products()

        if not products:
            print("❌ 未能获取到任何产品")
            print("可能原因：")
            print("  1. 网站无法访问")
            print("  2. 网站结构已改变")
            print("  3. 返回了示例数据（爬虫失败）")
            return

        print(f"✅ 成功获取 {len(products)} 个产品\n")

        # 显示每个产品的详细信息
        for idx, product in enumerate(products, 1):
            print("=" * 80)
            print(f"产品 {idx}: {product.get('product_name', 'Unknown')}")
            print("=" * 80)
            print(f"品牌: {product.get('roaster_brand')}")
            print(f"豆种: {product.get('bean_variety')}")
            print(f"产地: {product.get('origin_country')}")
            print(f"产区: {product.get('origin_region')}")
            print(f"海拔: {product.get('altitude')}")
            print(f"烘焙度: {product.get('roast_level')}")
            print(f"处理法: {product.get('processing_method')}")
            print(f"风味标签: {', '.join(product.get('flavor_tags', []))}")
            print(f"价格: {product.get('price_range')}")
            print(f"来源: {product.get('source_url')}")

            # 显示品尝笔记（前200字）
            tasting_notes = product.get('tasting_notes', '')
            if tasting_notes:
                preview = tasting_notes[:200] + "..." if len(tasting_notes) > 200 else tasting_notes
                print(f"品尝笔记: {preview}")
            print()

        # 验证数据质量
        print("=" * 80)
        print("数据质量验证")
        print("=" * 80)

        total_products = len(products)
        complete_products = 0
        products_with_flavor_tags = 0
        products_with_origin = 0
        products_with_price = 0

        for product in products:
            has_required_fields = (
                product.get('product_name') and
                product.get('roaster_brand') and
                product.get('price_range')
            )

            if has_required_fields:
                complete_products += 1

            if product.get('flavor_tags'):
                products_with_flavor_tags += 1

            if product.get('origin_country'):
                products_with_origin += 1

            if product.get('price_range'):
                products_with_price += 1

        print(f"总产品数: {total_products}")
        print(f"完整信息产品数: {complete_products} ({complete_products/total_products*100:.1f}%)")
        print(f"有风味标签的产品数: {products_with_flavor_tags} ({products_with_flavor_tags/total_products*100:.1f}%)")
        print(f"有产地信息的产品数: {products_with_origin} ({products_with_origin/total_products*100:.1f}%)")
        print(f"有价格信息的产品数: {products_with_price} ({products_with_price/total_products*100:.1f}%)")

        # 判断是否是示例数据
        print("\n" + "=" * 80)
        print("数据来源判断")
        print("=" * 80)

        # 检查是否是示例数据
        is_sample_data = False
        sample_keywords = ['明谦咖啡', '埃塞俄比亚耶加雪菲·花魁', '肯尼亚AA']

        for product in products:
            product_name = product.get('product_name', '').lower()
            if any(keyword.lower() in product_name for keyword in sample_keywords):
                is_sample_data = True
                break

            brand = product.get('roaster_brand', '').lower()
            if '明谦' in brand:
                is_sample_data = True
                break

        if is_sample_data:
            print("⚠️  检测到示例数据（爬虫可能失败，返回了备用的示例数据）")
        else:
            print("✅ 检测到真实爬取的数据")

        print("\n" + "=" * 80)
        print("测试完成")
        print("=" * 80)

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_scraper()
