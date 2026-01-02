"""
百度搜索工具集

这个模块提供了用于百度搜索的工具，主要用于获取中文医学信息的搜索结果。

主要功能：
1. search_baidu: 使用百度搜索引擎获取医学和健康相关信息

数据来源：
- 百度搜索引擎 (Baidu Search)

使用场景：
- 中文医学信息搜索
- 疾病症状查询
- 医学健康资讯获取
- 患者教育信息收集
- 医学研究动态了解

注意事项：
- 依赖第三方库 baidusearch
- 搜索结果来自公开网页，请谨慎验证信息的准确性
- 建议结合专业医学数据库和权威来源使用

安装依赖：
pip install baidusearch

作者: Rare Diagnosis Agent Team
版本: 1.0.0
"""

from typing import List
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# 这里假设你安装了 `python-baidusearch` 库
try:
    from baidusearch.baidusearch import search as baidu_search
except ImportError:
    baidu_search = None

class BaiduSearchRequest(BaseModel):
    query: str = Field(..., description="中文医学或症状关键词")
    num_results: int = Field(5, description="返回结果条数上限")

class BaiduResultItem(BaseModel):
    title: str
    summary: str

class BaiduSearchResult(BaseModel):
    results: List[BaiduResultItem]

@tool("search_baidu", args_schema=BaiduSearchRequest)
def search_baidu_tool(query: str, num_results: int = 5) -> BaiduSearchResult:
    """百度检索医学信息，失败返回空结果"""
    if baidu_search is None:
        return BaiduSearchResult(results=[])
    try:
        hits = baidu_search(query, num_results=num_results)
    except Exception:
        # 如果搜索失败，返回空结果
        return BaiduSearchResult(results=[])

    out = []
    for item in hits:
        # item 是 dict，通常包含 `title`, `abstract` (or summary), `url`
        out.append(BaiduResultItem(
            title=item.get("title", ""),
            summary=item.get("abstract", "")
        ))
    return BaiduSearchResult(results=out)


# --- main 测试 ---
if __name__ == "__main__":
    res = search_baidu_tool.invoke({"query": "视网膜色素变性", "num_results": 3})
    print("=== 百度搜索 结果 ===")
    for r in res.results:
        print(f"title: {r.title}\nsummary: {r.summary}\n---")
