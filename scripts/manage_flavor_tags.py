#!/usr/bin/env python3
"""
批量添加/更新咖啡产品的风味标签
"""

import sys
import os
import argparse
from sqlalchemy import text

# 添加项目路径
workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
sys.path.insert(0, workspace_path)

from src.storage.database.db import get_engine
from sqlalchemy.orm import sessionmaker


def get_db_session():
    """获取数据库会话"""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def add_flavor_tags(product_id: int, new_tags: list):
    """
    为指定产品添加风味标签

    Args:
        product_id: 产品 ID
        new_tags: 要添加的风味标签列表
    """
    session = get_db_session()

    try:
        # 获取当前风味标签
        result = session.execute(
            text("SELECT flavor_tags FROM coffee_products WHERE id = :id"),
            {"id": product_id}
        )
        row = result.fetchone()

        if not row:
            print(f"❌ 产品 ID {product_id} 不存在")
            return

        current_tags = list(row[0]) if row[0] else []

        # 添加新标签（去重）
        updated_tags = list(set(current_tags + new_tags))

        # 更新数据库
        session.execute(
            text("UPDATE coffee_products SET flavor_tags = :tags WHERE id = :id"),
            {"tags": updated_tags, "id": product_id}
        )

        session.commit()

        print(f"✅ 产品 {product_id} 的风味标签已更新")
        print(f"   原标签: {current_tags}")
        print(f"   新标签: {updated_tags}")

    except Exception as e:
        session.rollback()
        print(f"❌ 更新失败: {e}")
    finally:
        session.close()


def remove_flavor_tags(product_id: int, tags_to_remove: list):
    """
    从指定产品移除风味标签

    Args:
        product_id: 产品 ID
        tags_to_remove: 要移除的风味标签列表
    """
    session = get_db_session()

    try:
        # 获取当前风味标签
        result = session.execute(
            text("SELECT flavor_tags FROM coffee_products WHERE id = :id"),
            {"id": product_id}
        )
        row = result.fetchone()

        if not row:
            print(f"❌ 产品 ID {product_id} 不存在")
            return

        current_tags = list(row[0]) if row[0] else []

        # 移除标签
        updated_tags = [tag for tag in current_tags if tag not in tags_to_remove]

        # 更新数据库
        session.execute(
            text("UPDATE coffee_products SET flavor_tags = :tags WHERE id = :id"),
            {"tags": updated_tags, "id": product_id}
        )

        session.commit()

        print(f"✅ 产品 {product_id} 的风味标签已更新")
        print(f"   原标签: {current_tags}")
        print(f"   新标签: {updated_tags}")

    except Exception as e:
        session.rollback()
        print(f"❌ 更新失败: {e}")
    finally:
        session.close()


def list_all_products():
    """列出所有产品及其风味标签"""
    session = get_db_session()

    try:
        result = session.execute(
            text("""
                SELECT id, roaster_brand, product_name, flavor_tags
                FROM coffee_products
                ORDER BY id
            """)
        )

        print("\n" + "=" * 80)
        print(f"{'ID':<5} {'品牌':<15} {'产品名称':<30} {'风味标签'}")
        print("=" * 80)

        for row in result:
            tags = ", ".join(row[3]) if row[3] else "无"
            print(f"{row[0]:<5} {row[1]:<15} {row[2]:<30} {tags}")

        print("=" * 80)

    except Exception as e:
        print(f"❌ 查询失败: {e}")
    finally:
        session.close()


def list_all_flavor_tags():
    """列出所有风味标签"""
    session = get_db_session()

    try:
        result = session.execute(
            text("""
                SELECT DISTINCT unnest(flavor_tags) as tag
                FROM coffee_products
                WHERE flavor_tags IS NOT NULL
                ORDER BY tag
            """)
        )

        tags = [row[0] for row in result]

        print("\n" + "=" * 60)
        print("所有风味标签:")
        print("=" * 60)
        for i, tag in enumerate(tags, 1):
            print(f"{i:3d}. {tag}")
        print("=" * 60)
        print(f"共 {len(tags)} 个风味标签\n")

    except Exception as e:
        print(f"❌ 查询失败: {e}")
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description='管理咖啡产品的风味标签')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # 添加标签
    add_parser = subparsers.add_parser('add', help='添加风味标签')
    add_parser.add_argument('--id', type=int, required=True, help='产品 ID')
    add_parser.add_argument('--tags', nargs='+', required=True, help='要添加的标签')

    # 移除标签
    remove_parser = subparsers.add_parser('remove', help='移除风味标签')
    remove_parser.add_argument('--id', type=int, required=True, help='产品 ID')
    remove_parser.add_argument('--tags', nargs='+', required=True, help='要移除的标签')

    # 列出所有产品
    subparsers.add_parser('list-products', help='列出所有产品')

    # 列出所有风味标签
    subparsers.add_parser('list-tags', help='列出所有风味标签')

    args = parser.parse_args()

    if args.command == 'add':
        add_flavor_tags(args.id, args.tags)
    elif args.command == 'remove':
        remove_flavor_tags(args.id, args.tags)
    elif args.command == 'list-products':
        list_all_products()
    elif args.command == 'list-tags':
        list_all_flavor_tags()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
