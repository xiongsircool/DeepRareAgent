"""
PubMed 工具：使用 Entrez API 搜索生物医学文献，获取权威研究证据。

数据源：美国国家医学图书馆 PubMed 数据库 (https://pubmed.ncbi.nlm.nih.gov/)
依赖：biopython
版本：1.0.0
"""

from typing import List
from Bio import Entrez, Medline
from pydantic import BaseModel, Field
from langchain_core.tools import tool


# ============================================================
# Pydantic 输入/输出模型定义
# ============================================================

class PubMedSearchArgs(BaseModel):
    """PubMed 文献检索的输入参数"""
    query: str = Field(
        ...,
        description="医学检索关键词或查询语句，如疾病名称、基因名、症状、药物名等"
    )
    max_results: int = Field(
        default=3,
        ge=1,
        le=20,
        description="返回的文献条目数量上限（范围 1-20，推荐 3-5 篇以获取最相关结果）"
    )
    email: str = Field(
        default="demo@demo.com",
        description="联系邮箱（PubMed API 使用要求，用于追踪滥用行为）"
    )


class PubMedArticle(BaseModel):
    """单篇 PubMed 文献记录"""
    pmid: str = Field(description="PubMed ID（文献唯一标识符）")
    title: str = Field(description="文章标题")
    abstract: str = Field(description="摘要内容（可能为空字符串）")
    year: str = Field(description="发表年份或日期信息")
    journal: str = Field(description="发表期刊名称")


class PubMedSearchResult(BaseModel):
    """PubMed 文献检索的输出结果"""
    items: List[PubMedArticle] = Field(
        description="检索到的文献列表（网络异常或无结果时为空列表）"
    )


# ============================================================
# 工具定义
# ============================================================

@tool("search_pubmed", args_schema=PubMedSearchArgs)
def search_pubmed(
    query: str,
    max_results: int = 3,
    email: str = "demo@demo.com"
) -> PubMedSearchResult:
    """
    在 PubMed 数据库中搜索生物医学文献，获取权威研究证据。

    适用场景：
    - 查找特定疾病的最新研究进展和临床表现
    - 验证罕见病的诊断标准和鉴别诊断要点
    - 获取基因变异与疾病关联的文献证据
    - 查询药物治疗方案和临床试验结果
    - 查找病例报告和综述文章

    不适用场景：
    - 获取中文医学内容（请使用百度搜索工具）
    - 查询基础医学概念定义（请使用维基百科工具）
    - 需要语义级片段检索（请使用 LitSense 工具）

    数据来源：
    - 美国国家医学图书馆 PubMed 数据库
    - 包含超过 3600 万条生物医学文献索引

    Args:
        query: 医学检索关键词（支持复杂查询语法，如 "diabetes AND insulin resistance"）
        max_results: 返回文献数量（1-20，推荐 3-5 篇以保证质量）
        email: 联系邮箱（必需，用于符合 NCBI API 使用规范）

    Returns:
        PubMedSearchResult: 包含 PMID、标题、摘要、年份、期刊的文献列表

    错误处理：
        - 网络请求失败时返回空列表（items=[]）
        - API 错误时返回空列表
        - 无检索结果时返回空列表

    Examples:
        >>> result = search_pubmed.invoke({
        ...     "query": "Retinitis pigmentosa gene therapy",
        ...     "max_results": 5,
        ...     "email": "researcher@example.com"
        ... })
        >>> print(f"找到 {len(result.items)} 篇文献")
        >>> for article in result.items:
        ...     print(f"{article.pmid}: {article.title}")
        ...     print(f"期刊: {article.journal} ({article.year})")

    Note:
        - PubMed 摘要可能为空（某些老文献或特殊类型文献）
        - 建议使用具体的医学术语以提高检索精度
        - 可使用布尔运算符（AND、OR、NOT）构建复杂查询
    """
    try:
        # 设置 NCBI 邮箱（API 要求）
        Entrez.email = email

        # 第一步：搜索文献 ID
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
        record = Entrez.read(handle)
        id_list = record.get("IdList", [])

        if not id_list:
            return PubMedSearchResult(items=[])

        # 第二步：获取文献详细信息
        handle = Entrez.efetch(
            db="pubmed",
            id=",".join(id_list),
            rettype="medline",
            retmode="text"
        )
        records = list(Medline.parse(handle))

        # 第三步：构造结构化结果
        articles: List[PubMedArticle] = []
        for rec in records:
            articles.append(
                PubMedArticle(
                    pmid=rec.get("PMID", ""),
                    title=rec.get("TI", ""),
                    abstract=rec.get("AB", ""),
                    year=str(rec.get("DP", "")),
                    journal=rec.get("JT", "")
                )
            )

        return PubMedSearchResult(items=articles)

    except Exception:
        # 网络异常或 API 错误时返回空结果（不抛出异常）
        return PubMedSearchResult(items=[])


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("PubMed 工具测试")
    print("=" * 60)

    # 测试查询
    print("\n[测试] search_pubmed")
    print("-" * 60)
    print("查询关键词: 'Retinitis pigmentosa gene therapy'")
    print("返回数量: 3 篇")

    result = search_pubmed.invoke({
        "query": "Retinitis pigmentosa gene therapy",
        "max_results": 3,
        "email": "demo@demo.com"
    })

    print(f"\n找到 {len(result.items)} 篇文献：\n")

    for i, article in enumerate(result.items, 1):
        print(f"{i}. PMID: {article.pmid}")
        print(f"   标题: {article.title}")
        print(f"   期刊: {article.journal} ({article.year})")
        if article.abstract:
            abstract_preview = article.abstract[:200] + "..." if len(article.abstract) > 200 else article.abstract
            print(f"   摘要: {abstract_preview}")
        else:
            print(f"   摘要: (无)")
        print()

    print("=" * 60)
    print("测试完成")
    print("=" * 60)
