#!/usr/bin/env python3
"""
测试爬虫脚本 - 单独测试爬取逻辑
"""

import sys
import os

workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
sys.path.insert(0, workspace_path)
sys.path.insert(0, os.path.join(workspace_path, 'src'))

from tools.coffee.coffee_updater import scrape_coffee_products
from src.storage.database.db import get_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text


def get_db_session():
    """获取数据库会话"""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def main():
    """测试爬虫"""
    print("=" * 80)
    print("开始测试爬虫逻辑...")
    print("=" * 80)

    # 1. 测试爬取产品列表
    print("\n步骤1: 爬取产品列表...")
    products = scrape_coffee_products()

    if not products:
        print("❌ 未能获取到任何产品")
        return

    print(f"✅ 成功获取 {len(products)} 个产品")

    # 2. 显示产品信息
    print("\n" + "=" * 80)
    print("产品信息:")
    print("=" * 80)

    for idx, product in enumerate(products, 1):
        print(f"\n产品 {idx}:")
        print(f"  品牌: {product.get('roaster_brand')}")
        print(f"  名称: {product.get('product_name')}")
        print(f"  产地: {product.get('origin_country')}")
        print(f"  产区: {product.get('origin_region')}")
        print(f"  海拔: {product.get('altitude')}")
        print(f"  豆种: {product.get('bean_variety')}")
        print(f"  处理法: {product.get('processing_method')}")
        print(f"  烘焙度: {product.get('roast_level')}")
        print(f"  风味标签: {', '.join(product.get('flavor_tags', []))}")
        print(f"  价格: {product.get('price_range')}")
        print(f"  来源: {product.get('source_url')}")

    # 3. 查询当前数据库中的产品数量
    print("\n" + "=" * 80)
    print("数据库当前状态:")
    print("=" * 80)

    session = get_db_session()
    try:
        result = session.execute(text("SELECT COUNT(*) FROM coffee_products"))
        count = result.scalar()
        print(f"当前数据库中有 {count} 个产品")

        result = session.execute(text("""
            SELECT DISTINCT unnest(flavor_tags) as tag
            FROM coffee_products
            WHERE flavor_tags IS NOT NULL
        """))
        tags = [row[0] for row in result]
        print(f"当前数据库中有 {len(tags)} 个风味标签")

    except Exception as e:
        print(f"查询数据库失败: {e}")
    finally:
        session.close()

    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    main()
