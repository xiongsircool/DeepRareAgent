"""
测试：验证子图是否可以向主图返回 messages，即使子图 Schema 中没有定义 messages 字段
"""
from typing import Annotated, List, Dict, Any
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages


# 1. 定义主图状态（有 messages 字段）
class MainState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    patient_info: Dict[str, Any]
    diagnosis_complete: bool


# 2. 定义子图状态（没有 messages 字段）
class SubGraphState(TypedDict):
    patient_info: Dict[str, Any]
    diagnosis_complete: bool
    # 注意：这里故意不定义 messages


# 3. 子图节点 - 测试返回 messages
def subgraph_node_with_messages(state: SubGraphState) -> Dict[str, Any]:
    """子图节点：尝试返回 messages，即使 SubGraphState 没有定义"""
    print("\n[SubGraph Node] 执行中...")
    print(f"[SubGraph Node] 输入状态: {state}")

    # 尝试返回 messages
    result = {
        "patient_info": state.get("patient_info", {}),
        "diagnosis_complete": True,
        "messages": [AIMessage(content="这是子图节点添加的消息")]
    }

    print(f"[SubGraph Node] 返回值: {result}")
    return result


# 4. 创建子图
def create_subgraph():
    workflow = StateGraph(SubGraphState)
    workflow.add_node("process", subgraph_node_with_messages)
    workflow.add_edge(START, "process")
    workflow.add_edge("process", END)
    return workflow.compile(name="SubGraph")


# 5. 主图节点
def main_node(state: MainState) -> Dict[str, Any]:
    """主图的普通节点"""
    return {
        "messages": [AIMessage(content="这是主图节点添加的消息")]
    }


# 6. 创建主图
def create_main_graph():
    workflow = StateGraph(MainState)

    # 添加主图节点
    workflow.add_node("main_node", main_node)

    # 添加子图作为节点
    subgraph = create_subgraph()
    workflow.add_node("subgraph", subgraph)

    # 连接
    workflow.add_edge(START, "main_node")
    workflow.add_edge("main_node", "subgraph")
    workflow.add_edge("subgraph", END)

    return workflow.compile(name="MainGraph")


# 7. 运行测试
if __name__ == "__main__":
    import asyncio

    async def run_test():
        print("=" * 80)
        print("测试：子图是否可以返回 messages 到主图（即使子图 Schema 未定义）")
        print("=" * 80)

        graph = create_main_graph()

        initial_state = {
            "messages": [HumanMessage(content="用户输入")],
            "patient_info": {"name": "张三"},
            "diagnosis_complete": False
        }

        print("\n[初始状态]")
        print(f"  messages 数量: {len(initial_state['messages'])}")
        for i, msg in enumerate(initial_state['messages']):
            print(f"    {i+1}. {msg.__class__.__name__}: {msg.content}")

        print("\n[开始执行图]")
        result = await graph.ainvoke(initial_state)

        print("\n" + "=" * 80)
        print("[最终状态]")
        print("=" * 80)
        print(f"  messages 数量: {len(result['messages'])}")
        for i, msg in enumerate(result['messages']):
            print(f"    {i+1}. {msg.__class__.__name__}: {msg.content}")
        print(f"  diagnosis_complete: {result['diagnosis_complete']}")

        print("\n" + "=" * 80)
        print("[结论]")
        print("=" * 80)
        if len(result['messages']) == 3:
            print("✅ 成功！子图返回的 messages 被添加到主图")
            print("   说明：即使子图 Schema 没有定义 messages，也可以返回并更新主图")
        elif len(result['messages']) == 2:
            print("❌ 失败！子图返回的 messages 未被添加到主图")
            print("   说明：子图 Schema 必须定义 messages 字段才能返回")
        else:
            print(f"⚠️  意外结果：messages 数量为 {len(result['messages'])}")

    asyncio.run(run_test())