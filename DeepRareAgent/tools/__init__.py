"""
工具聚合模块

将本目录下的工具统一收口,便于在 deep agent 中一次性导入。
包含:
- HPO 本体查询工具
- 医学文献检索工具 (PubMed, LitSense)
- 通用搜索工具 (百度, Wikipedia)
- BioMCP 工具集成 (可选)
- 患者信息管理工具
- 证据管理工具
"""

# === 标准库导入 ===
import logging
from typing import Any, Dict, List

# === 第三方库导入 ===
from langchain_core.tools import tool

# === 本地工具导入 ===
# HPO 本体工具
from .hpo_tools import hpo_to_diseases_tool, phenotype_to_hpo_tool

# 搜索工具
from .baidu_tools import search_baidu_tool
from .wiki_tools import search_wikipedia_tool

# 医学文献工具
from .litsense_tool import lit_sense_search
from .pubmed_tools import search_pubmed

# BioMCP 工具 (可选,需要外部服务)
from .biomcp_tool import (
    build_biomcp_agent,
    load_biomcp_tools,
    load_biomcp_tools_sync,
)

# 患者信息与证据管理
from .evidencemanager import extract_evidences, save_evidences
from .patientinfo import PatientInfoManger


# === 工具列表构建函数 ===
def get_all_tools() -> List[Any]:
    """
    返回基础工具列表 (不包含 BioMCP)。

    Returns:
        包含 HPO、搜索和文献检索工具的列表
    """
    return [
        # HPO 本体工具
        phenotype_to_hpo_tool,
        hpo_to_diseases_tool,
        # 搜索工具
        search_baidu_tool,
        search_wikipedia_tool,
        # 文献检索工具
        search_pubmed,
        lit_sense_search,  # 直接使用原始工具
    ]


async def get_all_tools_async(include_biomcp: bool = False) -> List[Any]:
    """
    异步获取工具列表,可选加载 BioMCP 工具。

    Args:
        include_biomcp: 是否包含 BioMCP 工具 (需要启动 biomcp-python 服务)

    Returns:
        工具列表,如果启用则包含 BioMCP 工具
    """
    tools = get_all_tools()

    if include_biomcp:
        try:
            biomcp_tools = await load_biomcp_tools()
            tools.extend(biomcp_tools)
        except Exception as exc:
            logging.warning("加载 BioMCP 工具失败: %s", exc)

    return tools


def get_all_tools_with_biomcp_sync() -> List[Any]:
    """
    同步获取全部工具 (包含 BioMCP)。

    注意: 如果当前线程已有事件循环,请改用 get_all_tools_async(include_biomcp=True)

    Returns:
        包含 BioMCP 的完整工具列表
    """
    tools = get_all_tools()

    try:
        tools.extend(load_biomcp_tools_sync())
    except Exception as exc:
        logging.warning("同步加载 BioMCP 工具失败: %s", exc)

    return tools


# === 静态工具列表 ===
# 直接暴露的静态列表,方便快速导入 (不包含 BioMCP,避免启动外部进程)
ALL_TOOLS: List[Any] = get_all_tools()

# 目前主要用于测试多专家诊断节点时使用的基础工具用于延长记忆时常所以作为附加工具
#TODO:后续需要把所有工具都移到这里该变量中同时或者移除删除目前变量改用ALL_TOOLS
default_TOOL_EXCLUDE_LIST = {
    "save_evidences": save_evidences,
    "extract_evidences": extract_evidences,
    "phenotype_to_hpo_tool":phenotype_to_hpo_tool,
    "hpo_to_diseases_tool":hpo_to_diseases_tool,
    "search_baidu_tool":search_baidu_tool,
    "search_wikipedia_tool":search_wikipedia_tool,
    "search_pubmed":search_pubmed,
    "lit_sense_search": lit_sense_search,  # 更新为原始工具
}






# === 公共接口导出 ===
__all__ = [
    # 工具列表与加载函数
    "ALL_TOOLS",
    "default_TOOL_EXCLUDE_LIST",
    "get_all_tools",
    "get_all_tools_async",
    "get_all_tools_with_biomcp_sync",
    # HPO 工具
    "phenotype_to_hpo_tool",
    "hpo_to_diseases_tool",
    # 搜索工具
    "search_baidu_tool",
    "search_wikipedia_tool",
    # 文献检索工具
    "search_pubmed",
    "lit_sense_search",  # 更新导出
    # BioMCP 工具
    "load_biomcp_tools",
    "load_biomcp_tools_sync",
    "build_biomcp_agent",
    # 管理工具
    "PatientInfoManger",
]