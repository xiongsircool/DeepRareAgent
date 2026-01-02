"""
HPO 工具：将表型描述转换为 HPO 术语，并基于 HPO 术语查询关联疾病。

数据源：Jackson Laboratory (JAX) HPO API (https://ontology.jax.org/)
版本：1.0.0
"""

import requests
from pydantic import BaseModel, Field
from typing import List, Optional
from collections import Counter
from langchain_core.tools import tool


# ============================================================
# Pydantic 输入/输出模型定义
# ============================================================

class PhenotypeToHPORequest(BaseModel):
    """表型到 HPO 术语转换的输入参数"""
    phenotypes: List[str] = Field(
        ...,
        description="待标准化的临床表型/症状描述列表（支持中英文），如 ['视力模糊', 'night blindness', '听力下降']"
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="每个表型返回的最佳匹配 HPO 术语数量（范围 1-20，推荐 3-5）"
    )


class HPOEntry(BaseModel):
    """单条 HPO 术语结果"""
    id: str = Field(description="HPO 术语 ID，如 'HP:0000618'")
    name: str = Field(description="HPO 术语标准名称，如 'Blindness'")
    definition: Optional[str] = Field(default=None, description="术语的详细定义说明")
    synonyms: Optional[List[str]] = Field(default=None, description="同义词列表")
    translations: Optional[List[dict]] = Field(default=None, description="多语言翻译信息")


class PhenotypeToHPOResult(BaseModel):
    """表型到 HPO 术语转换的输出结果"""
    results: List[HPOEntry] = Field(
        description="匹配到的 HPO 术语列表（网络异常时可能为空列表）"
    )


class HPOToDiseaseRequest(BaseModel):
    """HPO 术语到疾病查询的输入参数"""
    hpo_ids: List[str] = Field(
        ...,
        description="HPO 术语 ID 列表，如 ['HP:0000618', 'HP:0000365']"
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="返回的疾病候选数量上限（范围 1-50，推荐 5-10）"
    )


class DiseaseEntry(BaseModel):
    """单条疾病候选结果"""
    disease_id: str = Field(description="疾病 ID（OMIM/ORPHA 等数据库编号）")
    name: str = Field(description="疾病名称")
    mondoId: Optional[str] = Field(default=None, description="MONDO 统一疾病本体论 ID")
    description: Optional[str] = Field(default=None, description="疾病描述")
    count: Optional[int] = Field(
        default=None,
        description="该疾病与查询 HPO 术语的共现次数（用于相关性排序）"
    )


class HPOToDiseaseResult(BaseModel):
    """HPO 术语到疾病查询的输出结果"""
    diseases: List[DiseaseEntry] = Field(
        description="按共现次数降序排列的疾病候选列表（网络异常时可能为空列表）"
    )


# ============================================================
# 工具定义
# ============================================================

@tool("phenotype_to_hpo", args_schema=PhenotypeToHPORequest)
def phenotype_to_hpo_tool(phenotypes: List[str], top_k: int = 5) -> PhenotypeToHPOResult:
    """
    将临床表型描述标准化为 HPO（人类表型本体论）术语。

    适用场景：
    - 当患者症状描述不规范时，需要标准化为 HPO 术语
    - 用于罕见病诊断的表型匹配分析前的预处理
    - 与疾病数据库进行关联查询前的术语标准化
    - 医学研究中的表型数据标准化

    数据来源：
    - Jackson Laboratory HPO API (https://ontology.jax.org/)

    Args:
        phenotypes: 临床表型/症状描述列表（支持中英文混合）
        top_k: 每个表型返回的最佳匹配数量（1-20，推荐 3-5）

    Returns:
        PhenotypeToHPOResult: 包含 HPO ID、名称、定义、同义词的标准化结果列表

    错误处理：
        - 网络请求失败的表型会被跳过，不影响其他表型的处理
        - 如果所有请求都失败，返回空列表（results=[]）

    Examples:
        >>> result = phenotype_to_hpo_tool.invoke({
        ...     "phenotypes": ["视力模糊", "night blindness"],
        ...     "top_k": 3
        ... })
        >>> print(f"找到 {len(result.results)} 条 HPO 术语")
        >>> for entry in result.results:
        ...     print(f"{entry.id}: {entry.name}")
    """
    out: List[HPOEntry] = []

    for pheno in phenotypes:
        try:
            resp = requests.get(
                "https://ontology.jax.org/api/hp/search",
                params={"q": pheno, "rows": top_k},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()

            for term in data.get("terms", []):
                entry = HPOEntry(
                    id=term.get("id", ""),
                    name=term.get("name", ""),
                    definition=term.get("definition"),
                    synonyms=term.get("synonyms"),
                    translations=term.get("translations")
                )
                out.append(entry)
        except Exception:
            # 网络请求失败时跳过该表型，继续处理下一个
            continue

    return PhenotypeToHPOResult(results=out)


@tool("hpo_to_diseases", args_schema=HPOToDiseaseRequest)
def hpo_to_diseases_tool(hpo_ids: List[str], top_k: int = 10) -> HPOToDiseaseResult:
    """
    根据 HPO 术语 ID 列表查询常见共现疾病，按关联度排序。

    适用场景：
    - 基于多个 HPO 术语生成罕见病候选列表
    - 用于鉴别诊断中的疾病候选筛选
    - 分析症状组合对应的可能疾病
    - 临床决策支持系统的疾病推荐

    工作原理：
    - 对每个 HPO 术语查询关联的疾病列表
    - 统计疾病在多个术语中的共现次数
    - 按共现次数降序排列，返回最相关的疾病候选

    数据来源：
    - Jackson Laboratory HPO Network Annotation API

    Args:
        hpo_ids: HPO 术语 ID 列表（如 ['HP:0000618', 'HP:0000365']）
        top_k: 返回的疾病候选数量上限（1-50，推荐 5-10）

    Returns:
        HPOToDiseaseResult: 按共现次数降序排列的疾病候选列表，每条包含疾病 ID、名称、描述和共现次数

    错误处理：
        - 网络请求失败的 HPO ID 会被跳过，不影响其他 ID 的处理
        - 如果所有请求都失败，返回空列表（diseases=[]）

    Examples:
        >>> result = hpo_to_diseases_tool.invoke({
        ...     "hpo_ids": ["HP:0000618", "HP:0000365"],
        ...     "top_k": 5
        ... })
        >>> print(f"找到 {len(result.diseases)} 个候选疾病")
        >>> for disease in result.diseases:
        ...     print(f"{disease.name} (共现次数: {disease.count})")
    """
    disease_list = []

    for hpoid in hpo_ids:
        try:
            resp = requests.get(
                f"https://ontology.jax.org/api/network/annotation/{hpoid}",
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()

            for d in data.get("diseases", []):
                disease_list.append(
                    (d.get("id", ""), d.get("name", ""), d.get("mondoId"), d.get("description"))
                )
        except Exception:
            # 网络请求失败时跳过该 HPO ID，继续处理下一个
            continue

    # 统计疾病共现次数并排序
    counter = Counter(disease_list)
    most_common = counter.most_common(top_k)

    out = []
    for ((did, name, mondoId, desc), cnt) in most_common:
        out.append(
            DiseaseEntry(
                disease_id=did,
                name=name,
                mondoId=mondoId,
                description=desc,
                count=cnt
            )
        )

    return HPOToDiseaseResult(diseases=out)


# ============================================================
# 测试入口
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("HPO 工具测试")
    print("=" * 60)

    # 测试 1: 表型转 HPO 术语
    print("\n[测试 1] phenotype_to_hpo_tool")
    print("-" * 60)
    res1 = phenotype_to_hpo_tool.invoke({
        "phenotypes": ["night blindness", "听力损失", "视力模糊"],
        "top_k": 3
    })
    print(f"查询 3 个表型，找到 {len(res1.results)} 条 HPO 术语：")
    for i, h in enumerate(res1.results[:5], 1):  # 只显示前 5 条
        print(f"  {i}. {h.id}: {h.name}")
        if h.definition:
            print(f"     定义: {h.definition[:80]}...")

    # 测试 2: HPO 术语查疾病
    print("\n[测试 2] hpo_to_diseases_tool")
    print("-" * 60)
    hpo_ids = [h.id for h in res1.results[:3] if h.id]  # 取前 3 个 HPO ID
    if hpo_ids:
        print(f"使用 {len(hpo_ids)} 个 HPO ID 查询疾病：{hpo_ids}")
        res2 = hpo_to_diseases_tool.invoke({"hpo_ids": hpo_ids, "top_k": 5})
        print(f"找到 {len(res2.diseases)} 个候选疾病：")
        for i, d in enumerate(res2.diseases, 1):
            print(f"  {i}. {d.name} ({d.disease_id})")
            print(f"     共现次数: {d.count}")
            if d.description:
                print(f"     描述: {d.description[:80]}...")
    else:
        print("未找到有效的 HPO ID，跳过疾病查询测试")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
