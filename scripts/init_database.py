#!/usr/bin/env python3
"""
Database Initialization Script
初始化数据库表结构，确保向量维度正确
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


def init_database():
    """初始化数据库表结构"""
    try:
        from src.storage.database.db import get_engine
        from sqlalchemy import text

        logger.info("=" * 60)
        logger.info("开始初始化数据库...")
        logger.info("=" * 60)

        engine = get_engine()

        with engine.begin() as conn:
            # 1. 创建 coffee_products 表（如果不存在）
            logger.info("检查/创建 coffee_products 表...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS coffee_products (
                    id SERIAL PRIMARY KEY,
                    roaster_brand VARCHAR(255),
                    product_name VARCHAR(500),
                    bean_variety VARCHAR(255),
                    origin_country VARCHAR(100),
                    origin_region VARCHAR(100),
                    altitude VARCHAR(50),
                    roast_level VARCHAR(50),
                    processing_method VARCHAR(50),
                    flavor_tags TEXT[],
                    tasting_notes TEXT,
                    brew_suggestions JSONB,
                    price_range VARCHAR(100),
                    source_url TEXT,
                    image_url TEXT,
                    is_active BOOLEAN DEFAULT true,
                    update_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            logger.info("✓ coffee_products 表已就绪")

            # 2. 创建 brewing_knowledge 表（如果不存在）
            logger.info("检查/创建 brewing_knowledge 表...")
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS brewing_knowledge (
                    id SERIAL PRIMARY KEY,
                    knowledge_type VARCHAR(100),
                    variety VARCHAR(255),
                    processing_method VARCHAR(50),
                    roast_level VARCHAR(50),
                    origin VARCHAR(100),
                    equipment_type VARCHAR(100),
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            logger.info("✓ brewing_knowledge 表已就绪")

            # 3. 检查 coffee_embeddings 表的维度
            logger.info("检查 coffee_embeddings 表...")
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'coffee_embeddings'
                )
            """))
            table_exists = result.scalar()

            if table_exists:
                # 检查现有表的向量维度
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

                    if current_dim != 2048:
                        logger.warning(f"向量维度不匹配（需要 2048，当前 {current_dim}），重建表...")
                        conn.execute(text("DROP TABLE IF EXISTS coffee_embeddings CASCADE"))
                        table_exists = False

            # 4. 创建 coffee_embeddings 表（确保为 2048 维）
            if not table_exists:
                logger.info("创建 coffee_embeddings 表（2048 维）...")
                conn.execute(text("""
                    CREATE TABLE coffee_embeddings (
                        id SERIAL PRIMARY KEY,
                        coffee_id INTEGER REFERENCES coffee_products(id) ON DELETE CASCADE,
                        embedding vector(2048),
                        content TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))

                # 创建索引（不创建向量索引，因为 pgvector 对 2048 维的支持有限）
                conn.execute(text("""
                    CREATE INDEX idx_coffee_embeddings_coffee_id
                    ON coffee_embeddings(coffee_id)
                """))
                conn.execute(text("""
                    CREATE INDEX idx_coffee_embeddings_created_at
                    ON coffee_embeddings(created_at)
                """))

                logger.info("✓ coffee_embeddings 表已创建（2048 维）")
            else:
                logger.info("✓ coffee_embeddings 表已存在且维度正确")

            logger.info("=" * 60)
            logger.info("✅ 数据库初始化完成")
            logger.info("=" * 60)

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ 数据库初始化失败: {e}")
        logger.error("=" * 60)
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    init_database()
