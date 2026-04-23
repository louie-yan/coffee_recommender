"""
Coffee Recommendation Evaluator
评估推荐咖啡产品与用户喜好的匹配程度
"""

from langchain.tools import tool
from typing import Dict, Any, Optional
import logging
import json

logger = logging.getLogger(__name__)


def evaluate_dimension(
    product_value: Any,
    user_preference: Any,
    dimension_name: str
) -> Optional[int]:
    """
    评估单个维度的匹配度

    Args:
        product_value: 产品在该维度的值
        user_preference: 用户在该维度的偏好
        dimension_name: 维度名称（用于特殊处理）

    Returns:
        int: 1 (匹配), 0 (不匹配), None (跳过评估)
    """
    # 如果用户未提供该维度的偏好，跳过评估
    if user_preference is None or user_preference == "":
        return None

    # 如果产品未记录该维度的值，跳过评估
    if product_value is None or product_value == "":
        return None

    # 特殊维度处理
    if dimension_name == "flavor":
        return evaluate_flavor_dimension(product_value, user_preference)

    # 通用维度处理
    user_pref_lower = str(user_preference).lower()
    product_value_lower = str(product_value).lower()

    # 精确匹配
    if user_pref_lower == product_value_lower:
        return 1

    # 包含匹配
    if user_pref_lower in product_value_lower or product_value_lower in user_pref_lower:
        return 1

    # 风味标签匹配（针对 flavor_tags 数组）
    if isinstance(product_value, list):
        for tag in product_value:
            if user_pref_lower in str(tag).lower():
                return 1

    return 0


def evaluate_flavor_dimension(
    flavor_tags: Any,
    user_preference: str
) -> Optional[int]:
    """
    评估风味维度的匹配度

    Args:
        flavor_tags: 产品的风味标签（可能是字符串或数组）
        user_preference: 用户的风味偏好

    Returns:
        int: 1 (匹配), 0 (不匹配), None (跳过评估)
    """
    if not user_preference or not user_preference.strip():
        return None

    if not flavor_tags:
        return 0

    # 将风味标签转换为列表
    tags_list = []
    if isinstance(flavor_tags, list):
        for tag in flavor_tags:
            # 处理可能包含空格、逗号、顿号的标签
            tag_str = str(tag).replace('，', ',').replace('、', ',')
            tags_list.extend([t.strip() for t in tag_str.split(',') if t.strip()])
    else:
        tag_str = str(flavor_tags).replace('，', ',').replace('、', ',')
        tags_list.extend([t.strip() for t in tag_str.split(',') if t.strip()])

    # 处理用户偏好（可能包含逗号分隔的多个关键词）
    user_pref_lower = user_preference.replace('，', ',').replace('、', ',').lower()
    user_keywords = [k.strip() for k in user_pref_lower.split(',') if k.strip()]

    # 检查是否有任何匹配
    for user_keyword in user_keywords:
        for tag in tags_list:
            tag_lower = tag.lower()
            if user_keyword in tag_lower or tag_lower in user_keyword:
                return 1

    return 0


def evaluate_price_dimension(
    product_price: Any,
    user_price_range: str
) -> Optional[int]:
    """
    评估价格维度的匹配度

    Args:
        product_price: 产品价格
        user_price_range: 用户价格范围

    Returns:
        int: 1 (匹配), 0 (不匹配), None (跳过评估)
    """
    if not user_price_range or not user_price_range.strip():
        return None

    if not product_price:
        return 0

    # 提取产品价格中的数字
    import re
    product_match = re.search(r'(\d+)', str(product_price))
    if not product_match:
        return 0

    product_price_num = int(product_match.group(1))

    # 解析用户价格范围
    # 支持 "50-80元", "50元左右", "50元以下", "50元以上" 等格式
    user_lower = user_price_range.lower()

    # "50元左右" - 允许 ±20 元误差
    if "左右" in user_lower or "约" in user_lower:
        target_match = re.search(r'(\d+)', user_lower)
        if target_match:
            target = int(target_match.group(1))
            if abs(product_price_num - target) <= 20:
                return 1

    # "50元以下"
    elif "以下" in user_lower or "小于" in user_lower:
        max_match = re.search(r'(\d+)', user_lower)
        if max_match:
            max_price = int(max_match.group(1))
            if product_price_num <= max_price:
                return 1

    # "50元以上"
    elif "以上" in user_lower or "大于" in user_lower:
        min_match = re.search(r'(\d+)', user_lower)
        if min_match:
            min_price = int(min_match.group(1))
            if product_price_num >= min_price:
                return 1

    # "50-80元" 区间
    else:
        range_matches = re.findall(r'(\d+)', user_lower)
        if len(range_matches) >= 2:
            min_price = int(range_matches[0])
            max_price = int(range_matches[1])
            if min_price <= product_price_num <= max_price:
                return 1

    return 0


@tool
def evaluate_recommendation_match(
    product_info: Dict[str, Any],
    user_preferences: Dict[str, Any]
) -> str:
    """
    评估推荐产品与用户喜好的匹配程度

    Args:
        product_info: 推荐的产品信息（来自 search_coffee_products 的返回结果）
        user_preferences: 用户的偏好信息，包含以下字段：
            - flavor_preference: 风味偏好（如：花香、果香）
            - bean_variety: 豆种偏好
            - origin: 产地偏好
            - processing_method: 处理法偏好
            - roast_level: 烘焙度偏好
            - price_range: 价格范围偏好

    Returns:
        str: JSON 格式的评估结果，包含：
            - is_match: 是否匹配
            - match_score: 匹配分数
            - dimension_scores: 各维度评分
            - is_good_match: 是否是好匹配
            - recommendation: 建议（是否重新推荐）
    """
    try:
        # 提取产品和用户偏好
        product = product_info.get("product", product_info) if isinstance(product_info, dict) else product_info

        # 初始化维度评分
        dimension_scores = {
            "flavor": None,
            "bean_variety": None,
            "processing_method": None,
            "roast_level": None,
            "price": None,
            "origin": None
        }

        # 评估各个维度
        dimension_scores["flavor"] = evaluate_dimension(
            product.get("flavor_tags", product.get("tasting_notes")),
            user_preferences.get("flavor_preference"),
            "flavor"
        )

        dimension_scores["bean_variety"] = evaluate_dimension(
            product.get("bean_variety"),
            user_preferences.get("bean_variety"),
            "bean_variety"
        )

        dimension_scores["processing_method"] = evaluate_dimension(
            product.get("processing_method"),
            user_preferences.get("processing_method"),
            "processing_method"
        )

        dimension_scores["roast_level"] = evaluate_dimension(
            product.get("roast_level"),
            user_preferences.get("roast_level"),
            "roast_level"
        )

        dimension_scores["price"] = evaluate_price_dimension(
            product.get("price_range"),
            user_preferences.get("price_range", "")
        )

        dimension_scores["origin"] = evaluate_dimension(
            product.get("origin_country"),
            user_preferences.get("origin"),
            "origin"
        )

        # 计算总匹配分数（只计算已评估的维度）
        evaluated_dimensions = {k: v for k, v in dimension_scores.items() if v is not None}
        if evaluated_dimensions:
            match_score = sum(evaluated_dimensions.values()) / len(evaluated_dimensions)
        else:
            match_score = 0.0

        # 判断是否是好匹配
        is_good_match = check_match_quality(dimension_scores)

        # 决定是否需要重新推荐
        should_retry = not is_good_match

        result = {
            "is_match": match_score > 0,
            "match_score": round(match_score, 2),
            "dimension_scores": dimension_scores,
            "evaluated_dimensions": list(evaluated_dimensions.keys()),
            "is_good_match": is_good_match,
            "should_retry": should_retry,
            "recommendation": "重新推荐" if should_retry else "使用当前推荐",
            "reason": get_evaluation_reason(dimension_scores, is_good_match)
        }

        logger.info(f"评估结果: 匹配分数={match_score:.2f}, 好匹配={is_good_match}")
        logger.info(f"维度评分: {dimension_scores}")

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"评估失败: {e}")
        return json.dumps({
            "is_match": False,
            "match_score": 0.0,
            "dimension_scores": {},
            "is_good_match": False,
            "should_retry": False,
            "error": str(e)
        }, ensure_ascii=False, indent=2)


def check_match_quality(dimension_scores: Dict[str, Optional[int]]) -> bool:
    """
    检查匹配质量

    规则：
    1. 风味匹配分数必须为 1（如果用户提供了风味偏好）
    2. 处理法、烘焙程度两个维度中至少 1 个为 1（如果用户提供了相关偏好）
    3. 价格、产地、豆种可以接受不匹配

    Args:
        dimension_scores: 各维度评分

    Returns:
        bool: 是否是好匹配
    """
    # 规则 1: 风味必须匹配（如果用户提供了风味偏好）
    if dimension_scores["flavor"] is not None:
        if dimension_scores["flavor"] != 1:
            return False

    # 规则 2: 处理法、烘焙程度至少 1 个匹配
    processing_score = dimension_scores.get("processing_method")
    roast_score = dimension_scores.get("roast_level")

    # 如果用户提供了其中任何一个偏好，检查是否有匹配
    if processing_score is not None or roast_score is not None:
        # 至少有 1 个匹配
        has_one_match = False
        if processing_score == 1 or roast_score == 1:
            has_one_match = True

        # 如果两个都提供了但都不匹配，则不是好匹配
        if (processing_score is not None and processing_score == 0) and \
           (roast_score is not None and roast_score == 0):
            return False

    return True


def get_evaluation_reason(dimension_scores: Dict[str, Optional[int]], is_good_match: bool) -> str:
    """
    获取评估原因

    Args:
        dimension_scores: 各维度评分
        is_good_match: 是否是好匹配

    Returns:
        str: 评估原因
    """
    if is_good_match:
        return "产品与用户偏好匹配良好"

    reasons = []

    if dimension_scores.get("flavor") == 0:
        reasons.append("风味不匹配")

    if dimension_scores.get("processing_method") == 0 and dimension_scores.get("roast_level") == 0:
        reasons.append("处理法和烘焙度都不匹配")
    elif dimension_scores.get("processing_method") == 0:
        reasons.append("处理法不匹配")
    elif dimension_scores.get("roast_level") == 0:
        reasons.append("烘焙度不匹配")

    if dimension_scores.get("price") == 0:
        reasons.append("价格不匹配")

    if dimension_scores.get("origin") == 0:
        reasons.append("产地不匹配")

    if dimension_scores.get("bean_variety") == 0:
        reasons.append("豆种不匹配")

    if not reasons:
        reasons.append("综合匹配度不够")

    return "; ".join(reasons)
