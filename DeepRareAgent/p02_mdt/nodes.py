#---------------------------------------该脚本用于实现MDT Group-----------------------------------
# 1 开启深度诊断后需要将诊断数据转化成将患者信息转化为多专家组并行状态。
# 2 多专家并行处理节点的创建
# 


import asyncio
from typing import Any, Dict, List, Optional, Callable
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage,ToolMessage
from DeepRareAgent.schema import MDTGraphState, ExpertGroupState, SharedBlackboard
from DeepRareAgent.config import settings
from DeepRareAgent.tools.patientinfo import patient_info_to_text
from langchain_core.runnables import RunnableConfig


# ----------------------------------------------------------------------------
# 1. 初始化节点 (Triage Node)
# ----------------------------------------------------------------------------
async def triage_to_mdt_node(state: Dict[str, Any],config: RunnableConfig) -> MDTGraphState:
    """
    分诊节点：将患者信息转化为多专家并行状态。
    """
    # print("config",config.get("metadata", {}).get("langgraph_node"))
    print("\n>>> [MDT Triage] 初始化专家会诊桌...")
    # 格式化患者画像
    patient_report = patient_info_to_text.invoke({"state": state})
    # 获取预诊断阶段的对话总结
    dialogue_summary = state.get("summary_with_dialogue", "")
    
    # 日志：显示接收到的对话总结
    if dialogue_summary:
        print(f"[INFO] 接收到对话总结（{len(dialogue_summary)} 字符）:")
        print("-" * 80)
        print(dialogue_summary[:200] + "..." if len(dialogue_summary) > 200 else dialogue_summary)
        print("-" * 80)
    else:
        print("[WARNING] 未接收到对话总结 (summary_with_dialogue 为空)")
    
    # 构造专家组初始消息（包含患者病例 + 对话总结）
    if dialogue_summary:
        initial_message = f"研究和讨论的患者病例信息如下:\n\n{patient_report}\n\n---\n\n**预诊问诊对话总结：**\n{dialogue_summary}"
    else:
        initial_message = f"研究和讨论的患者病例信息如下:\n\n{patient_report}"
    # 初始化专家池
    group_configs = settings.multi_expert_diagnosis_agent.to_dict()
    expert_pool = {}
    for group_id in group_configs.keys():
        expert_pool[group_id] = {
            "group_id": group_id,
            "messages": [AIMessage(content=initial_message)],
            "report": "等待诊断启动...",
            "evidences": [],
            "is_satisfied": False,
            "reinvestigate_reason": None,
            "has_error": False
        }

    # 从配置文件读取 max_rounds
    max_rounds = getattr(settings.mdt_config, 'max_rounds', 3) if hasattr(settings, 'mdt_config') else 3

    return {
        "messages": [AIMessage(content=initial_message),
                     AIMessage(content=f"[LAB] 正在初始化多专家会诊系统，已分配 {len(expert_pool)} 个专家组...")],
        "patient_info": state.get("patient_info", {}),  # 传递患者信息
        "summary_with_dialogue": dialogue_summary,  # 保留对话摘要，供后续节点使用
        "patient_portrait": patient_report,
        "expert_pool": expert_pool,
        "blackboard": {
            "published_reports": {},
            "conflicts": [],
            "common_understandings": []
        },
        "round_count": 1,
        "max_rounds": max_rounds,  # 使用配置文件中的值
        "consensus_reached": False
    }


# ----------------------------------------------------------------------------
# 2. 路由判断节点 (Routing Node)
# ----------------------------------------------------------------------------
def routing_decision_node(state: MDTGraphState, config: RunnableConfig) -> MDTGraphState:
    """
    路由决策节点：判断是否达成共识或超出最大轮数。

    该节点不做任何状态修改，仅用于后续条件边读取状态进行路由判断。
    也可以在这里添加一些日志或统计信息。
    """
    round_count = state.get("round_count", 0)
    max_rounds = state.get("max_rounds", 3)
    consensus_reached = state.get("consensus_reached", False)

    print("\n" + "=" * 60)
    print(">>> [MDT 路由判断]")
    print("=" * 60)
    print(f"  当前轮数: {round_count}/{max_rounds}")
    print(f"  共识状态: {'已达成' if consensus_reached else '未达成'}")

    # 统计专家满意度
    expert_pool = state.get("expert_pool", {})
    satisfied_count = sum(
        1 for expert in expert_pool.values()
        if expert.get("is_satisfied", False) and not expert.get("has_error", False)
    )
    total_count = sum(
        1 for expert in expert_pool.values()
        if not expert.get("has_error", False)
    )
    print(f"  专家满意度: {satisfied_count}/{total_count}")

    if consensus_reached:
        print("  决策: 达成共识，准备结束")
    elif round_count >= max_rounds:
        print("  决策: 达到最大轮数，准备结束")
    else:
        print(f"  决策: 继续第 {round_count + 1} 轮诊断")
    print("=" * 60 + "\n")

    # 不修改状态，直接返回空字典
    return {}


# ----------------------------------------------------------------------------
# 3. 扇出节点 (Fan-out Node) - 重新分发到各专家
# ----------------------------------------------------------------------------
def fan_out_node(state: MDTGraphState, config: RunnableConfig) -> MDTGraphState:
    """
    扇出节点：从路由决策后重新分发到各个专家节点。

    该节点作为一个逻辑上的"重新开始诊断"的标记点，
    添加消息提示用户开始新一轮诊断。
    """
    round_count = state.get("round_count", 0)

    print("\n" + "=" * 60)
    print(f">>> [MDT 扇出] 开始第 {round_count} 轮专家诊断...")
    print("=" * 60 + "\n")

    # 添加新轮次开始的消息提示
    return {
        "messages": [AIMessage(content=f"🔄 开始第 {round_count} 轮专家诊断，重新审视患者信息...")]
    }


# ----------------------------------------------------------------------------
# 4. 条件边路由函数 (用于 add_conditional_edges)
# ----------------------------------------------------------------------------
def should_continue_or_end(state: MDTGraphState) -> str:
    """
    条件边路由函数：基于状态判断下一步走向。

    Returns:
        "end": 结束流程
        "continue": 继续诊断（回到扇出节点）
    """
    consensus_reached = state.get("consensus_reached", False)
    round_count = state.get("round_count", 0)
    max_rounds = state.get("max_rounds", 3)

    if consensus_reached:
        return "end"
    if round_count >= max_rounds:
        return "end"
    return "continue"







    







