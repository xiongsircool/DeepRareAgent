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
        "past_medical_history": [],
        "others": []
    }


# --- 4. 准备MDT的中间节点 ---
async def prepare_for_mdt_node(state: MainGraphState):
    """
    在进入MDT之前的准备节点：生成对话总结
    
    这个节点解决了一个关键问题：
    trigger_deep_diagnosis 工具通过 Command.PARENT 直接更新主图状态，
    导致预诊断节点的 result 中无法捕获 start_diagnosis 的变化。
    因此我们在主图的路由阶段生成对话总结。
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    
    # 检查是否已有对话总结
    existing_summary = state.get('summary_with_dialogue', '')
    if existing_summary:
        print(f"\n[LIST] 已存在对话总结，无需重新生成（{len(existing_summary)} 字符）")
        return {}
    
    # 提取对话历史
    messages = state.get('messages', [])
    if not messages:
        print("\n[WARN] 没有对话历史，跳过总结生成")
        return {}
    
    print("\n[NOTE] [Prepare MDT] 正在生成对话总结...")
    
    # 使用配置中的模型生成总结
    # 注意：使用 pre_diagnosis_agent 的配置，因为这是对预诊断对话的总结
    # 可以考虑未来添加专门的配置项，如 summary_agent 或 prepare_mdt_agent
    try:
        from DeepRareAgent.utils.model_factory import create_llm_from_config
        
        # 使用预诊断配置创建模型（轻量级任务，使用相同配置合理）
        model = create_llm_from_config(settings.pre_diagnosis_agent)
        
        print(f"  - 使用模型: {settings.pre_diagnosis_agent.model_name}")
        print(f"  - Provider: {getattr(settings.pre_diagnosis_agent, 'provider', 'openai')}")
        
        # 修改为“上述”对话，因为我们将把提示词append到对话列表最后
        summary_prompt = """请将上述医患对话总结为简洁的患者病情摘要，包括主诉、症状、病史等关键信息，供后续深度诊断参考。

请用结构化的形式输出摘要（不超过500字）："""
        
        # 这里的修改：不再手动拼接字符串，而是直接使用 messages 列表
        # 这样可以保留多模态信息（如图片），避免 str(content) 造成的格式错误
        input_messages = messages + [SystemMessage(content=summary_prompt)]
        
        summary_response = await model.ainvoke(input_messages)
        summary_with_dialogue = summary_response.content
        
        print(f"\n[PASS] 对话摘要生成完成（{len(summary_with_dialogue)} 字符）:")
        print("-" * 80)
        print(summary_with_dialogue[:300] + "..." if len(summary_with_dialogue) > 300 else summary_with_dialogue)
        print("-" * 80)
        
        return {
            'summary_with_dialogue': summary_with_dialogue,
            'messages': [AIMessage(content="正在生成对话总结并准备专家会诊...")]
        }
        
    except Exception as e:
        print(f"\n[WARN] 生成对话摘要失败: {e}")
        print("  - 使用降级方案：尝试提取文本内容作为摘要")
        
        try:
             # 简单的文本回退逻辑
             fallback_text = "\n".join([
                f"{'患者' if isinstance(m, HumanMessage) else '医生'}: {m.content if isinstance(m.content, str) else '[Multimodal Content]'}" 
                for m in messages
                if isinstance(m, (HumanMessage, AIMessage))
            ])
        except:
            fallback_text = "无法提取对话历史"

        return {
            'summary_with_dialogue': fallback_text,
            'messages': [AIMessage(content="[WARN] 对话总结生成失败，使用原始对话记录")]
        }


# --- 5. 路由逻辑 ---
def route_after_prediagnosis(state: MainGraphState) -> str:
    """
    预诊断后的路由判断：
    - 如果 start_diagnosis=True，进入准备MDT节点
    - 否则结束对话，等待用户下次输入
    """
    if state.get("start_diagnosis", False):
        return "prepare_mdt"
    return "__end__"



# --- 6. 构建主图 ---
def create_main_graph():
    """
    创建罕见病诊断系统主图

    流程：
    START → 预诊断 → (判断) → 准备MDT → MDT 会诊 → 汇总报告 → END
                       ↓
                      END (未开始诊断时结束，等待用户继续输入)
    """
    workflow = StateGraph(MainGraphState)

    # 1. 添加预诊断节点
    prediagnosis_node = create_pre_diagnosis_node(settings=settings)
    workflow.add_node("prediagnosis", prediagnosis_node)

    # 2. 添加准备MDT节点（生成对话总结）
    workflow.add_node("prepare_mdt", prepare_for_mdt_node)

    # 3. 添加 MDT 多专家会诊子图（作为一个节点）
    mdt_graph = create_mdt_graph()
    workflow.add_node("mdt_diagnosis", mdt_graph)

    # 4. 添加汇总节点
    workflow.add_node("summary", summary_node)

    # 5. 连接边
    # START → 预诊断
    workflow.add_edge(START, "prediagnosis")

    # 预诊断 → 条件判断（开始诊断 or 结束等待用户）
    workflow.add_conditional_edges(
        "prediagnosis",
        route_after_prediagnosis,
        {
            "prepare_mdt": "prepare_mdt",  # 先准备MDT（生成总结）
            "__end__": END  # 结束对话，等待用户下次输入
        }
    )

    # 准备MDT → MDT 会诊
    workflow.add_edge("prepare_mdt", "mdt_diagnosis")

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
        result = await graph.ainvoke(initial_state)

    asyncio.run(run_test())
