"""
Keyword Expansion Tool
使用 LLM 将泛指关键词扩展为具体的风味标签
"""

from langchain.tools import tool
from typing import List, Optional
import logging
import json
import re
from sqlalchemy import text

logger = logging.getLogger(__name__)


def get_db_session():
    """获取数据库会话"""
    from storage.database.db import get_engine
    from sqlalchemy.orm import sessionmaker
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def get_existing_flavor_tags() -> List[str]:
    """
    从数据库获取所有现有的风味标签

    Returns:
        List[str]: 风味标签列表
    """
    try:
        session = get_db_session()

        result = session.execute(
            text("SELECT DISTINCT unnest(flavor_tags) FROM coffee_products WHERE flavor_tags IS NOT NULL")
        )
        rows = result.fetchall()

        session.close()

        tags = []
        for row in rows:
            if row[0]:
                # unnest 返回的是单个标签，不需要再 split
                tag = row[0].strip()
                if tag:
                    tags.append(tag)

        # 去重并排序
        unique_tags = sorted(set(tags))

        logger.info(f"获取到 {len(unique_tags)} 个风味标签: {unique_tags}")
        return unique_tags

    except Exception as e:
        logger.error(f"获取风味标签失败: {e}")
        return []


def expand_keywords_with_llm(user_keywords: str, existing_tags: List[str]) -> List[str]:
    """
    使用 LLM 将用户输入的泛指关键词扩展为具体的风味标签

    Args:
        user_keywords: 用户输入的关键词（如："花香、果香"）
        existing_tags: 数据库中现有的所有风味标签

    Returns:
        List[str]: 扩展后的具体风味标签列表
    """
    try:
        from coze_coding_dev_sdk import LLMClient
        from coze_coding_utils.log.write_log import request_context
        from coze_coding_utils.runtime_ctx.context import new_context
        from langchain_core.messages import SystemMessage, HumanMessage

        ctx = request_context.get() or new_context(method="keyword_expansion")

        client = LLMClient(ctx=ctx)

        # 构建 prompt
        prompt = f"""你是一位咖啡风味专家，请将用户输入的泛指风味关键词转换为具体的风味标签。

【现有风味标签库】
{json.dumps(existing_tags, ensure_ascii=False)}

【用户输入】
{user_keywords}

【任务】
1. 分析用户输入的风味关键词，理解其意图
2. 从现有风味标签库中找到最匹配的具体标签
3. 如果用户输入的是泛指词（如"花香"），找出对应的具体标签（如"茉莉花"、"玫瑰"等）
4. 返回最相关的 3-5 个具体标签

【输出格式】
严格按照 JSON 格式输出，不要包含任何其他文字：
{{"tags": ["标签1", "标签2", "标签3"]}}

示例：
输入: "花香"
输出: {{"tags": ["茉莉花", "玫瑰", "洋甘菊"]}}

输入: "果香"
输出: {{"tags": ["柑橘", "草莓", "葡萄柚"]}}

输入: "坚果巧克力"
输出: {{"tags": ["黑巧克力", "焦糖", "坚果"]}}

现在请处理用户输入：
"""

        # 调用 LLM
        response = client.invoke(
            messages=[
                SystemMessage(content="你是咖啡风味专家，擅长将泛指关键词转换为具体的风味标签。"),
                HumanMessage(content=prompt)
            ],
            temperature=0.3
        )

        # 解析响应
        response_text = str(response.content).strip()

        # 提取 JSON 部分
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            result = json.loads(json_str)
            tags = result.get('tags', [])
            logger.info(f"关键词扩展成功: '{user_keywords}' -> {tags}")
            return tags
        else:
            logger.warning(f"LLM 响应格式错误: {response_text}")
            return []

    except Exception as e:
        logger.error(f"LLM 关键词扩展失败: {e}")
        # 降级：直接返回用户输入的关键词
        return [k.strip() for k in user_keywords.split(',') if k.strip()]


@tool
def expand_flavor_keywords(user_keywords: str) -> str:
    """
    将泛指风味关键词扩展为具体的风味标签

    该工具会：
    1. 读取数据库中的所有现有风味标签
    2. 使用 LLM 分析用户输入的泛指关键词
    3. 从现有标签中找到最匹配的具体标签
    4. 返回扩展后的具体标签列表

    例如：
    - "花香" -> ["茉莉花", "玫瑰", "洋甘菊"]
    - "果香" -> ["柑橘", "草莓", "葡萄柚"]
    - "坚果巧克力" -> ["黑巧克力", "焦糖", "坚果"]

    Args:
        user_keywords: 用户输入的风味关键词，多个关键词用逗号或顿号分隔
                       如："花香、果香" 或 "花香,果香"

    Returns:
        str: 扩展后的具体风味标签列表的 JSON 格式字符串
             格式: {"tags": ["标签1", "标签2", ...]}
    """
    try:
        logger.info(f"扩展风味关键词: {user_keywords}")

        # 获取现有风味标签
        existing_tags = get_existing_flavor_tags()

        if not existing_tags:
            logger.warning("数据库中没有风味标签数据")
            return json.dumps({
                "status": "warning",
                "message": "数据库中没有风味标签数据，无法扩展",
                "tags": []
            }, ensure_ascii=False, indent=2)

        # 使用 LLM 扩展关键词
        expanded_tags = expand_keywords_with_llm(user_keywords, existing_tags)

        if not expanded_tags:
            logger.warning("关键词扩展失败，返回原始关键词")
            # 降级：返回原始关键词
            original_tags = [k.strip() for k in re.split(r'[,、]', user_keywords) if k.strip()]
            return json.dumps({
                "status": "warning",
                "message": "关键词扩展失败，返回原始关键词",
                "original_keywords": user_keywords,
                "tags": original_tags
            }, ensure_ascii=False, indent=2)

        return json.dumps({
            "status": "success",
            "original_keywords": user_keywords,
            "tags": expanded_tags,
            "message": f"已将 '{user_keywords}' 扩展为具体标签: {', '.join(expanded_tags)}"
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"扩展风味关键词失败: {e}")
        return json.dumps({
            "status": "error",
            "message": f"扩展失败: {str(e)}",
            "tags": []
        }, ensure_ascii=False, indent=2)
