#!/usr/bin/env python3
"""
测试评估工具
"""

import sys
import os
import json

# 添加项目路径
workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
sys.path.insert(0, workspace_path)

# 导入底层的评估函数
from src.tools.coffee.coffee_evaluator import (
    evaluate_dimension,
    evaluate_flavor_dimension,
    evaluate_price_dimension,
    check_match_quality,
    get_evaluation_reason
)


def evaluate_recommendation(product_info, user_preferences):
    """手动实现评估逻辑（用于测试）"""
    product = product_info.get("product", product_info)

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

    # 计算总匹配分数
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

    return json.dumps(result, ensure_ascii=False, indent=2)


def test_evaluation():
    """测试评估工具"""
    print("=" * 80)
    print("测试评估工具")
    print("=" * 80)
    """测试评估工具"""
    print("=" * 80)
    print("测试评估工具")
    print("=" * 80)

    # 测试场景 1：完美匹配
    print("\n测试场景 1：完美匹配")
    print("-" * 80)

    product_info = {
        "product": {
            "flavor_tags": ["茉莉花", "柑橘", "蜂蜜"],
            "processing_method": "Natural",
            "roast_level": "Light",
            "origin_country": "Ethiopia",
            "bean_variety": "Heirloom",
            "price_range": "88元/227g"
        }
    }

    user_preferences = {
        "flavor_preference": "茉莉花",
        "processing_method": "Natural",
        "roast_level": "Light",
        "origin": "Ethiopia"
    }

    result = json.loads(evaluate_recommendation(product_info, user_preferences))
    print(f"匹配分数: {result['match_score']}")
    print(f"是否好匹配: {result['is_good_match']}")
    print(f"是否需要重新推荐: {result['should_retry']}")
    print(f"维度评分: {json.dumps(result['dimension_scores'], ensure_ascii=False, indent=2)}")
    print(f"评估原因: {result['reason']}")

    # 测试场景 2：风味不匹配
    print("\n\n测试场景 2：风味不匹配")
    print("-" * 80)

    product_info = {
        "product": {
            "flavor_tags": ["坚果", "巧克力", "焦糖"],
            "processing_method": "Natural",
            "roast_level": "Light",
            "origin_country": "Ethiopia",
            "bean_variety": "Heirloom",
            "price_range": "88元/227g"
        }
    }

    user_preferences = {
        "flavor_preference": "茉莉花",
        "processing_method": "Natural",
        "roast_level": "Light",
        "origin": "Ethiopia"
    }

    result = json.loads(evaluate_recommendation(product_info, user_preferences))
    print(f"匹配分数: {result['match_score']}")
    print(f"是否好匹配: {result['is_good_match']}")
    print(f"是否需要重新推荐: {result['should_retry']}")
    print(f"维度评分: {json.dumps(result['dimension_scores'], ensure_ascii=False, indent=2)}")
    print(f"评估原因: {result['reason']}")

    # 测试场景 3：处理法和烘焙度都不匹配
    print("\n\n测试场景 3：处理法和烘焙度都不匹配")
    print("-" * 80)

    product_info = {
        "product": {
            "flavor_tags": ["茉莉花", "柑橘", "蜂蜜"],
            "processing_method": "Washed",
            "roast_level": "Medium",
            "origin_country": "Ethiopia",
            "bean_variety": "Heirloom",
            "price_range": "88元/227g"
        }
    }

    user_preferences = {
        "flavor_preference": "茉莉花",
        "processing_method": "Natural",
        "roast_level": "Light",
        "origin": "Ethiopia"
    }

    result = json.loads(evaluate_recommendation(product_info, user_preferences))
    print(f"匹配分数: {result['match_score']}")
    print(f"是否好匹配: {result['is_good_match']}")
    print(f"是否需要重新推荐: {result['should_retry']}")
    print(f"维度评分: {json.dumps(result['dimension_scores'], ensure_ascii=False, indent=2)}")
    print(f"评估原因: {result['reason']}")

    # 测试场景 4：部分维度未提供
    print("\n\n测试场景 4：部分维度未提供")
    print("-" * 80)

    product_info = {
        "product": {
            "flavor_tags": ["茉莉花", "柑橘", "蜂蜜"],
            "processing_method": "Natural",
            "roast_level": "Light",
            # origin 和 bean_variety 未提供
            "price_range": "88元/227g"
        }
    }

    user_preferences = {
        "flavor_preference": "茉莉花",
        "processing_method": "Natural",
        "roast_level": "Light"
        # origin 和 bean_variety 未提供
    }

    result = json.loads(evaluate_recommendation(product_info, user_preferences))
    print(f"匹配分数: {result['match_score']}")
    print(f"是否好匹配: {result['is_good_match']}")
    print(f"是否需要重新推荐: {result['should_retry']}")
    print(f"维度评分: {json.dumps(result['dimension_scores'], ensure_ascii=False, indent=2)}")
    print(f"评估原因: {result['reason']}")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    test_evaluation()
