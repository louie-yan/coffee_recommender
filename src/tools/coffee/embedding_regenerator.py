"""
Regenerate Coffee Embeddings
重新生成所有咖啡产品的向量索引
"""

from langchain.tools import tool
from typing import List, Dict, Any
import logging
import json
from sqlalchemy import text
from datetime import datetime

logger = logging.getLogger(__name__)

# 数据库连接
from storage.database.db import get_engine

# Embedding 客户端
from coze_coding_dev_sdk import EmbeddingClient
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


def get_db_session():
    """获取数据库会话"""
    engine = get_engine()
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    return Session()


def generate_embedding(text: str) -> List[float] | None:
    """生成文本的向量嵌入"""
    try:
        ctx = request_context.get() or new_context(method="regenerate_embeddings")
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

        logger.info(f"产品 {coffee_id} 向量存储成功（维度: {len(embedding)}）")

    except Exception as e:
        logger.error(f"存储产品向量失败: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()


@tool
def regenerate_all_embeddings() -> str:
    """
    重新生成所有咖啡产品的向量索引

    该工具会：
    1. 读取数据库中的所有咖啡产品
    2. 为每个产品生成 2048 维向量
    3. 将向量存储到 coffee_embeddings 表

    Returns:
        str: 操作结果信息
    """
    try:
        logger.info("开始重新生成所有产品向量...")

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
            return "数据库中没有活跃的产品。"

        logger.info(f"找到 {len(rows)} 个产品")

        # 为每个产品生成并存储向量
        success_count = 0
        for row in rows:
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

        return f"✅ 成功生成 {success_count} 个产品的向量索引（2048 维）"

    except Exception as e:
        logger.error(f"重新生成向量失败: {e}")
        return f"❌ 重新生成向量失败: {str(e)}"
