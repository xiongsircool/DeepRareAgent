"""
LitSense 文献语义搜索工具集

这个模块提供了用于 NCBI LitSense API 的工具，用于执行语句/片段级别的生物医学文献语义检索。

主要功能：
1. lit_sense_search: 执行语义检索，返回相关的文献片段和评分

数据来源：
- NCBI LitSense API: https://www.ncbi.nlm.nih.gov/research/litsense-api/

使用场景：
- 精确的医学文献片段检索
- 疾病相关证据收集
- 医学研究支持
- 临床决策证据检索
- 个性化医疗研究

特点：
- 支持语义检索而非简单关键词匹配
- 返回文献片段而非整篇文档
- 提供相关性评分排序
- 包含 PubMed ID 和 PMC ID 引用信息
- 支持结果重排序 (rerank)

安装依赖：
pip install requests pydantic

作者: Rare Diagnosis Agent Team
版本: 1.0.0
"""

import requests
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool


class LitSenseQueryResult(BaseModel):
    """LitSense 查询单条结果"""
    score: float
    pmcid: Optional[str]
    pmid: Optional[int]
    text: str
    annotations: List[str]
    section: Optional[str]


class LitSenseSearchArgs(BaseModel):
    """LitSense 搜索参数模型"""
    query: str = Field(..., description="语义检索的句子或片段")
    rerank: bool = Field(True, description="是否让 LitSense 重新排序结果")
    base_url: str = Field(
        "https://www.ncbi.nlm.nih.gov/research/litsense-api/api/",
        description="LitSense API 基础地址"
    )


class LitSenseSearchResult(BaseModel):
    """LitSense 搜索结果模型"""
    query: str
    results: List[LitSenseQueryResult]
    error: Optional[str] = None


@tool("lit_sense_search", args_schema=LitSenseSearchArgs)
def lit_sense_search(
    query: str,
    rerank: bool = True,
    base_url: str = "https://www.ncbi.nlm.nih.gov/research/litsense-api/api/"
) -> Dict[str, Any]:
    """LitSense 语义检索，返回片段与评分"""
    params = {
        "query": query,
        "rerank": "true" if rerank else "false"
    }
    try:
        resp = requests.get(base_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return {
            "query": query,
            "results": [],
            "error": str(exc)
        }

    results = []
    for rec in data:
        results.append({
            "score": rec.get("score", 0.0),
            "pmcid": rec.get("pmcid"),
            "pmid": rec.get("pmid"),
            "text": rec.get("text", ""),
            "annotations": rec.get("annotations", []),
            "section": rec.get("section")
        })

    return {
        "query": query,
        "results": results,
        "error": None
    }


# --- 测试入口 ---
if __name__ == "__main__":
    q = "Breast cancers with HER2 amplification"
    res = lit_sense_search.invoke({"query": q, "rerank": True})
    print("Query:", res["query"])
    if res.get("error"):
        print("Error:", res["error"])
    else:
        for i, rec in enumerate(res["results"][:5]):
            print(f"--- Result {i+1} ---")
            print("Score:", rec["score"])
            print("PMID:", rec.get("pmid"), "PMC:", rec.get("pmcid"))
            print("Text:", rec["text"])
            print("Annotations:", rec["annotations"])
            print("Section:", rec.get("section"))
            print()