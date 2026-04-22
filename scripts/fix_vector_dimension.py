#!/usr/bin/env python3
"""
Deploy Fix Script
修复部署时的向量维度不匹配问题
"""

import sys
import os
import logging

# 添加项目路径
workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
sys.path.insert(0, workspace_path)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fix_vector_dimension():
    """修复向量维度问题"""
    try:
        from src.storage.database.db import get_engine
        from sqlalchemy import text

        logger.info("=" * 60)
        logger.info("开始修复向量维度问题...")
        logger.info("=" * 60)

        engine = get_engine()

        with engine.begin() as conn:
            # 1. 检查当前向量维度
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'coffee_embeddings'
                )
            """))
            table_exists = result.scalar()

            if not table_exists:
                logger.info("coffee_embeddings 表不存在，跳过修复")
                return

            # 获取当前维度
            result = conn.execute(text("""
                SELECT a.atttypmod as typmod
                FROM pg_attribute a
                JOIN pg_type t ON a.atttypid = t.oid
                WHERE a.attrelid = 'coffee_embeddings'::regclass
                AND a.attname = 'embedding'
            """))
            row = result.fetchone()

            if row:
                current_dim = row[0]
                logger.info(f"当前向量维度: {current_dim}")

                if current_dim == 1536:
                    logger.warning("检测到 1536 维向量，需要清理并重建为 2048 维...")

                    # 清空表数据
                    logger.info("清空 coffee_embeddings 表数据...")
                    conn.execute(text("TRUNCATE TABLE coffee_embeddings CASCADE"))

                    # 删除表
                    logger.info("删除 coffee_embeddings 表...")
                    conn.execute(text("DROP TABLE IF EXISTS coffee_embeddings CASCADE"))

                    # 重新创建表（2048 维）
                    logger.info("重新创建 coffee_embeddings 表（2048 维）...")
                    conn.execute(text("""
                        CREATE TABLE coffee_embeddings (
                            id SERIAL PRIMARY KEY,
                            coffee_id INTEGER REFERENCES coffee_products(id) ON DELETE CASCADE,
                            embedding vector(2048),
                            content TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """))

                    # 创建索引
                    conn.execute(text("""
                        CREATE INDEX idx_coffee_embeddings_coffee_id
                        ON coffee_embeddings(coffee_id)
                    """))
                    conn.execute(text("""
                        CREATE INDEX idx_coffee_embeddings_created_at
                        ON coffee_embeddings(created_at)
                    """))

                    logger.info("✓ 表已重建为 2048 维")

                elif current_dim == 2048:
                    logger.info("✓ 向量维度正确（2048 维）")
                    # 清空旧数据，确保没有 1536 维的残留
                    logger.info("清空表数据...")
                    conn.execute(text("TRUNCATE TABLE coffee_embeddings CASCADE"))
                    logger.info("✓ 表数据已清空")

                else:
                    logger.warning(f"未知的向量维度: {current_dim}")
                    logger.info("清理并重建表...")
                    conn.execute(text("DROP TABLE IF EXISTS coffee_embeddings CASCADE"))
                    conn.execute(text("""
                        CREATE TABLE coffee_embeddings (
                            id SERIAL PRIMARY KEY,
                            coffee_id INTEGER REFERENCES coffee_products(id) ON DELETE CASCADE,
                            embedding vector(2048),
                            content TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    conn.execute(text("""
                        CREATE INDEX idx_coffee_embeddings_coffee_id
                        ON coffee_embeddings(coffee_id)
                    """))
                    logger.info("✓ 表已重建")

            logger.info("=" * 60)
            logger.info("✅ 向量维度修复完成")
            logger.info("=" * 60)
            logger.info("注意：向量数据已清空，需要重新生成")
            logger.info("请运行: python scripts/regenerate_embeddings.py")

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ 修复失败: {e}")
        logger.error("=" * 60)
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    fix_vector_dimension()
