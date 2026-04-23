#!/usr/bin/env python3
"""
测试 Reflection + Evaluation 循环功能
测试需要重新推荐的场景
"""

import sys
import os
import json

# 添加项目路径
workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
sys.path.insert(0, workspace_path)

from src.tools.coffee.coffee_evaluator import (
    evaluate_dimension,
    evaluate_price_dimension,
    check_match_quality,
    get_evaluation_reason
)


def test_scenarios():
    """测试不同场景"""
    print("=" * 80)
    print("测试 Reflection + Evaluation 循环场景")
    print("=" * 80)

    # 场景 1：完美匹配
    print("\n【场景 1】完美匹配 - 应该直接输出")
    print("-" * 80)

    product = {
        "flavor_tags": ["茉莉花", "柑橘"],
        "processing_method": "Natural",
        "roast_level": "Light",
        "origin_country": "Ethiopia"
    }

    user_pref = {
        "flavor_preference": "茉莉花",
        "processing_method": "Natural",
        "roast_level": "Light",
        "origin": "Ethiopia"
    }

    result = evaluate_product(product, user_pref)
    print(f"评估结果: {result['reason']}")
    print(f"是否好匹配: {result['is_good_match']}")
    print(f"是否需要重新推荐: {result['should_retry']}")

    # 场景 2：风味不匹配（应该重新推荐）
    print("\n【场景 2】风味不匹配 - 应该重新推荐")
    print("-" * 80)

    product = {
        "flavor_tags": ["坚果", "巧克力"],
        "processing_method": "Natural",
        "roast_level": "Light",
        "origin_country": "Ethiopia"
    }

    user_pref = {
        "flavor_preference": "茉莉花",
        "processing_method": "Natural",
        "roast_level": "Light",
        "origin": "Ethiopia"
    }

    result = evaluate_product(product, user_pref)
    print(f"评估结果: {result['reason']}")
    print(f"是否好匹配: {result['is_good_match']}")
    print(f"是否需要重新推荐: {result['should_retry']}")
    print("→ 应该重新执行 search_coffee_products")

    # 场景 3：处理法和烘焙度都不匹配（应该重新推荐）
    print("\n【场景 3】处理法和烘焙度都不匹配 - 应该重新推荐")
    print("-" * 80)

    product = {
        "flavor_tags": ["茉莉花", "柑橘"],
        "processing_method": "Washed",
        "roast_level": "Medium",
        "origin_country": "Ethiopia"
    }

    user_pref = {
        "flavor_preference": "茉莉花",
        "processing_method": "Natural",
        "roast_level": "Light",
        "origin": "Ethiopia"
    }

    result = evaluate_product(product, user_pref)
    print(f"评估结果: {result['reason']}")
    print(f"是否好匹配: {result['is_good_match']}")
    print(f"是否需要重新推荐: {result['should_retry']}")
    print("→ 应该重新执行 search_coffee_products")

    # 场景 4：只提供风味偏好（其他维度可以不匹配）
    print("\n【场景 4】只提供风味偏好 - 其他维度可以不匹配")
    print("-" * 80)

    product = {
        "flavor_tags": ["茉莉花", "柑橘"],
        "processing_method": "Washed",  # 不匹配
        "roast_level": "Medium",  # 不匹配
        "origin_country": "Brazil"  # 不匹配
    }

    user_pref = {
        "flavor_preference": "茉莉花"
    }

    result = evaluate_product(product, user_pref)
    print(f"评估结果: {result['reason']}")
    print(f"是否好匹配: {result['is_good_match']}")
    print(f"是否需要重新推荐: {result['should_retry']}")
    print("→ 只要风味匹配，其他维度可以不匹配")

    # 场景 5：3 次循环后仍未达到好匹配
    print("\n【场景 5】模拟 3 次循环后仍未达到好匹配")
    print("-" * 80)

    for i in range(1, 4):
        print(f"\n第 {i} 次尝试:")
        # 模拟每次都风味不匹配
        product = {
            "flavor_tags": ["坚果", "巧克力"],
            "processing_method": "Natural",
            "roast_level": "Light",
            "origin_country": "Ethiopia"
        }

        user_pref = {
            "flavor_preference": "茉莉花",
            "processing_method": "Natural",
            "roast_level": "Light",
            "origin": "Ethiopia"
        }

        result = evaluate_product(product, user_pref)
        print(f"  评估: {result['reason']}")
        print(f"  好匹配: {result['is_good_match']}")

        if i == 3:
            print("\n  → 已达到循环上限（3次），输出最后一次推荐 + 提示信息")
            print('  提示: "在咖啡产品库中未找到最佳匹配的产品，可以尝试一下这款"')
        else:
            print("  → 重新执行 search_coffee_products")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


def evaluate_product(product, user_preferences):
    """评估产品（简化版）"""
    dimension_scores = {
        "flavor": None,
        "processing_method": None,
        "roast_level": None,
        "origin": None
    }

    # 评估各个维度
    dimension_scores["flavor"] = evaluate_dimension(
        product.get("flavor_tags"),
        user_preferences.get("flavor_preference"),
        "flavor"
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

    dimension_scores["origin"] = evaluate_dimension(
        product.get("origin_country"),
        user_preferences.get("origin"),
        "origin"
    )

    # 判断是否是好匹配
    is_good_match = check_match_quality(dimension_scores)

    return {
        "is_good_match": is_good_match,
        "should_retry": not is_good_match,
        "reason": get_evaluation_reason(dimension_scores, is_good_match),
        "dimension_scores": dimension_scores
    }


if __name__ == "__main__":
    test_scenarios()
