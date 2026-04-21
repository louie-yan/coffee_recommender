"""
Coffee Product Recommender Tool
基于用户喜好向量检索匹配的咖啡产品
"""

from langchain.tools import tool
from typing import Optional, List, Dict, Any
import logging
import json
from sqlalchemy import text

logger = logging.getLogger(__name__)

# 数据库连接
from storage.database.db import get_engine

# Embedding 客户端（用于向量检索）
from coze_coding_dev_sdk import EmbeddingClient
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context


def get_db_session():
    """获取数据库会话"""
    engine = get_engine()
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    return Session()


def generate_query_vector(query_text: str) -> Optional[List[float]]:
    """生成查询文本的向量嵌入"""
    try:
        ctx = request_context.get() or new_context(method="coffee_recommender")
        client = EmbeddingClient()
        embedding = client.embed_text(query_text)
        return embedding
    except Exception as e:
        logger.error(f"生成查询向量失败: {e}")
        return None


def vector_search_products(
    query_text: str,
    filters: Dict[str, Optional[str]],
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    使用向量相似度搜索咖啡产品

    Args:
        query_text: 查询文本（用户喜好）
        filters: 过滤条件
        top_k: 返回结果数量

    Returns:
        List[Dict]: 匹配的产品列表
    """
    try:
        # 检查是否有向量数据
        session = get_db_session()
        result = session.execute(
            text("SELECT COUNT(*) FROM coffee_embeddings")
        )
        embedding_count = result.scalar()
        session.close()

        if embedding_count == 0:
            logger.info("向量索引为空，使用关键词匹配")
            return keyword_search_products(query_text, filters, top_k)

        # 生成查询向量
        query_embedding = generate_query_vector(query_text)
        if not query_embedding:
            logger.warning("生成查询向量失败，使用关键词匹配")
            return keyword_search_products(query_text, filters, top_k)

        # 构建向量相似度查询
        session = get_db_session()

        # 基础查询
        where_clauses = ["ce.content IS NOT NULL"]
        params = {
            "query_embedding": query_embedding,
            "limit_count": top_k
        }

        # 添加过滤条件
        if filters.get('roast_level'):
            where_clauses.append("cp.roast_level = :roast_level")
            params['roast_level'] = filters['roast_level']

        if filters.get('origin'):
            where_clauses.append("cp.origin_country = :origin")
            params['origin'] = filters['origin']

        if filters.get('processing_method'):
            where_clauses.append("cp.processing_method = :processing_method")
            params['processing_method'] = filters['processing_method']

        where_sql = " AND ".join(where_clauses)

        # 执行向量相似度搜索
        query = f"""
            SELECT
                cp.id,
                cp.roaster_brand,
                cp.product_name,
                cp.bean_variety,
                cp.origin_country,
                cp.origin_region,
                cp.altitude,
                cp.roast_level,
                cp.processing_method,
                cp.flavor_tags,
                cp.tasting_notes,
                cp.brew_suggestions,
                cp.price_range,
                cp.source_url,
                1 - (ce.embedding <=> :query_embedding) as similarity
            FROM coffee_embeddings ce
            JOIN coffee_products cp ON ce.coffee_id = cp.id
            WHERE {where_sql}
            ORDER BY ce.embedding <=> :query_embedding
            LIMIT :limit_count
        """

        result = session.execute(text(query), params)
        rows = result.fetchall()

        # 转换为字典列表
        products = []
        for row in rows:
            products.append({
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
                'price_range': row[12],
                'source_url': row[13],
                'similarity_score': float(row[14]) if row[14] else 0.0
            })

        session.close()
        return products

    except Exception as e:
        logger.error(f"向量搜索失败: {e}")
        # 降级到关键词搜索
        return keyword_search_products(query_text, filters, top_k)


def keyword_search_products(
    query_text: str,
    filters: Dict[str, Optional[str]],
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    使用关键词匹配搜索咖啡产品（后备方案）

    Args:
        query_text: 查询文本（用户喜好）
        filters: 过滤条件
        top_k: 返回结果数量

    Returns:
        List[Dict]: 匹配的产品列表
    """
    try:
        session = get_db_session()

        # 构建基础查询
        where_clauses = ["cp.is_active = true"]
        params = {"limit_count": top_k}

        # 添加文本搜索条件
        if query_text:
            where_clauses.append("""
                (
                    cp.roaster_brand ILIKE :query
                    OR cp.product_name ILIKE :query
                    OR cp.tasting_notes ILIKE :query
                    OR array_to_string(cp.flavor_tags, ' ') ILIKE :query
                )
            """)
            params['query'] = f"%{query_text}%"

        # 添加过滤条件
        if filters.get('roast_level'):
            where_clauses.append("cp.roast_level = :roast_level")
            params['roast_level'] = filters['roast_level']

        if filters.get('origin'):
            where_clauses.append("cp.origin_country = :origin")
            params['origin'] = filters['origin']

        if filters.get('processing_method'):
            where_clauses.append("cp.processing_method = :processing_method")
            params['processing_method'] = filters['processing_method']

        where_sql = " AND ".join(where_clauses)

        # 执行查询
        query = f"""
            SELECT
                cp.id,
                cp.roaster_brand,
                cp.product_name,
                cp.bean_variety,
                cp.origin_country,
                cp.origin_region,
                cp.altitude,
                cp.roast_level,
                cp.processing_method,
                cp.flavor_tags,
                cp.tasting_notes,
                cp.brew_suggestions,
                cp.price_range,
                cp.source_url,
                1.0 as similarity_score
            FROM coffee_products cp
            WHERE {where_sql}
            ORDER BY cp.update_date DESC
            LIMIT :limit_count
        """

        result = session.execute(text(query), params)
        rows = result.fetchall()

        # 转换为字典列表
        products = []
        for row in rows:
            products.append({
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
                'price_range': row[12],
                'source_url': row[13],
                'similarity_score': float(row[14]) if row[14] else 0.0
            })

        session.close()
        return products

    except Exception as e:
        logger.error(f"关键词搜索失败: {e}")
        return []


def calculate_match_score(
    product: Dict[str, Any],
    user_preferences: Dict[str, Any]
) -> float:
    """
    计算产品与用户喜好的匹配分数

    Args:
        product: 产品信息
        user_preferences: 用户偏好

    Returns:
        float: 匹配分数 (0.0 - 1.0)
    """
    score = 0.0
    weights = {
        'flavor_preference': 0.4,
        'roast_level': 0.2,
        'origin': 0.15,
        'processing_method': 0.15,
        'price_range': 0.1
    }

    # 1. 风味偏好匹配
    flavor_pref = user_preferences.get('flavor_preference', '').lower()
    if flavor_pref:
        # flavor_tags 可能是包含空格的字符串数组，需要转换为字符串列表
        flavor_tags_list = []
        if product.get('flavor_tags'):
            for tag in product['flavor_tags']:
                # 将每个标签按空格分割
                flavor_tags_list.extend(tag.split())

        flavor_tags = [tag.lower() for tag in flavor_tags_list]
        tasting_notes = product.get('tasting_notes', '').lower()
        product_name = product.get('product_name', '').lower()

        # 检查风味关键词
        keywords = flavor_pref.split()
        match_count = 0
        for keyword in keywords:
            if keyword in flavor_tags or keyword in tasting_notes or keyword in product_name:
                match_count += 1

        flavor_score = match_count / len(keywords) if keywords else 0
        score += flavor_score * weights['flavor_preference']

    # 2. 烘焙度匹配
    if user_preferences.get('roast_level'):
        if product.get('roast_level', '').lower() == user_preferences['roast_level'].lower():
            score += weights['roast_level']
        # 部分匹配（如 Medium-Light 匹配 Light）
        elif user_preferences['roast_level'].lower() in product.get('roast_level', '').lower():
            score += weights['roast_level'] * 0.5

    # 3. 产地匹配
    if user_preferences.get('origin'):
        if product.get('origin_country', '').lower() == user_preferences['origin'].lower():
            score += weights['origin']

    # 4. 处理法匹配
    if user_preferences.get('processing_method'):
        if product.get('processing_method', '').lower() == user_preferences['processing_method'].lower():
            score += weights['processing_method']

    # 5. 价格匹配（简单匹配）
    price_range = user_preferences.get('price_range', '')
    product_price = product.get('price_range', '')

    if price_range and product_price:
        # 提取数字进行简单比较
        import re
        price_match = re.search(r'(\d+)', product_price)
        user_price_match = re.search(r'(\d+)', price_range)

        if price_match and user_price_match:
            product_price_num = int(price_match.group(1))
            user_price_num = int(user_price_match.group(1))

            # 价格在合理范围内
            if abs(product_price_num - user_price_num) <= 20:
                score += weights['price_range']
            elif abs(product_price_num - user_price_num) <= 50:
                score += weights['price_range'] * 0.5

    # 6. 加入向量相似度分数（如果有）
    if product.get('similarity_score'):
        score = score * 0.7 + product['similarity_score'] * 0.3

    return min(score, 1.0)


@tool
def search_coffee_products(
    flavor_preference: str,
    roast_level: Optional[str] = None,
    origin: Optional[str] = None,
    processing_method: Optional[str] = None,
    price_range: Optional[str] = None
) -> str:
    """
    基于用户喜好向量检索匹配的咖啡产品

    Args:
        flavor_preference: 风味偏好（如：花香、果香、坚果等）
        roast_level: 烘焙度（Light/Medium/Dark）
        origin: 产地国家（如：Ethiopia、Colombia等）
        processing_method: 处理法（Washed/Natural/Honey）
        price_range: 价格区间（如：50-80元）

    Returns:
        str: TOP 1 最匹配产品的 JSON 格式字符串
    """
    try:
        logger.info(f"搜索咖啡产品: {flavor_preference}")

        # 构建查询文本
        query_parts = [flavor_preference]
        if roast_level:
            query_parts.append(roast_level)
        if origin:
            query_parts.append(origin)
        if processing_method:
            query_parts.append(processing_method)
        query_text = " ".join(query_parts)

        # 构建过滤条件
        filters = {
            'roast_level': roast_level,
            'origin': origin,
            'processing_method': processing_method
        }

        # 搜索产品（优先向量检索，降级到关键词搜索）
        products = vector_search_products(query_text, filters, top_k=5)

        # 如果没有找到结果，尝试放宽搜索条件（不使用文本搜索，只用过滤条件）
        if not products:
            logger.info("未找到匹配产品，尝试放宽搜索条件")
            relaxed_filters = {
                'roast_level': roast_level,
                'origin': origin,
                'processing_method': processing_method
            }
            # 使用空查询文本，只应用过滤条件
            products = vector_search_products("", relaxed_filters, top_k=5)

        # 如果还是没有结果，返回提示
        if not products:
            return json.dumps({
                "status": "not_found",
                "message": "未找到匹配的咖啡产品",
                "suggestions": [
                    "尝试调整风味偏好描述（如：茉莉花、柑橘、黑醋栗等具体风味）",
                    "放宽其他过滤条件",
                    "检查数据库是否有足够的产品数据"
                ]
            }, ensure_ascii=False, indent=2)

        # 计算匹配分数并排序
        user_preferences = {
            'flavor_preference': flavor_preference,
            'roast_level': roast_level,
            'origin': origin,
            'processing_method': processing_method,
            'price_range': price_range
        }

        for product in products:
            product['match_score'] = calculate_match_score(product, user_preferences)

        # 按匹配分数排序
        products.sort(key=lambda x: x['match_score'], reverse=True)

        # 获取 TOP 1 产品
        top_product = products[0]

        # 移除不需要返回的字段
        result_product = {
            'id': top_product.get('id'),
            'roaster_brand': top_product.get('roaster_brand'),
            'product_name': top_product.get('product_name'),
            'bean_variety': top_product.get('bean_variety'),
            'origin_country': top_product.get('origin_country'),
            'origin_region': top_product.get('origin_region'),
            'altitude': top_product.get('altitude'),
            'roast_level': top_product.get('roast_level'),
            'processing_method': top_product.get('processing_method'),
            'flavor_tags': top_product.get('flavor_tags', []),
            'tasting_notes': top_product.get('tasting_notes'),
            'brew_suggestions': top_product.get('brew_suggestions'),
            'price_range': top_product.get('price_range'),
            'source_url': top_product.get('source_url'),
            'match_score': round(top_product.get('match_score', 0), 3),
            'similarity_score': round(top_product.get('similarity_score', 0), 3)
        }

        logger.info(f"推荐产品: {result_product['product_name']} (匹配分数: {result_product['match_score']})")

        return json.dumps({
            "status": "success",
            "product": result_product,
            "total_candidates": len(products),
            "message": f"为您找到最匹配的咖啡产品：{result_product['product_name']}"
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"搜索咖啡产品失败: {e}")
        return json.dumps({
            "status": "error",
            "message": f"搜索失败: {str(e)}",
            "suggestions": [
                "请检查输入参数是否正确",
                "稍后重试或联系技术支持"
            ]
        }, ensure_ascii=False, indent=2)
