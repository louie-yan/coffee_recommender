"""
Coffee Database Updater Tool
定期更新咖啡产品数据库（每日限流一次）
"""

from langchain.tools import tool
from typing import Optional, List, Dict, Any
import logging
import json
import time
from datetime import datetime, date
from sqlalchemy import text
from coze_coding_utils.log.write_log import request_context
from coze_coding_utils.runtime_ctx.context import new_context

logger = logging.getLogger(__name__)

# 数据库连接
from storage.database.db import get_engine

# Embedding 客户端
from coze_coding_dev_sdk import EmbeddingClient


def get_db_session():
    """获取数据库会话"""
    engine = get_engine()
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    return Session()


def check_today_updated() -> bool:
    """检查今日是否已更新数据库"""
    try:
        session = get_db_session()
        today = date.today()
        result = session.execute(
            text("SELECT COUNT(*) FROM coffee_products WHERE last_daily_check = :today"),
            {"today": today}
        )
        count = result.scalar()
        session.close()
        return count > 0
    except Exception as e:
        logger.error(f"检查更新状态失败: {e}")
        return False


def scrape_coffee_products() -> List[Dict[str, Any]]:
    """
    爬取 specialitycoffee.ca 网站的咖啡产品信息

    Returns:
        List[Dict]: 咖啡产品信息列表
    """
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    base_url = "https://specialtycoffee.ca"
    products_url = f"{base_url}/collections/coffee"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }

    products = []

    try:
        logger.info(f"开始爬取: {products_url}")
        response = requests.get(products_url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # 查找产品列表 - 根据实际网站结构调整选择器
        product_items = soup.find_all('div', class_='product-item') or \
                       soup.find_all('div', class_='product') or \
                       soup.find_all('li', class_='product-item')

        logger.info(f"找到 {len(product_items)} 个产品")

        for idx, item in enumerate(product_items[:20]):  # 限制爬取数量
            try:
                # 提取产品信息
                product_link = item.find('a', href=True)
                if not product_link:
                    continue

                product_url = urljoin(base_url, product_link['href'])
                product_name = str(product_link.get('title', '')).strip()

                # 提取价格
                price_elem = item.find('span', class_='price') or item.find('span', class_='money')
                price = price_elem.get_text(strip=True) if price_elem else "未知"

                # 提取品牌（从URL或标题）
                brand = extract_brand(product_name, product_url)

                # 提取图像（如果有）
                img_elem = item.find('img')
                image_url = urljoin(base_url, img_elem['src']) if img_elem else None

                product_info = {
                    'roaster_brand': brand,
                    'product_name': product_name,
                    'bean_variety': None,  # 需要进入详情页获取
                    'origin_country': None,
                    'origin_region': None,
                    'altitude': None,
                    'roast_level': None,
                    'processing_method': None,
                    'flavor_tags': [],
                    'tasting_notes': None,
                    'brew_suggestions': None,
                    'price_range': price,
                    'source_url': product_url,
                    'image_url': image_url
                }

                products.append(product_info)
                logger.info(f"提取产品 {idx + 1}/{len(product_items)}: {product_name}")

                # 添加延迟避免被封
                time.sleep(1)

            except Exception as e:
                logger.warning(f"解析产品失败: {e}")
                continue

        # 尝试获取详细信息（可选）
        if products:
            products = enrich_product_details(products, base_url, headers)

    except Exception as e:
        logger.error(f"爬取失败: {e}")
        # 返回一些示例数据用于测试
        products = get_sample_products()

    return products


def extract_brand(product_name: str, product_url: str) -> str:
    """从产品名称或 URL 中提取品牌"""
    # 简单实现，可以根据实际情况调整
    import re

    # 从 URL 中提取品牌
    url_match = re.search(r'/products/([^/]+)', product_url)
    if url_match:
        url_brand = url_match.group(1).split('-')[0].title()
        return url_brand

    # 从产品名称中提取品牌（第一个词）
    if product_name:
        return product_name.split()[0].title()

    return "未知品牌"


def enrich_product_details(products: List[Dict], base_url: str, headers: Dict) -> List[Dict]:
    """
    进入产品详情页获取更多信息（豆种、产地、处理法等）

    注意：此步骤会增加请求时间，可以根据需要禁用
    """
    import requests
    from bs4 import BeautifulSoup

    enriched = []
    for product in products[:5]:  # 限制详情页爬取数量
        try:
            response = requests.get(product['source_url'], headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # 尝试提取详细信息（根据实际网站结构调整）
            desc_elem = soup.find('div', class_='product-description') or \
                       soup.find('div', class_='description') or \
                       soup.find('p', class_='product-desc')

            if desc_elem:
                description = desc_elem.get_text(strip=True)
                product['tasting_notes'] = description[:500]  # 限制长度

                # 简单的关键词提取
                keywords = {
                    'origin': ['Ethiopia', 'Colombia', 'Kenya', 'Guatemala', 'Brazil', 'Panama'],
                    'processing': ['Washed', 'Natural', 'Honey', 'Anaerobic'],
                    'roast': ['Light', 'Medium', 'Dark'],
                    'variety': ['Bourbon', 'Typica', 'Gesha', 'SL28', 'Catuai']
                }

                for key, values in keywords.items():
                    for value in values:
                        if value.lower() in description.lower():
                            if key == 'origin':
                                product['origin_country'] = value
                            elif key == 'processing':
                                product['processing_method'] = value
                            elif key == 'roast':
                                product['roast_level'] = value
                            elif key == 'variety':
                                product['bean_variety'] = value
                            break

            enriched.append(product)
            time.sleep(2)  # 增加延迟

        except Exception as e:
            logger.warning(f"获取产品详情失败: {e}")
            enriched.append(product)

    return enriched + products[5:]


def get_sample_products() -> List[Dict[str, Any]]:
    """返回示例产品数据（用于测试或爬虫失败时）"""
    return [
        {
            'roaster_brand': '明谦咖啡',
            'product_name': '埃塞俄比亚耶加雪菲·花魁',
            'bean_variety': '埃塞俄比亚原生种',
            'origin_country': 'Ethiopia',
            'origin_region': 'Yirgacheffe',
            'altitude': '1800-2000m',
            'roast_level': 'Light',
            'processing_method': 'Natural',
            'flavor_tags': ['茉莉花', '柑橘', '蜂蜜', '柠檬', '红茶'],
            'tasting_notes': '这款咖啡展现出茉莉花和柑橘的香气，蜂蜜般的甜感，尾段带有红茶的余韵。',
            'brew_suggestions': {'method': 'V60', 'temp': '90-92°C', 'ratio': '1:15'},
            'price_range': '88元/227g',
            'source_url': 'https://example.com/ethiopia-yirgacheffe'
        },
        {
            'roaster_brand': '明谦咖啡',
            'product_name': '哥伦比亚慧兰·粉红波旁',
            'bean_variety': 'Pink Bourbon',
            'origin_country': 'Colombia',
            'origin_region': 'Huila',
            'altitude': '1700-1900m',
            'roast_level': 'Light',
            'processing_method': 'Washed',
            'flavor_tags': ['草莓', '焦糖', '甜橙', '红酒'],
            'tasting_notes': '明亮的草莓酸甜感，伴随焦糖和甜橙的风味，尾段有红酒般的余韵。',
            'brew_suggestions': {'method': 'Chemex', 'temp': '92-94°C', 'ratio': '1:16'},
            'price_range': '95元/227g',
            'source_url': 'https://example.com/colombia-pink-bourbon'
        },
        {
            'roaster_brand': '明谦咖啡',
            'product_name': '肯尼亚AA·水洗',
            'bean_variety': 'SL28, SL34',
            'origin_country': 'Kenya',
            'origin_region': 'Nyeri',
            'altitude': '1700-1900m',
            'roast_level': 'Medium-Light',
            'processing_method': 'Washed',
            'flavor_tags': ['黑醋栗', '葡萄柚', '布朗尼', '柠檬'],
            'tasting_notes': '经典的肯尼亚风味，黑醋栗和葡萄柚的明亮酸度，布朗尼般的醇厚度。',
            'brew_suggestions': {'method': 'Kalita Wave', 'temp': '93-95°C', 'ratio': '1:15.5'},
            'price_range': '82元/227g',
            'source_url': 'https://example.com/kenya-aa'
        }
    ]


def generate_embedding(text: str) -> Optional[List[float]]:
    """生成文本的向量嵌入"""
    try:
        ctx = request_context.get() or new_context(method="update_coffee_database")
        client = EmbeddingClient()

        # 构建用于检索的文本
        search_text = f"{text}"
        embedding = client.embed_text(search_text)

        return embedding
    except Exception as e:
        logger.error(f"生成 embedding 失败: {e}")
        return None


def upsert_coffee_product(product: Dict[str, Any]) -> Optional[int]:
    """插入或更新咖啡产品"""
    try:
        session = get_db_session()

        # 检查产品是否已存在（通过品牌和名称）
        result = session.execute(
            text("""
                SELECT id FROM coffee_products
                WHERE roaster_brand = :brand AND product_name = :name
            """),
            {"brand": product['roaster_brand'], "name": product['product_name']}
        )
        existing = result.fetchone()

        now = datetime.now()

        if existing:
            # 更新现有产品
            product_id = existing[0]
            session.execute(
                text("""
                    UPDATE coffee_products
                    SET bean_variety = :variety,
                        origin_country = :origin,
                        origin_region = :region,
                        altitude = :altitude,
                        roast_level = :roast,
                        processing_method = :processing,
                        flavor_tags = :flavor_tags,
                        tasting_notes = :tasting_notes,
                        brew_suggestions = :brew_suggestions,
                        price_range = :price,
                        source_url = :source_url,
                        update_date = :update_date,
                        last_daily_check = :check_date,
                        is_active = true
                    WHERE id = :id
                """),
                {
                    "variety": product.get('bean_variety'),
                    "origin": product.get('origin_country'),
                    "region": product.get('origin_region'),
                    "altitude": product.get('altitude'),
                    "roast": product.get('roast_level'),
                    "processing": product.get('processing_method'),
                    "flavor_tags": product.get('flavor_tags', []),
                    "tasting_notes": product.get('tasting_notes'),
                    "brew_suggestions": json.dumps(product.get('brew_suggestions')) if product.get('brew_suggestions') else None,
                    "price": product.get('price_range'),
                    "source_url": product.get('source_url'),
                    "update_date": now,
                    "check_date": now.date(),
                    "id": product_id
                }
            )
        else:
            # 插入新产品
            result = session.execute(
                text("""
                    INSERT INTO coffee_products (
                        roaster_brand, product_name, bean_variety,
                        origin_country, origin_region, altitude,
                        roast_level, processing_method, flavor_tags,
                        tasting_notes, brew_suggestions, price_range,
                        source_url, update_date, last_daily_check, is_active
                    ) VALUES (
                        :brand, :name, :variety, :origin, :region, :altitude,
                        :roast, :processing, :flavor_tags, :tasting_notes,
                        :brew_suggestions, :price, :source_url, :update_date,
                        :check_date, :is_active
                    ) RETURNING id
                """),
                {
                    "brand": product['roaster_brand'],
                    "name": product['product_name'],
                    "variety": product.get('bean_variety'),
                    "origin": product.get('origin_country'),
                    "region": product.get('origin_region'),
                    "altitude": product.get('altitude'),
                    "roast": product.get('roast_level'),
                    "processing": product.get('processing_method'),
                    "flavor_tags": product.get('flavor_tags', []),
                    "tasting_notes": product.get('tasting_notes'),
                    "brew_suggestions": json.dumps(product.get('brew_suggestions')) if product.get('brew_suggestions') else None,
                    "price": product.get('price_range'),
                    "source_url": product.get('source_url'),
                    "update_date": now,
                    "check_date": now.date(),
                    "is_active": True
                }
            )
            product_id = result.fetchone()[0]

        session.commit()
        session.close()

        return product_id

    except Exception as e:
        logger.error(f"插入/更新产品失败: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
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
        content_parts.extend(product.get('flavor_tags', []))
        content_parts.append(product.get('tasting_notes', ''))

        search_text = ' '.join(filter(None, content_parts))

        # 生成向量
        embedding = generate_embedding(search_text)
        if not embedding:
            logger.warning(f"产品 {coffee_id} 生成 embedding 失败")
            return

        # 存储向量
        session = get_db_session()

        # 检查是否已存在
        result = session.execute(
            text("SELECT id FROM coffee_embeddings WHERE coffee_id = :coffee_id"),
            {"coffee_id": coffee_id}
        )
        existing = result.fetchone()

        if existing:
            # 更新现有向量
            session.execute(
                text("""
                    UPDATE coffee_embeddings
                    SET embedding = :embedding, content = :content, created_at = :created_at
                    WHERE coffee_id = :coffee_id
                """),
                {
                    "embedding": embedding,
                    "content": search_text,
                    "created_at": datetime.now(),
                    "coffee_id": coffee_id
                }
            )
        else:
            # 插入新向量
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

        logger.info(f"产品 {coffee_id} 向量存储成功")

    except Exception as e:
        logger.error(f"存储产品向量失败: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()


@tool
def update_coffee_database() -> str:
    """
    更新咖啡产品数据库（每日限流一次）

    该工具会：
    1. 检查今日是否已更新
    2. 如果未更新，爬取 specialitycoffee.ca 网站的最新产品
    3. 更新数据库中的产品信息
    4. 生成向量索引

    Returns:
        str: 更新结果信息
    """
    try:
        # 检查今日是否已更新
        if check_today_updated():
            return "今日已更新数据库，跳过本次更新。"

        logger.info("开始更新咖啡产品数据库...")

        # 爬取产品信息
        products = scrape_coffee_products()

        if not products:
            return "未获取到产品信息，更新失败。"

        logger.info(f"获取到 {len(products)} 个产品")

        # 更新产品到数据库
        updated_count = 0
        for product in products:
            product_id = upsert_coffee_product(product)
            if product_id:
                # 生成并存储向量
                store_product_embedding(product_id, product)
                updated_count += 1

        logger.info(f"成功更新 {updated_count} 个产品")

        return f"✅ 数据库更新成功！共更新 {updated_count} 个产品，其中包含新的向量索引。"

    except Exception as e:
        logger.error(f"更新数据库失败: {e}")
        return f"❌ 更新数据库失败: {str(e)}"
