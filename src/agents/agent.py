"""
Coffee Recommendation Agent
专业的手冲咖啡推荐顾问，基于用户喜好推荐咖啡豆并提供冲煮建议
"""

import os
import json
from typing import Annotated
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage
from coze_coding_utils.runtime_ctx.context import default_headers
from storage.memory.memory_saver import get_memory_saver
from tools.coffee.coffee_updater import update_coffee_database
from tools.coffee.coffee_recommender import search_coffee_products
from tools.coffee.keyword_expander import expand_flavor_keywords
from tools.coffee.price_matcher import check_price_match, parse_user_price_range
from tools.coffee.brewing_knowledge import get_brewing_knowledge

LLM_CONFIG = "config/agent_llm_config.json"

# 默认保留最近 20 轮对话 (40 条消息)
MAX_MESSAGES = 40

def _windowed_messages(old, new):
    """滑动窗口: 只保留最近 MAX_MESSAGES 条消息"""
    return add_messages(old, new)[-MAX_MESSAGES:]  # type: ignore

class AgentState(MessagesState):
    messages: Annotated[list[AnyMessage], _windowed_messages]

def build_agent(ctx=None):
    """构建咖啡推荐 Agent"""
    workspace_path = os.getenv("COZE_WORKSPACE_PATH", "/workspace/projects")
    config_path = os.path.join(workspace_path, LLM_CONFIG)

    # 读取配置文件
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    # 获取环境变量
    api_key = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
    base_url = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL")

    # 初始化 LLM
    llm = ChatOpenAI(
        model=cfg['config'].get("model"),
        api_key=api_key,
        base_url=base_url,
        temperature=cfg['config'].get('temperature', 0.7),
        streaming=True,
        timeout=cfg['config'].get('timeout', 600),
        extra_body={
            "thinking": {
                "type": cfg['config'].get('thinking', 'disabled')
            }
        },
        default_headers=default_headers(ctx) if ctx else {}
    )

    # 构建 Agent，添加工具
    return create_agent(
        model=llm,
        system_prompt=cfg.get("sp"),
        tools=[
            update_coffee_database,
            search_coffee_products,
            expand_flavor_keywords,
            check_price_match,
            parse_user_price_range,
            get_brewing_knowledge
        ],
        checkpointer=get_memory_saver(),
        state_schema=AgentState,
    )
