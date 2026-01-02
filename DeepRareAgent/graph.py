"""
罕见病诊断系统 - 主图
整合预诊断 → MDT 多专家会诊 → 汇总报告的完整流程
"""

# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

# 1. 导入配置
from DeepRareAgent.config import settings

# 2. 导入各阶段节点
from DeepRareAgent.p01pre_diagnosis_agent import create_pre_diagnosis_node
from DeepRareAgent.p02_mdt.graph import create_mdt_graph
from DeepRareAgent.p03summary_agent import summary_node
from DeepRareAgent.schema import MainGraphState

# --- 3. 状态初始化辅助函数 ---
def init_patient_info() -> Dict[str, Any]:
    """
    初始化患者信息结构，确保所有必需字段都存在。
    """
    return {
        "base_info": {},
        "symptoms": [],
        "vitals": [],
        "exams": [],
        "medications": [],
        "family_history": [],
        "others": []
    }


# --- 4. 路由逻辑 ---
def route_after_prediagnosis(state: MainGraphState) -> str:
    """
    预诊断后的路由判断：
    - 如果 start_diagnosis=True，进入 MDT 会诊
    - 否则结束对话，等待用户下次输入
    """
    if state.get("start_diagnosis", False):
        return "mdt_diagnosis"
    return "__end__"


# --- 5. 构建主图 ---
def create_main_graph():
    """
    创建罕见病诊断系统主图

    流程：
    START → 预诊断 → (判断) → MDT 会诊 → 汇总报告 → END
                       ↓
                      END (未开始诊断时结束，等待用户继续输入)
    """
    workflow = StateGraph(MainGraphState)

    # 1. 添加预诊断节点
    prediagnosis_node = create_pre_diagnosis_node(settings=settings)
    workflow.add_node("prediagnosis", prediagnosis_node)

    # 2. 添加 MDT 多专家会诊子图（作为一个节点）
    mdt_graph = create_mdt_graph()
    workflow.add_node("mdt_diagnosis", mdt_graph)

    # 3. 添加汇总节点
    workflow.add_node("summary", summary_node)

    # 4. 连接边
    # START → 预诊断
    workflow.add_edge(START, "prediagnosis")

    # 预诊断 → 条件判断（开始诊断 or 结束等待用户）
    workflow.add_conditional_edges(
        "prediagnosis",
        route_after_prediagnosis,
        {
            "mdt_diagnosis": "mdt_diagnosis",
            "__end__": END  # 结束对话，等待用户下次输入
        }
    )

    # MDT 会诊 → 汇总报告
    workflow.add_edge("mdt_diagnosis", "summary")

    # 汇总报告 → END
    workflow.add_edge("summary", END)

    return workflow.compile(name="RareDiagnosisSystem")


# 编译主图
graph = create_main_graph()

__all__ = ["graph", "init_patient_info", "MainGraphState", "create_main_graph"]


# --- 6. 测试入口 ---
if __name__ == "__main__":
    import asyncio
    from langchain_core.messages import HumanMessage

    async def run_test():
        print("=" * 80)
        print("罕见病诊断系统 - 主图测试")
        print("=" * 80)

        # 初始化状态
        initial_state = {
            # 主图专有字段
            "messages": [HumanMessage(content="你好，我想咨询一下我的病情")],
            "start_diagnosis": False,
            "final_report": "",

            # 患者信息字段
            "patient_info": init_patient_info(),
            "summary_with_dialogue": "",
            "patient_portrait": "",

            # MDT 输出字段（初始为空）
            "expert_pool": {},
            "blackboard": {
                "published_reports": {},
                "conflicts": {},
                "common_understandings": {}
            },
            "consensus_reached": False
        }

        print("\n[1] 初始状态准备完成")
        print(f"    - 预诊断状态: {'未开始' if not initial_state['start_diagnosis'] else '已开始'}")

        print("\n[2] 主图编译成功")
        print("    流程: 预诊断 → MDT 会诊 → 汇总报告")

        print("\n[3] 提示：")
        print("    - 要运行完整测试，请设置 start_diagnosis=True")
        print("    - 或使用交互式预诊断收集患者信息")

        # 你可以在这里运行 graph.ainvoke(initial_state)
        # result = await graph.ainvoke(initial_state)

    asyncio.run(run_test())
