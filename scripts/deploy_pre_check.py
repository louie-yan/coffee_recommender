#!/usr/bin/env python3
"""
Deploy Pre-check Script
部署前检查脚本，确保数据库表结构正确
"""

import sys
import os
import logging

# 添加项目路径
workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
sys.path.insert(0, workspace_path)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_database_schema():
    """检查数据库表结构"""
    try:
        from src.storage.database.db import get_engine
        from sqlalchemy import text

        logger.info("检查数据库表结构...")

        engine = get_engine()

        with engine.begin() as conn:
            # 1. 检查 coffee_embeddings 表是否存在
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'coffee_embeddings'
                )
            """))
            table_exists = result.scalar()

            if not table_exists:
                logger.warning("coffee_embeddings 表不存在，跳过检查")
                return True

            # 2. 检查向量维度
            result = conn.execute(text("""
                SELECT a.atttypmod as typmod
                FROM pg_attribute a
                JOIN pg_type t ON a.atttypid = t.oid
                WHERE a.attrelid = 'coffee_embeddings'::regclass
                AND a.attname = 'embedding'
            """))
            row = result.fetchone()

            if not row:
                logger.error("无法获取向量维度信息")
                return False

            current_dim = row[0]
            expected_dim = 2048

            if current_dim != expected_dim:
                logger.error(f"向量维度不匹配！")
                logger.error(f"  期望: {expected_dim} 维")
                logger.error(f"  当前: {current_dim} 维")
                logger.error("")
                logger.error("请运行以下命令修复:")
                logger.error("  python scripts/fix_vector_dimension.py")
                logger.error("  python scripts/regenerate_embeddings.py")
                return False

            logger.info(f"✓ 向量维度正确: {current_dim} 维")

            # 3. 检查向量数据数量
            result = conn.execute(text("""
                SELECT COUNT(*) FROM coffee_embeddings
            """))
            count = result.scalar()
            logger.info(f"✓ 向量数据数量: {count} 条")

            # 4. 检查产品数据数量
            result = conn.execute(text("""
                SELECT COUNT(*) FROM coffee_products WHERE is_active = true
            """))
            product_count = result.scalar()
            logger.info(f"✓ 产品数据数量: {product_count} 条")

            if count < product_count:
                logger.warning(f"⚠ 向量数据 ({count}) 少于产品数据 ({product_count})")
                logger.warning("建议运行: python scripts/regenerate_embeddings.py")

        logger.info("✅ 数据库表结构检查通过")
        return True

    except Exception as e:
        logger.error(f"数据库检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = check_database_schema()
    sys.exit(0 if success else 1)
