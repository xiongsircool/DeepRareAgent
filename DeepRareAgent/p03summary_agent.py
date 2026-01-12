# -*- coding: utf-8 -*-
"""
汇总诊断智能体 (P03)

整合多个专家组的诊断报告，生成符合临床规范的综合诊断报告。
"""

import re
from typing import Any, Dict
from pathlib import Path
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from DeepRareAgent.config import settings
from DeepRareAgent.schema import MainGraphState
from DeepRareAgent.utils.model_factory import create_llm_from_config
from DeepRareAgent.utils.report_utils import process_expert_report_references


def _load_system_prompt() -> str:
    """
    加载系统提示词
    
    Returns:
        系统提示词内容
        
    Raises:
        FileNotFoundError: 如果提示词文件不存在
    """
    prompt_path = settings.summary_agent.system_prompt_path
    
    if not Path(prompt_path).exists():
        raise FileNotFoundError(
            f"汇总智能体提示词文件不存在: {prompt_path}\n"
            f"请检查配置文件中的 summary_agent.system_prompt_path"
        )
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def _format_expert_reports(
    reports: Dict[str, str],
    expert_pool: Dict[str, Any]
) -> str:
    """
    格式化专家报告，处理引用并整合
    
    Args:
        reports: 专家组报告字典 {group_id: report}
        expert_pool: 专家池，包含证据列表
        
    Returns:
        格式化后的所有报告文本
    """
    formatted_reports = []
    
    for group_id, report in reports.items():
        # 处理证据引用
        expert_data = expert_pool.get(group_id, {})
        evidences = expert_data.get("evidences", [])
        
        if evidences:
            report = process_expert_report_references(report, evidences)
        
        # 格式化单个报告
        formatted_report = f"""
{'=' * 60}
专家组: {group_id}
{'=' * 60}

{report}
"""
        formatted_reports.append(formatted_report)
    
    return "\n".join(formatted_reports)


def _resolve_evidence_references(report_text: str, evidence_mapping: Dict[str, str]) -> str:
    """
    解析报告中的 <ref>group_id.index</ref> 标签，并将对应的证据内容追加到报告末尾。
    
    使用稳定的 group_id.index 格式，确保证据引用不会混淆。
    
    Args:
        report_text: 汇总报告文本
        evidence_mapping: 证据映射字典 {group_id.index: evidence_content}
        
    Returns:
        追加了证据详情的报告文本
    """
    if not report_text or not evidence_mapping:
        return report_text
    
    # 1. 查找所有唯一的引用键
    # 匹配 <ref>group_id.number</ref> 格式
    ref_pattern = re.compile(r'<ref>([a-zA-Z0-9_]+\.\d+)</ref>')
    matches = ref_pattern.findall(report_text)
    
    if not matches:
        return report_text
    
    # 去重并保持顺序
    seen = set()
    ref_keys = []
    for match in matches:
        if match not in seen:
            seen.add(match)
            ref_keys.append(match)
    
    # 2. 提取对应的证据
    extracted_evidences = []
    for ref_key in ref_keys:
        if ref_key in evidence_mapping:
            evidence_content = evidence_mapping[ref_key]
            extracted_evidences.append(f"[{ref_key}] {evidence_content}")
        else:
            # 如果引用的键不存在，记录警告但不中断
            print(f"[WARN] 未找到证据引用: {ref_key}")
    
    if not extracted_evidences:
        return report_text
    
    # 3. 拼接到报告末尾
    formatted_evidence_section = "\n\n#### 引用证据详情\n" + "\n".join(extracted_evidences)
    
    return report_text + formatted_evidence_section


def summary_node(state: MainGraphState, config: RunnableConfig) -> Dict[str, Any]:
    """
    汇总节点：整合多位专家的诊断报告，生成最终综合诊断
    
    Args:
        state: 主图状态，包含专家组报告
        config: 运行配置
        
    Returns:
        包含最终报告的状态更新
        
    Raises:
        ValueError: 如果没有专家报告
        FileNotFoundError: 如果提示词文件不存在
        Exception: LLM 调用失败时抛出
    """
    print("\n" + "=" * 80)
    print(">>> [汇总节点] 开始整合专家诊断报告")
    print("=" * 80)
    
    # 1. 验证输入
    blackboard = state.get("blackboard", {})
    reports = blackboard.get("published_reports", {})
    
    if not reports:
        error_msg = "错误：未找到任何专家报告，无法生成综合诊断"
        print(f"[ERROR] {error_msg}")
        raise ValueError(error_msg)
    
    print(f"\n[INFO] 专家组数量: {len(reports)}")
    for group_id in reports.keys():
        print(f"   - {group_id}")
    
    # 2. 格式化专家报告并构建稳定的证据映射
    print("\n[NOTE] 整合专家报告...")
    expert_pool = state.get("expert_pool", {})
    all_reports_text = _format_expert_reports(reports, expert_pool)
    
    # 构建稳定的证据映射：为每个专家组的证据创建唯一标识
    # 格式: {group_id}.{evidence_index} -> evidence_content
    # 这样LLM可以明确引用特定专家的证据，避免混淆
    evidence_mapping = {}
    evidence_count = 0
    
    for group_id in sorted(reports.keys()):  # 排序确保顺序一致
        expert_data = expert_pool.get(group_id, {})
        evidences = expert_data.get("evidences", [])
        
        for idx, evidence in enumerate(evidences, start=1):
            # 创建稳定的引用键: group_id.index
            ref_key = f"{group_id}.{idx}"
            evidence_mapping[ref_key] = evidence
            evidence_count += 1
    
    print(f"📚 构建证据映射: {evidence_count} 条证据来自 {len(reports)} 个专家组")
    
    # 生成证据引用指南，告知LLM如何正确引用
    evidence_guide = ""
    if evidence_mapping:
        evidence_guide = "\n\n【证据引用指南】\n"
        evidence_guide += "如需引用专家报告中的证据，请使用格式: <ref>专家组ID.证据编号</ref>\n"
        evidence_guide += "可用的证据引用:\n"
        for group_id in sorted(reports.keys()):
            expert_data = expert_pool.get(group_id, {})
            evidences = expert_data.get("evidences", [])
            if evidences:
                evidence_guide += f"  - {group_id}: 证据 1-{len(evidences)} (引用示例: <ref>{group_id}.1</ref>)\n"
    
    # 3. 加载系统提示词
    print("📖 加载系统提示词...")
    system_prompt = _load_system_prompt()
    
    # 4. 构建用户提示词（支持自定义格式）
    patient_portrait = state.get("patient_portrait", "")
    summary_style = state.get("summary_style", "")
    
    # 获取当前时间
    current_time = datetime.now().strftime("%Y-%m-%d")

    # 如果有自定义格式要求，使用自定义；否则使用默认
    if summary_style:
        # 用户自定义报告格式
        format_instruction = f"""
请按照以下格式要求生成报告：

{summary_style}

报告生成日期：{current_time}
"""
    else:
        # 默认格式要求
        format_instruction = f"""
请严格按照系统提示词的标准格式，直接生成一份临床诊断报告。

报告生成日期：{current_time}

要求：
- 明确给出诊断结论，不要描述专家讨论过程
- 提供具体的检查和治疗建议
- 包含实用的随访计划和注意事项
- 使用患者和医生都能理解的专业语言
- 可在关键诊断依据处使用 <ref>专家组ID.证据编号</ref> 引用专家证据，增强可追溯性
"""
    
    user_prompt = f"""以下是患者的临床信息和多位专家的诊断分析，请为患者出具正式的罕见病诊断报告。

{'【患者信息】' + chr(10) + patient_portrait + chr(10) if patient_portrait else ''}
【专家诊断分析】
{all_reports_text}
{evidence_guide}
{format_instruction}
"""
    
    # 5. 调用 LLM 生成报告
    print("[LLM] 调用 LLM 生成综合诊断报告...")
    
    llm = create_llm_from_config(settings.summary_agent)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    response = llm.invoke(messages)
    final_report = response.content
    
    # 处理汇总报告中的证据引用（使用稳定的group_id.index映射）
    if evidence_mapping:
        final_report = _resolve_evidence_references(final_report, evidence_mapping)
    
    print(f"\n[SUCCESS] 综合报告生成成功（{len(final_report)} 字符）")
    print("=" * 80 + "\n")
    
    # 6. 返回结果
    return {
        "messages": [AIMessage(content=final_report)],
        "final_report": final_report
    }


# 导出
__all__ = ["summary_node"]


# 测试代码
if __name__ == "__main__":
    """测试汇总节点"""
    from DeepRareAgent.schema import SharedBlackboard

    # 模拟测试数据
    test_state = {
        "patient_portrait": "35岁男性，四肢疼痛10年，皮肤血管角质瘤5年，家族史母亲肾衰竭",
        "blackboard": {
            "published_reports": {
                "group_1": """# 诊断报告 - 专家组1

## 诊断意见
法布雷病（Fabry Disease）- 高度怀疑<ref>1</ref>

## 主要依据
1. 四肢阵发性疼痛（典型 Fabry 危象）
2. 少汗症（自主神经受累）
3. 皮肤血管角质瘤（特征性表现）<ref>2</ref>
4. 家族史符合 X-连锁遗传

## 建议检查
- α-半乳糖苷酶A活性检测
- GLA基因测序
""",
                "group_2": """# 诊断报告 - 专家组2

## 诊断意见
法布雷病（Fabry Disease）- 高度可能

## 补充证据
1. 肾功能异常（肌酐升高）
2. 心脏超声异常（左室增厚）
3. 听力下降（感音神经性）

## 鉴别诊断
需排除其他溶酶体贮积症
"""
            }
        },
        "patient_info": {},
        "summary_with_dialogue": "",
        "expert_pool": {
            "group_1": {
                "evidences": [
                    "患者自述手脚疼痛，像烧灼一样，尤其夏天严重。",
                    "体检发现躯干部位有红色小点，压之不退色。"
                ]
            },
            "group_2": {
                "evidences": []
            }
        },
        "round_count": 2,
        "max_rounds": 3
    }

    print("\n" + "=" * 80)
    print("测试汇总节点")
    print("=" * 80)

    result = summary_node(test_state, {})

    print("\n生成的综合报告：")
    print("=" * 80)
    print(result.get("final_report", "无报告"))
    print("=" * 80)
