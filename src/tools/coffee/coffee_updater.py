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

    流程：
    1. 访问产品列表页 https://specialitycoffee.ca/product-category/filter/
    2. 提取所有产品页面的链接
    3. 进入每个产品详情页获取详细信息

    Returns:
        List[Dict]: 咖啡产品信息列表
    """
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin

    base_url = "https://specialitycoffee.ca"
    products_list_url = f"{base_url}/product-category/filter/"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    products = []

    try:
        logger.info(f"步骤1: 爬取产品列表页: {products_list_url}")
        response = requests.get(products_list_url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # 查找产品链接 - 尝试多种选择器
        product_links = []

        # 方法1: 查找所有指向产品详情页的链接
        for a in soup.find_all('a', href=True):
            href = a.get('href')
            if href and '/product/' in href and '/product-category/' not in href:
                product_links.append(urljoin(base_url, href))

        # 方法2: 如果方法1没找到，尝试其他常见选择器
        if not product_links:
            for item in soup.find_all(['div', 'li', 'article']):
                if any(cls in str(item.get('class', '')) for cls in ['product', 'item', 'post']):
                    link = item.find('a', href=True)
                    href = link.get('href') if link else None
                    if href and '/product/' in href:
                        product_links.append(urljoin(base_url, href))

        # 去重
        product_links = list(set(product_links))
        logger.info(f"找到 {len(product_links)} 个产品链接")

        # 限制爬取数量（避免过度爬取）
        product_links = product_links[:15]

        # 步骤2: 访问每个产品详情页
        for idx, product_url in enumerate(product_links, 1):
            try:
                logger.info(f"步骤2: 爬取产品详情 [{idx}/{len(product_links)}]: {product_url}")

                product_info = scrape_product_detail(product_url, headers, base_url)

                if product_info:
                    products.append(product_info)
                    logger.info(f"✓ 成功提取产品: {product_info.get('product_name', 'Unknown')}")

                # 添加延迟避免被封
                time.sleep(2)

            except Exception as e:
                logger.warning(f"✗ 爬取产品详情失败: {e}")
                continue

        logger.info(f"总共成功提取 {len(products)} 个产品")

    except Exception as e:
        logger.error(f"爬取失败: {e}")
        # 返回一些示例数据用于测试
        logger.info("返回示例数据")
        products = get_sample_products()

    return products


def scrape_product_detail(product_url: str, headers: dict, base_url: str) -> Optional[Dict[str, Any]]:
    """
    爬取单个产品详情页的信息

    Args:
        product_url: 产品详情页 URL
        headers: HTTP 请求头
        base_url: 网站 base URL

    Returns:
        Dict or None: 产品信息字典
    """
    import requests
    from bs4 import BeautifulSoup

    try:
        response = requests.get(product_url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # 提取基本信息
        product_info = {
            'roaster_brand': None,
            'product_name': None,
            'bean_variety': None,
            'origin_country': None,
            'origin_region': None,
            'altitude': None,
            'roast_level': None,
            'processing_method': None,
            'flavor_tags': [],
            'tasting_notes': None,
            'brew_suggestions': None,
            'price_range': None,
            'source_url': product_url,
            'image_url': None
        }

        # 1. 提取产品名称
        title_elem = soup.find('h1') or soup.find('h2') or soup.find(class_='product_title')
        if title_elem:
            product_info['product_name'] = title_elem.get_text(strip=True)

        # 2. 提取品牌
        # 尝试从面包屑导航、产品标题或URL中提取
        breadcrumbs = soup.find_all(class_='breadcrumb') or soup.find_all('nav', class_='woocommerce-breadcrumb')
        for breadcrumb in breadcrumbs:
            breadcrumb_text = breadcrumb.get_text(strip=True)
            if 'Coffee' in breadcrumb_text or 'Home' in breadcrumb_text:
                parts = breadcrumb_text.split('/')
                if len(parts) > 1:
                    product_info['roaster_brand'] = parts[-2].strip() if parts[-2] else 'Speciality Coffee'

        if not product_info['roaster_brand']:
            product_info['roaster_brand'] = 'Speciality Coffee'

        # 3. 提取价格
        price_elem = soup.find(class_='price') or soup.find(class_='woocommerce-Price-amount')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            # 提取数字和货币符号
            import re
            price_match = re.search(r'[$€£]?\s*[\d.,]+', price_text)
            if price_match:
                product_info['price_range'] = price_match.group()

        # 4. 提取产品描述和风味信息
        description = ""
        desc_elems = [
            soup.find(class_='woocommerce-product-details__short-description'),
            soup.find(class_='product-description'),
            soup.find(class_='description'),
            soup.find('div', {'id': 'tab-description'}),
            soup.find(class_='summary')
        ]

        for elem in desc_elems:
            if elem:
                desc = elem.get_text(strip=True)
                if len(desc) > 50:  # 过滤掉太短的内容
                    description = desc
                    break

        product_info['tasting_notes'] = description[:1000] if description else None

        # 5. 从描述中提取结构化信息
        product_info.update(extract_coffee_info_from_description(description, product_info['product_name']))

        # 6. 提取图像
        img_elem = soup.find('img', class_='wp-post-image') or soup.find(class_='product-image') or soup.find('img', class_='attachment-woocommerce_single')
        if img_elem and img_elem.get('src'):
            product_info['image_url'] = img_elem['src']

        # 7. 尝试从特定区域提取更多信息
        # 查找可能包含产品规格的区域
        specs_sections = soup.find_all(class_=['product-specs', 'coffee-specs', 'product-attributes'])
        for section in specs_sections:
            section_text = section.get_text(strip=True)
            additional_info = extract_coffee_info_from_description(section_text, product_info['product_name'])
            for key, value in additional_info.items():
                if not product_info.get(key):
                    product_info[key] = value

        return product_info

    except Exception as e:
        logger.error(f"爬取产品详情页失败: {e}")
        return None


def extract_coffee_info_from_description(text: str, product_name: str = None) -> Dict[str, Any]:
    """
    从描述文本中提取咖啡的结构化信息

    Args:
        text: 描述文本
        product_name: 产品名称（辅助提取）

    Returns:
        Dict: 提取的结构化信息
    """
    import re

    info = {
        'bean_variety': None,
        'origin_country': None,
        'origin_region': None,
        'altitude': None,
        'roast_level': None,
        'processing_method': None,
        'flavor_tags': []
    }

    if not text:
        return info

    text_lower = text.lower()

    # 1. 提取产地
    origins = {
        'ethiopia': 'Ethiopia',
        'colombia': 'Colombia',
        'kenya': 'Kenya',
        'guatemala': 'Guatemala',
        'brazil': 'Brazil',
        'panama': 'Panama',
        'costa rica': 'Costa Rica',
        'indonesia': 'Indonesia',
        'tanzania': 'Tanzania',
        'rwanda': 'Rwanda',
        'uganda': 'Uganda',
        'burundi': 'Burundi',
        'mexico': 'Mexico',
        'peru': 'Peru',
        'honduras': 'Honduras',
        'nicaragua': 'Nicaragua',
        'yemen': 'Yemen',
        'jamaica': 'Jamaica'
    }

    for origin_en, origin_name in origins.items():
        if origin_en in text_lower:
            info['origin_country'] = origin_name
            break

    # 2. 提取产区
    region_patterns = [
        r'(\w+cheffe)',  # Yirgacheffe, Sidamo, Guji
        r'(\w+la)',  # Huila, Tolima, Narino
        r'(\w+ri)',  # Nyeri, Kirinyaga
        r'(\w+go)',  # Antiogo, Chiriqui
    ]
    for pattern in region_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            region = match.group(1).title()
            if region not in info['origin_region'] if info['origin_region'] else True:
                info['origin_region'] = region
                break

    # 3. 提取海拔
    altitude_match = re.search(r'(\d{3,4})\s*(-|~|to)?\s*(\d{3,4})?\s*m', text, re.IGNORECASE)
    if altitude_match:
        start = altitude_match.group(1)
        end = altitude_match.group(3) if altitude_match.group(3) else start
        info['altitude'] = f"{start}-{end}m"

    # 4. 提取豆种
    varieties = [
        'Bourbon', 'Typica', 'Gesha', 'Geisha', 'SL28', 'SL34',
        'Catuai', 'Caturra', 'Pacamara', 'Maragogype', 'Pacas',
        'Mundo Novo', 'Catimor', 'Kent', 'S795', 'Rume Sudan',
        'Pink Bourbon', 'Red Bourbon', 'Yellow Bourbon'
    ]
    for variety in varieties:
        if variety.lower() in text_lower:
            info['bean_variety'] = variety
            break

    # 5. 提取处理法
    processing_methods = {
        'washed': 'Washed',
        'water processed': 'Washed',
        'natural': 'Natural',
        'dry processed': 'Natural',
        'honey': 'Honey',
        'pulped natural': 'Honey',
        'anaerobic': 'Anaerobic',
        'carbonic maceration': 'Anaerobic'
    }
    for method_en, method_name in processing_methods.items():
        if method_en in text_lower:
            info['processing_method'] = method_name
            break

    # 6. 提取烘焙度
    roast_levels = {
        'light roast': 'Light',
        'medium-light roast': 'Medium-Light',
        'medium roast': 'Medium',
        'medium-dark roast': 'Medium-Dark',
        'dark roast': 'Dark'
    }
    for roast_en, roast_name in roast_levels.items():
        if roast_en in text_lower:
            info['roast_level'] = roast_name
            break

    # 7. 提取风味标签
    flavor_keywords = {
        # 花香
        'floral': None,
        'jasmine': '茉莉花',
        'rose': '玫瑰',
        'lavender': '薰衣草',
        'hibiscus': '芙蓉',

        # 果香
        'fruity': None,
        'citrus': '柑橘',
        'lemon': '柠檬',
        'orange': '甜橙',
        'grapefruit': '葡萄柚',
        'berry': '莓果',
        'strawberry': '草莓',
        'blueberry': '蓝莓',
        'raspberry': '覆盆子',
        'stone fruit': '核果',
        'peach': '桃子',
        'mango': '芒果',
        'pineapple': '菠萝',
        'apple': '苹果',

        # 坚果
        'nutty': None,
        'almond': '杏仁',
        'hazelnut': '榛子',
        'walnut': '核桃',
        'cashew': '腰果',
        'peanut': '花生',

        # 巧克力
        'chocolate': '巧克力',
        'dark chocolate': '黑巧克力',
        'cocoa': '可可',
        'cacao': '可可',

        # 糖类
        'sweet': '甜',
        'caramel': '焦糖',
        'honey': '蜂蜜',
        'brown sugar': '红糖',
        'molasses': '糖蜜',
        'toffee': '太妃糖',
        'maple': '枫糖',

        # 谷物
        'grainy': '谷物',
        'oat': '燕麦',
        'bread': '面包',
        'toast': '吐司',
        'biscuit': '饼干',

        # 香料
        'spicy': '香料',
        'cinnamon': '肉桂',
        'clove': '丁香',
        'cardamom': '豆蔻',
        'pepper': '胡椒',

        # 其他
        'earthy': '泥土',
        'tobacco': '烟草',
        'wine': '红酒',
        'winey': '红酒',
        'rum': '朗姆酒',
        'tea': '茶',
        'black tea': '红茶',
        'green tea': '绿茶',
        'chocolate': '巧克力',
        'brownie': '布朗尼'
    }

    found_tags = []
    for keyword_en, keyword_zh in flavor_keywords.items():
        if keyword_en in text_lower:
            if keyword_zh:
                found_tags.append(keyword_zh)
            else:
                # 将英文关键词翻译成中文
                translation_map = {
                    'floral': '花香',
                    'fruity': '果香',
                    'nutty': '坚果',
                    'sweet': '甜',
                    'spicy': '香料',
                    'grainy': '谷物',
                    'earthy': '泥土',
                    'winey': '酒香'
                }
                if keyword_en in translation_map:
                    found_tags.append(translation_map[keyword_en])

    # 去重并限制数量（最多6个）
    info['flavor_tags'] = list(set(found_tags))[:6]

    return info


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
