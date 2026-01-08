# -*- coding: utf-8 -*-
import os
import warnings
from pathlib import Path
from typing import List, Optional, Dict, Any, Annotated

from pydantic import BaseModel, Field
from dotenv import load_dotenv

# LangChain and Langgraph 基础组件
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.runtime import Runtime
from langgraph.types import Command
from langgraph.prebuilt import InjectedState

# 框架特有的封装 (根据你的环境导入)
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import AgentMiddleware, hook_config

# 自己构建的包导入
from DeepRareAgent.tools.patientinfo import PatientInfoManger
from DeepRareAgent.states.prediagnosis import PreDiagnosisState
from DeepRareAgent.utils.model_factory import create_llm_from_config

warnings.filterwarnings("ignore", category=UserWarning, module="langchain")


from DeepRareAgent.config import settings as global_settings # 默认全局配置


# ---------------------------------------------------------
# 1. 触发深度诊断的工具函数
# ---------------------------------------------------------
@tool
def trigger_deep_diagnosis(
    state: Annotated[Dict[str, Any], InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    触发深度诊断开关。

    当你认为已经收集到足够的患者信息，满足以下所有条件时调用此工具：
    1. 已收集患者的年龄和性别
    2. 已获得详细的症状描述（包括发作时间、持续时间、严重程度、加重/缓解因素）
    3. 已了解相关的既往史和家族史
    4. 症状复杂或提示罕见病可能，需要深度分析

    或者用户明确要求开始诊断分析时也应调用此工具。

    调用此工具后，系统将自动进入深度诊断模式。
    """
    from langchain_core.messages import ToolMessage
    
    # 更新当前 agent 的 state（不使用 graph=Command.PARENT）
    # 这样 result.get('start_diagnosis') 可以正确获取到 True
    # 然后由节点返回值统一更新到主图
    return Command(
        update={
            "messages": [ToolMessage(content="已触发深度诊断模式", tool_call_id=tool_call_id)],
            "start_diagnosis": True
        }
    )

# ---------------------------------------------------------
# 2. 中间件插件定义
# ---------------------------------------------------------
class PatientContextPlugin(AgentMiddleware):
    """注入患者上下文信息到系统消息"""
    @hook_config()
    def before_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        patient_info = state.get('patient_info', {})
        # print(f"\n>>> [Context] 当前患者信息快照: {patient_info}")
        return {
            "messages": [AIMessage(content=f"目前系统该患者已经记录的患者信息: {patient_info}")],
        }

# ---------------------------------------------------------
# 3. 核心工厂函数：构建预诊断节点
# ---------------------------------------------------------
def create_pre_diagnosis_node(
    model: Optional[ChatOpenAI] = None,
    prompt_path: Optional[str] = None,
    settings: Any = None,
):
    """
    预诊断节点工厂函数（配置驱动版）。
    """
    # 3.1 获取配置快照
    active_settings = settings or global_settings
    cfg = active_settings.pre_diagnosis_agent

    # 3.2 准备模型：优先使用传入的，否则使用 settings 里的配置
    if not model:
        # 使用统一的模型工厂函数创建 LLM 实例
        model = create_llm_from_config(cfg, override_model=None)
        # print(f">>> [PreDiagnosis Agent] 使用模型: {cfg.model_name} (Provider: {getattr(cfg, 'provider', 'openai')})")

    # 3.3 加载 Prompt
    p_path = Path(prompt_path or cfg.system_prompt_path)
    if not p_path.exists():
        raise FileNotFoundError(f"未找到预诊断 Prompt 文件: {p_path}")

    with open(p_path, "r", encoding="utf-8") as f:
        system_prompt_str = f.read()

    # 3.4 准备工具列表
    # 合并患者信息管理工具和深度诊断触发工具
    all_tools = PatientInfoManger + [trigger_deep_diagnosis]

    # 3.5 构建 Agent（不使用 response_format，简化代码）
    internal_agent = create_agent(
        model=model,
        tools=all_tools,
        state_schema=PreDiagnosisState,
        middleware=[PatientContextPlugin()],
        system_prompt=system_prompt_str,
    )

    # 3.6 节点函数 - 简化逻辑
    async def prediagnode(state: PreDiagnosisState, runtime: Runtime | None = None) -> Dict[str, Any]:
        """
        预诊断节点函数

        简化逻辑：
        1. 调用 agent，让它自己决定是否调用 trigger_deep_diagnosis 工具
        2. trigger_deep_diagnosis 工具会通过 Command 自动更新 start_diagnosis
        3. 直接返回 agent 的结果
        """
        # 调用 agent
        state = state.copy()
        result = await internal_agent.ainvoke(state)

        # 提取最后一条 AI 回复消息（过滤掉工具调用等中间消息）
        messages = result.get('messages', [])
        final_ai_message = None

        # 从后往前找最后一条 AIMessage
        for msg in reversed(messages):
            if isinstance(msg, AIMessage):
                final_ai_message = msg
                break

        # 检测是否触发了深度诊断，如果是则添加系统提示
        # 注意：对话总结的生成已移到主图的 prepare_for_mdt_node 中
        # 这里只负责检测触发并添加UI提示
        if result.get('start_diagnosis', False) and not state.get('start_diagnosis', False):
            print("\n🚀 [PreDiag] 检测到深度诊断触发（状态由工具通过Command更新）")
            if final_ai_message:
                content = final_ai_message.content
                final_ai_message = AIMessage(content= (content+'\n\n<span style="color:red">**系统提示：检测到满足深度研究条件，正在为您跳转专家诊断模式...**</span>'))
        
        # 只返回最后一条 AI 消息 + 其他状态更新
        # add_messages 会自动将这条消息追加到主图的 messages 列表
        # 注意：patient_info 已经通过工具的 Command 更新，这里不再重复返回
        return {
            'messages': [final_ai_message] if final_ai_message else [],
            'patient_info': result.get('patient_info', state.get('patient_info', {})),
            # summary_with_dialogue 在主图的 prepare_mdt 节点中生成，这里保持原值
            'summary_with_dialogue': state.get('summary_with_dialogue', ''),
            'start_diagnosis': result.get('start_diagnosis', state.get('start_diagnosis', False))
        }

    return prediagnode


# ---------------------------------------------------------
# 4. 默认导出
# ---------------------------------------------------------
# 直接暴露一个默认节点，方便在 graph.py 中直接导入使用
# 注意：为了避免在导入时就加载模型，这里注释掉默认实例化
# default_pre_diagnosis_node = create_pre_diagnosis_node()

# ========== 测试代码 ==========
if __name__ == "__main__":
    import asyncio
    from langchain_core.messages import HumanMessage, AIMessage

    async def test_p01():
        print(">>> 正在初始化预诊断节点...")
        try:
            # 1. 初始化节点
            prediagnode_node = create_pre_diagnosis_node()
            
            # --- 场景 1: 用户一次性提供完整信息 ---
            print("\n>>> [测试场景] 用户提供完整信息，期待 Agent 请求确认而不是直接触发")
            
            initial_state = {
                "messages": [HumanMessage(content="我今年25岁，男。我头疼了3天了，搏动性疼痛，剧烈程度8/10。没有家族史。请帮我诊断。")],
                "patient_info": {
                    "base_info": {}, "symptoms": [], "vitals": [], "exams": [], "medications": [], "family_history": [], "others": []
                },
                "start_diagnosis": False
            }

            # 运行第一轮
            start_diagnosis_triggered = False
            result1 = None
            try:
                result1 = await prediagnode_node(initial_state)
                # Check normal return
                if result1.get('start_diagnosis'):
                    start_diagnosis_triggered = True
            except Exception as e:
                if "start_diagnosis" in str(e) and "True" in str(e):
                    print(f"[WARN] 捕获到工具调用异常 (符合预期 if 这是在第二轮, 但在第一轮意味着失败): {e}")
                    start_diagnosis_triggered = True
                else:
                    raise e
            
            print("\n" + "-"*30)
            print("【第一轮结果】")
            print(f"是否触发深度诊断: {start_diagnosis_triggered}")
            if result1:
                print(f"回复内容: \n{result1['messages'][0].content}")
            print("-"*30)
            
            if start_diagnosis_triggered:
                print("[FAIL] 失败：在第一轮就触发了深度诊断，未进行确认。")
                return

            print("[PASS] 第一轮未触发，正在模拟确认...")

            # 如果第一轮没有触发（符合预期），我们模拟用户确认
            print("\n>>> [测试场景] 用户回复 '是的，开始深度诊断' ...")
            
            # 构造第二轮状态
            # 简单起见，我们假设 result1 返回了回复。
            msg_history = initial_state["messages"]
            if result1 and result1.get('messages'):
                 msg_history.extend(result1['messages'])
            
            msg_history.append(HumanMessage(content="是的，开始深度诊断"))

            state_round_2 = {
                "messages": msg_history,
                "patient_info": result1.get('patient_info') if result1 else initial_state['patient_info'],
                "start_diagnosis": False
            }
            
            result2 = None
            start_diagnosis_triggered_2 = False
            try:
                result2 = await prediagnode_node(state_round_2)
                if result2.get('start_diagnosis'):
                    start_diagnosis_triggered_2 = True
            except Exception as e:
                # Catch the Command bubble update
                if "start_diagnosis" in str(e):
                     print(f"[PASS] 捕获到工具调用 (符合预期): {e}")
                     start_diagnosis_triggered_2 = True
                else:
                     print(f"[FAIL] 捕获到意外异常: {e}")

            
            print("\n" + "-"*30)
            print("【第二轮结果】")
            print(f"是否触发深度诊断: {start_diagnosis_triggered_2}")
            if result2:
                print(f"回复内容: \n{result2['messages'][0].content}")
            print("-"*30)
            
            if start_diagnosis_triggered_2:
                 print("[PASS] 测试通过：在确认后触发了深度诊断。")
            else:
                 print("[FAIL] 测试失败：确认后仍未触发。")

        except Exception as e:
            print(f"[FAIL] 测试运行时挂了: {e}")
            import traceback
            traceback.print_exc()

    asyncio.run(test_p01())
