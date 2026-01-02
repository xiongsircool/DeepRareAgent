"""
MCP 动态加载 biomcp 生物医学工具。
通过 biomcp-python 暴露基因、蛋白、文献等检索能力。
"""

import asyncio
import os
from typing import Any, Dict, Iterable, List, Optional

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent


BIOMCP_SERVER_CONFIG = {
    "biomcp": {
        "command": "uv",
        "args": ["run", "--with", "biomcp-python", "biomcp", "run"],
        "transport": "stdio",
    }
}


async def load_biomcp_tools(
    server_config: Optional[Dict[str, Dict[str, Any]]] = None
) -> List[Any]:
    """从 biomcp-python MCP 服务动态拉取工具列表。"""
    client = MultiServerMCPClient(server_config or BIOMCP_SERVER_CONFIG)
    return await client.get_tools()


async def build_biomcp_agent(
    llm: Any = None,
    server_config: Optional[Dict[str, Dict[str, Any]]] = None,
    prompt: str = (
        "You are a biomedical research assistant. "
        "Use the available tools to answer user queries about genes, proteins, "
        "diseases, drugs, and clinical trials."
    ),
    debug: bool = False,
):
    """
    构建一个带 biomcp 工具的 ReAct agent。
    如果未提供 llm，则从环境变量读取：
      - BIOMCP_LLM_MODEL
      - BIOMCP_LLM_API_KEY
      - BIOMCP_LLM_BASE_URL
    """
    if llm is None:
        from langchain_openai import ChatOpenAI

        model_name = os.getenv("BIOMCP_LLM_MODEL", "glm-4.1v-thinking-flash")
        api_key = os.getenv("BIOMCP_LLM_API_KEY")
        base_url = os.getenv("BIOMCP_LLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
        if not api_key:
            raise ValueError("BIOMCP_LLM_API_KEY is required to build biomcp agent.")
        llm = ChatOpenAI(api_key=api_key, base_url=base_url, model=model_name)

    biomcp_tools = await load_biomcp_tools(server_config=server_config)
    agent = create_react_agent(
        model=llm,
        tools=biomcp_tools,
        debug=debug,
        prompt=prompt,
    )
    return agent


def load_biomcp_tools_sync(
    server_config: Optional[Dict[str, Dict[str, Any]]] = None
) -> List[Any]:
    """
    同步拉取 biomcp 工具（在无事件循环场景下使用）。
    注意：如果已有事件循环运行，请改用异步接口。
    """
    return asyncio.run(load_biomcp_tools(server_config=server_config))


async def demo_query(user_query: str = "请帮我查找与BRCA1基因相关的疾病有哪些？") -> Any:
    """示例：运行一次查询并返回 agent 输出。"""
    agent = await build_biomcp_agent(debug=True)
    return agent.invoke({"messages": [("user", user_query)]})


if __name__ == "__main__":
    result = asyncio.run(demo_query())
    print(result)
