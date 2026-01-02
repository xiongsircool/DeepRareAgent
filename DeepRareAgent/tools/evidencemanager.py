"""
Evidence Management Tools for DeepRareAgent

Provides tools for saving and extracting diagnostic evidence chains in the main graph state.
Each piece of evidence is a string that can be used to track diagnostic reasoning and findings.
"""

from typing import Annotated, List, Dict, Any
import operator
from langgraph.prebuilt import InjectedState
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.types import Command

# 1. 保存证据工具
@tool
def save_evidences(
    evidences: Annotated[List[str], "A list of NEW factual, declarative evidence statements to append."],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Record NEW diagnostic evidence into the graph state.
    Guidelines:
    - Factual and verifiable statements only.
    - Avoid speculative language (e.g., 'might', 'suggests').
    - Example: 'Patient has elevated serum creatine kinase (CK) levels.'
    """
    summary = f"Recorded {len(evidences)} item(s)."
    if evidences:
        summary += f" First: {evidences[0][:50]}..."
        
    tool_msg = ToolMessage(content=f"SUCCESS: {summary}", tool_call_id=tool_call_id)
    
    return Command(
        update={
            "evidences": evidences, # 依赖 State 的 operator.add 自动追加
            "messages": [tool_msg]
        }
    )

# 2. 提取证据工具
@tool
def extract_evidences(
    state: Annotated[Dict[str, Any], InjectedState],
    reason: str = "review"
) -> str:
    """
    Retrieve all recorded diagnostic evidence from the current state.
    Returns a formatted string of the entire evidence chain.
    Args:
        reason: Optional reason for extraction (e.g. "final_report").
    """
    ev_list = state.get("evidences", [])
    if not ev_list:
        content = "No diagnostic evidence has been recorded for this patient yet."
    else:
        header = f"--- CURRENT EVIDENCE CHAIN (Reason: {reason}) ---\n"
        body = "\n".join([f"[{i+1}] {ev}" for i, ev in enumerate(ev_list)])
        content = header + body
    
    return content


# 辅助说明：
# - save_evidences: 必须返回 Command，因为它要修改全局的 evidences 列表。
# - extract_evidences: 建议直接返回 str 字符串。因为读取操作不需要修改 State，
#   直接返回字符串会被框架自动包装成 ToolMessage，这种方式对 Agent 来说更稳定。

if __name__ == "__main__":
    from typing_extensions import TypedDict
    import asyncio
    from langchain.agents import create_agent, AgentState
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage
    import operator

    # 1. 定义测试使用的 State
    class TestState(AgentState):
        evidences: Annotated[List[str], operator.add]

    # 2. 初始化模型
    model = ChatAnthropic(
        model="mimo-v2-flash",
        anthropic_api_key="sk-c01l9de7awq589w1b0oxtwo7mzizvi487jvtaio5lbg8sabb",
        base_url="https://api.xiaomimimo.com/anthropic"
    )

    # 3. 创建测试 Agent
    agent = create_agent(
        model=model, 
        tools=[save_evidences, extract_evidences], 
        state_schema=TestState
    )

    async def run_test():
        print("\n=== Testing Evidence Tools ===")
        initial_state = {
            "messages": [HumanMessage(content="帮我记录一条证据：患者基因检测正常。然后利用 extract_evidences 查看所有证据 告诉我目前的全部证据。")],
            "evidences": ["历史存量证据"]
        }
        
        print(f"Initial Evidences: {initial_state['evidences']}")
        
        result = await agent.ainvoke(initial_state)
        for i in result.get("messages", []):
            print(i.content)    
        print("\n=== Final State ===")
        print(f"Evidence Chain Length: {len(result.get('evidences', []))}")
        for i, ev in enumerate(result.get("evidences", []), 1):
            print(f"  {i}. {ev}")

    asyncio.run(run_test())

