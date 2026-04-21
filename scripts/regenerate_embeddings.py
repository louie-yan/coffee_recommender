#!/usr/bin/env python3
"""
Regenerate all coffee embeddings
重新生成所有咖啡产品的向量索引（2048 维）
"""

import sys
import os
import logging
from typing import List, Dict, Any
from sqlalchemy import text
from datetime import datetime

# 添加项目路径
workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
sys.path.insert(0, workspace_path)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_db_session():
    """获取数据库会话"""
    from src.storage.database.db import get_engine
    from sqlalchemy.orm import sessionmaker
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def generate_embedding(text: str) -> List[float] | None:
    """生成文本的向量嵌入"""
    try:
        from coze_coding_dev_sdk import EmbeddingClient
        from coze_coding_utils.runtime_ctx.context import new_context
        
        ctx = new_context(method="regenerate_embeddings")
        client = EmbeddingClient()
        embedding = client.embed_text(text)
        return embedding
    except Exception as e:
        logger.error(f"生成 embedding 失败: {e}")
        return None


def store_product_embedding(coffee_id: int, product: Dict[str, Any]):
    """存储产品的向量嵌入"""
    try:
        # 构建用于检索的文本内容
        content_parts = [
            product.get('roaster_brand', ''),
            product.get('product_name', ''),
            product.get('bean_variety', ''),
            product.get('origin_country', ''),
            product.get('origin_region', ''),
            product.get('roast_level', ''),
            product.get('processing_method', ''),
        ]
        
        # 处理风味标签
        flavor_tags = product.get('flavor_tags', [])
        if flavor_tags:
            for tag in flavor_tags:
                content_parts.extend(tag.split())
        
        content_parts.append(product.get('tasting_notes', ''))

        search_text = ' '.join(filter(None, content_parts))

        # 生成向量
        embedding = generate_embedding(search_text)
        if not embedding:
            logger.warning(f"产品 {coffee_id} 生成 embedding 失败")
            return

        # 存储向量
        session = get_db_session()

        session.execute(
            text("""
                INSERT INTO coffee_embeddings (coffee_id, embedding, content, created_at)
                VALUES (:coffee_id, :embedding, :content, :created_at)
            """),
            {
                "coffee_id": coffee_id,
                "embedding": embedding,
                "content": search_text,
                "created_at": datetime.now()
            }
        )

        session.commit()
        session.close()

        logger.info(f"✓ 产品 {coffee_id} 向量存储成功（维度: {len(embedding)}）")

    except Exception as e:
        logger.error(f"✗ 存储产品向量失败: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()


def verify_and_recreate_vector_table():
    """验证并重建向量表，确保维度正确"""
    try:
        logger.info("验证向量表结构...")

        session = get_db_session()

        # 检查当前向量列的维度
        result = session.execute(
            text("""
                SELECT a.atttypmod as typmod
                FROM pg_attribute a
                JOIN pg_type t ON a.atttypid = t.oid
                WHERE a.attrelid = 'coffee_embeddings'::regclass
                AND a.attname = 'embedding'
            """)
        )
        row = result.fetchone()

        if row:
            current_dim = row[0]
            logger.info(f"当前向量列维度: {current_dim}")

            if current_dim != 2048:
                logger.warning(f"向量维度不匹配（需要 2048，当前 {current_dim}），重建表...")

                # 删除并重建表（不创建索引，暂时不支持 2000+ 维度的索引）
                session.execute(text("DROP TABLE IF EXISTS coffee_embeddings CASCADE"))
                session.execute(text("""
                    CREATE TABLE coffee_embeddings (
                        id SERIAL PRIMARY KEY,
                        coffee_id INTEGER REFERENCES coffee_products(id) ON DELETE CASCADE,
                        embedding vector(2048),
                        content TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))

                # 普通索引
                session.execute(text("""
                    CREATE INDEX idx_coffee_embeddings_coffee_id 
                    ON coffee_embeddings(coffee_id)
                """))

                session.commit()
                logger.info("向量表已重建为 2048 维（注意：由于 pgvector 限制，暂时不创建向量索引）")

        session.close()

    except Exception as e:
        logger.error(f"验证向量表失败: {e}")
        if 'session' in locals():
            session.close()
        raise


def main():
    """主函数"""
    try:
        logger.info("=" * 60)
        logger.info("开始重新生成所有产品向量（2048 维）...")
        logger.info("=" * 60)

        # 验证并重建向量表
        verify_and_recreate_vector_table()

        # 获取所有产品
        session = get_db_session()
        result = session.execute(
            text("""
                SELECT id, roaster_brand, product_name, bean_variety,
                       origin_country, origin_region, altitude,
                       roast_level, processing_method, flavor_tags,
                       tasting_notes, brew_suggestions, price_range
                FROM coffee_products
                WHERE is_active = true
            """)
        )
        rows = result.fetchall()
        session.close()

        if not rows:
            logger.warning("数据库中没有活跃的产品。")
            return

        logger.info(f"找到 {len(rows)} 个产品")
        logger.info("-" * 60)

        # 为每个产品生成并存储向量
        success_count = 0
        for i, row in enumerate(rows, 1):
            logger.info(f"[{i}/{len(rows)}] 处理产品: {row[2]}...")
            
            product = {
                'id': row[0],
                'roaster_brand': row[1],
                'product_name': row[2],
                'bean_variety': row[3],
                'origin_country': row[4],
                'origin_region': row[5],
                'altitude': row[6],
                'roast_level': row[7],
                'processing_method': row[8],
                'flavor_tags': row[9] if row[9] else [],
                'tasting_notes': row[10],
                'brew_suggestions': row[11],
                'price_range': row[12]
            }
            
            store_product_embedding(product['id'], product)
            success_count += 1

        logger.info("=" * 60)
        logger.info(f"✅ 成功生成 {success_count} 个产品的向量索引（2048 维）")
        logger.info("=" * 60)

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ 重新生成向量失败: {e}")
        logger.error("=" * 60)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
