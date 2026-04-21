"""
Price Matcher Tool
增强的价格匹配逻辑，支持复杂价格区间解析
"""

from langchain.tools import tool
from typing import Optional, Tuple
import logging
import json
import re

logger = logging.getLogger(__name__)


def parse_price_range(price_str: str) -> Optional[Tuple[float, float]]:
    """
    解析价格区间字符串，返回 (min_price, max_price)

    支持的格式：
    - "50-80" -> (50, 80)
    - "50~80" -> (50, 80)
    - "50到80" -> (50, 80)
    - "50-80元" -> (50, 80)
    - "50-80元/100g" -> (50, 80)
    - "50元左右" -> (40, 60)
    - "50元以下" -> (0, 50)
    - "50元以上" -> (50, 999999)
    - "80" -> (75, 85)  # 单个价格，给予±5的容差

    Args:
        price_str: 价格字符串

    Returns:
        Tuple[float, float] or None: (min_price, max_price)，解析失败返回 None
    """
    try:
        price_str = price_str.strip()

        # 1. 处理 "50-80" 格式
        match = re.search(r'(\d+)\s*[-~到]\s*(\d+)', price_str)
        if match:
            min_price = float(match.group(1))
            max_price = float(match.group(2))
            return (min_price, max_price)

        # 2. 处理 "50元左右" 格式
        match = re.search(r'(\d+)\s*元?\s*左右', price_str)
        if match:
            base_price = float(match.group(1))
            # ±5 的容差
            return (base_price - 5, base_price + 5)

        # 3. 处理 "50元以下" 格式
        match = re.search(r'(\d+)\s*元?\s*(以下|以内)', price_str)
        if match:
            max_price = float(match.group(1))
            return (0, max_price)

        # 4. 处理 "50元以上" 格式
        match = re.search(r'(\d+)\s*元?\s*(以上|超过)', price_str)
        if match:
            min_price = float(match.group(1))
            return (min_price, 999999)

        # 5. 处理单个数字 "80" 或 "80元"
        match = re.search(r'^(\d+)\s*元?$', price_str)
        if match:
            base_price = float(match.group(1))
            # 给予±5的容差
            return (base_price - 5, base_price + 5)

        logger.warning(f"无法解析价格区间: {price_str}")
        return None

    except Exception as e:
        logger.error(f"解析价格区间失败: {e}")
        return None


def extract_price_from_range(price_str: str) -> Optional[float]:
    """
    从价格区间字符串中提取一个代表性价格

    Args:
        price_str: 价格字符串，如 "50-80元"

    Returns:
        float or None: 代表性价格（中位数或第一个价格）
    """
    try:
        # 尝试解析为区间
        range_tuple = parse_price_range(price_str)
        if range_tuple:
            min_price, max_price = range_tuple
            # 返回中位数
            return (min_price + max_price) / 2

        # 尝试提取第一个数字
        match = re.search(r'(\d+)', price_str)
        if match:
            return float(match.group(1))

        return None

    except Exception as e:
        logger.error(f"提取价格失败: {e}")
        return None


def is_price_in_range(user_range: Tuple[float, float], product_price_str: str) -> bool:
    """
    检查产品价格是否在用户指定的价格范围内

    Args:
        user_range: 用户价格范围 (min_price, max_price)
        product_price_str: 产品价格字符串

    Returns:
        bool: 是否在范围内
    """
    try:
        # 解析产品价格
        product_price = extract_price_from_range(product_price_str)
        if product_price is None:
            # 无法解析产品价格，默认匹配
            logger.warning(f"无法解析产品价格: {product_price_str}")
            return True

        user_min, user_max = user_range

        # 检查是否在范围内
        return user_min <= product_price <= user_max

    except Exception as e:
        logger.error(f"检查价格范围失败: {e}")
        return True  # 默认匹配


def calculate_price_match_score(
    user_range: Tuple[float, float],
    product_price_str: str
) -> float:
    """
    计算价格匹配分数 (0.0 - 1.0)

    分数越高，匹配度越好：
    - 1.0: 完全匹配
    - 0.7-1.0: 价格接近
    - 0.5-0.7: 价格在可接受范围
    - <0.5: 价格偏离较大

    Args:
        user_range: 用户价格范围 (min_price, max_price)
        product_price_str: 产品价格字符串

    Returns:
        float: 匹配分数
    """
    try:
        # 解析产品价格
        product_price = extract_price_from_range(product_price_str)
        if product_price is None:
            return 0.5  # 无法解析，给中等分数

        user_min, user_max = user_range
        user_mid = (user_min + user_max) / 2

        # 计算产品价格与用户目标价格中位数的偏差
        deviation = abs(product_price - user_mid)
        user_range_width = user_max - user_min

        if user_range_width == 0:
            user_range_width = 10  # 避免除零

        # 偏差比例
        deviation_ratio = deviation / user_range_width

        # 根据偏差比例计算分数
        if deviation_ratio <= 0.2:
            # 偏差在 20% 以内，高匹配
            score = 1.0 - deviation_ratio
        elif deviation_ratio <= 0.5:
            # 偏差在 50% 以内，中等匹配
            score = 0.8 - (deviation_ratio - 0.2)
        elif deviation_ratio <= 1.0:
            # 偏差在 100% 以内，低匹配
            score = 0.5 - (deviation_ratio - 0.5) * 0.5
        else:
            # 偏差超过 100%，极低匹配
            score = 0.2

        return max(0.0, min(1.0, score))

    except Exception as e:
        logger.error(f"计算价格匹配分数失败: {e}")
        return 0.5


@tool
def check_price_match(
    user_price_range: str,
    product_price: str
) -> str:
    """
    检查产品价格是否匹配用户的价格要求

    支持复杂的价格区间解析：
    - "50-80" 或 "50~80" 或 "50到80"
    - "50元左右"
    - "50元以下"
    - "50元以上"
    - "80" 或 "80元"（单个价格，±5容差）

    Args:
        user_price_range: 用户的价格要求，如 "50-80元"
        product_price: 产品的价格，如 "60-70元"

    Returns:
        str: 匹配结果的 JSON 格式字符串
             格式:
             {
               "status": "success" | "mismatch" | "error",
               "is_match": true | false,
               "match_score": 0.85,
               "user_range": [50, 80],
               "product_price": 65,
               "message": "匹配成功"
             }
    """
    try:
        logger.info(f"检查价格匹配: 用户要求 {user_price_range} vs 产品价格 {product_price}")

        # 解析用户价格范围
        user_range = parse_price_range(user_price_range)
        if user_range is None:
            return json.dumps({
                "status": "error",
                "message": f"无法解析用户价格范围: {user_price_range}",
                "suggestions": "请使用以下格式：50-80、50元左右、50元以下、50元以上"
            }, ensure_ascii=False, indent=2)

        # 提取产品价格
        product_price_num = extract_price_from_range(product_price)
        if product_price_num is None:
            logger.warning(f"无法解析产品价格: {product_price}")
            # 无法解析，视为匹配
            return json.dumps({
                "status": "success",
                "is_match": True,
                "match_score": 0.5,
                "user_range": user_range,
                "product_price": None,
                "message": f"无法解析产品价格 '{product_price}'，默认匹配"
            }, ensure_ascii=False, indent=2)

        # 检查是否在范围内
        is_match = is_price_in_range(user_range, product_price)

        # 计算匹配分数
        match_score = calculate_price_match_score(user_range, product_price)

        # 生成消息
        if is_match:
            if match_score >= 0.9:
                message = f"价格完全匹配！产品价格 {product_price_num} 元符合您的要求"
            elif match_score >= 0.7:
                message = f"价格匹配良好。产品价格 {product_price_num} 元在您的预算范围内"
            else:
                message = f"价格基本匹配。产品价格 {product_price_num} 元接近您的预算"
        else:
            message = f"价格不匹配。产品价格 {product_price_num} 元不在您的预算范围内"

        return json.dumps({
            "status": "success" if is_match else "mismatch",
            "is_match": is_match,
            "match_score": round(match_score, 2),
            "user_range": user_range,
            "product_price": product_price_num,
            "message": message
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"检查价格匹配失败: {e}")
        return json.dumps({
            "status": "error",
            "message": f"检查失败: {str(e)}",
            "is_match": False,
            "match_score": 0.0
        }, ensure_ascii=False, indent=2)


@tool
def parse_user_price_range(price_str: str) -> str:
    """
    解析用户输入的价格区间

    支持的格式：
    - "50-80" -> min: 50, max: 80
    - "50~80" -> min: 50, max: 80
    - "50到80" -> min: 50, max: 80
    - "50元左右" -> min: 45, max: 55
    - "50元以下" -> min: 0, max: 50
    - "50元以上" -> min: 50, max: 999999
    - "80" -> min: 75, max: 85

    Args:
        price_str: 用户输入的价格字符串

    Returns:
        str: 解析结果的 JSON 格式字符串
             格式:
             {
               "status": "success" | "error",
               "min_price": 50,
               "max_price": 80,
               "description": "50-80元",
               "message": "解析成功"
             }
    """
    try:
        logger.info(f"解析价格区间: {price_str}")

        # 解析价格范围
        range_tuple = parse_price_range(price_str)
        if range_tuple is None:
            return json.dumps({
                "status": "error",
                "message": f"无法解析价格区间: {price_str}",
                "suggestions": "请使用以下格式：50-80、50元左右、50元以下、50元以上"
            }, ensure_ascii=False, indent=2)

        min_price, max_price = range_tuple

        # 生成描述
        if max_price == 999999:
            description = f"{min_price}元以上"
        elif min_price == 0:
            description = f"{max_price}元以下"
        elif min_price == max_price - 10:  # 单个价格的情况（±5容差）
            description = f"{int((min_price + max_price) / 2)}元左右"
        else:
            description = f"{int(min_price)}-{int(max_price)}元"

        return json.dumps({
            "status": "success",
            "min_price": min_price,
            "max_price": max_price,
            "description": description,
            "message": "解析成功"
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"解析价格区间失败: {e}")
        return json.dumps({
            "status": "error",
            "message": f"解析失败: {str(e)}"
        }, ensure_ascii=False, indent=2)
