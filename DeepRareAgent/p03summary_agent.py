# -*- coding: utf-8 -*-
"""
汇总诊断智能体 (P03)
- 整合多个专家组的诊断报告
- 生成综合的最终诊断报告
- 符合临床诊断文书规范
"""
from typing import Any, Dict
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from DeepRareAgent.config import settings
from DeepRareAgent.schema import MainGraphState
from DeepRareAgent.utils.model_factory import create_llm_from_config


def summary_node(state: MainGraphState, config: RunnableConfig) -> Dict[str, Any]:
    """
    汇总节点：整合多位专家的诊断报告，生成最终综合诊断

    输入：
        state: MainGraphState，包含 blackboard.published_reports

    输出：
        更新后的状态，包含 final_report 字段
    """
    print("\n" + "=" * 60)
    print(">>> [汇总节点] 开始整合专家诊断报告...")
    print("=" * 60)

    # 1. 提取专家报告
    blackboard = state.get("blackboard", {})
    reports = blackboard.get("published_reports", {})

    if not reports:
        print("    警告：未找到任何专家报告，返回空报告")
        error_msg = "错误：未能获取专家诊断报告，无法生成综合诊断。"
        return {
            "messages": [AIMessage(content=error_msg)],
            "final_report": error_msg
        }

    print(f"    专家组数量: {len(reports)}")
    for group_id in reports.keys():
        print(f"    - {group_id}")

    # 2. 整合所有专家报告
    all_reports_text = ""
    for group_id, report in reports.items():
        all_reports_text += f"\n\n{'=' * 60}\n"
        all_reports_text += f"专家组: {group_id}\n"
        all_reports_text += f"{'=' * 60}\n\n"
        all_reports_text += report

    # 3. 获取患者画像（可选，用于报告开头）
    patient_portrait = state.get("patient_portrait", "")

    # 4. 构建汇总提示词
    user_prompt = f"""请基于以下专家组的诊断报告，生成一份综合的最终诊断报告。

{'患者信息：' + chr(10) + patient_portrait + chr(10) if patient_portrait else ''}
专家组诊断报告：
{all_reports_text}

请按照系统提示词中的要求，生成结构化的综合诊断报告。
"""

    # 5. 调用 LLM 生成汇总报告
    print("    正在调用 LLM 生成综合诊断报告...")

    try:
        llm = create_llm_from_config(settings.summary_agent)
        messages = [HumanMessage(content=user_prompt)]
        response = llm.invoke(messages)

        final_report = response.content

        print(f"    综合报告生成成功（长度: {len(final_report)} 字符）")
        print("=" * 60 + "\n")

        # 返回两个信息：
        # 1. messages - 添加 AIMessage 到对话历史
        # 2. final_report - 最终报告内容
        return {
            "messages": [AIMessage(content=final_report)],
            "final_report": final_report
        }

    except Exception as e:
        print(f"    错误：汇总报告生成失败 - {str(e)}")
        print("=" * 60 + "\n")

        # 返回降级方案：直接拼接专家报告
        fallback_report = f"""# 综合诊断报告（降级模式）

注意：由于系统错误，以下为各专家组报告的直接整合，未经 AI 汇总处理。

{all_reports_text}

---
错误信息：{str(e)}
"""
        return {
            "messages": [AIMessage(content=fallback_report)],
            "final_report": fallback_report
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
法布雷病（Fabry Disease）- 高度怀疑

## 主要依据
1. 四肢阵发性疼痛（典型 Fabry 危象）
2. 少汗症（自主神经受累）
3. 皮肤血管角质瘤（特征性表现）
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
        "expert_pool": {},
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
