# ----------------------------------------------------------------------------
# 1. 初始化 LangGraph
# ----------------------------------------------------------------------------
from langgraph.graph import StateGraph, START, END
from DeepRareAgent.schema import MDTGraphState
from DeepRareAgent.p02_mdt.nodes import (
    triage_to_mdt_node,
    routing_decision_node,
    fan_out_node,
    should_continue_or_end
)
from DeepRareAgent.p02_mdt.export_reviewer_node import expert_reviewer_node
from DeepRareAgent.config import settings
from DeepRareAgent.p02_mdt.builddeepexportnode import create_deep_export_node

def create_mdt_graph():
    """创建多专家会诊图"""

    graph = StateGraph(MDTGraphState)

    # 1. 添加初始化节点
    graph.add_node("triage_to_mdt_node", triage_to_mdt_node)

    # 2. 添加各个专家诊断节点
    expert_nodes = []
    group_configs = settings.multi_expert_diagnosis_agent.to_dict()
    for group_id in group_configs.keys():
        # 注意：节点名直接使用 group_id (如 "group_1")，因为：
        # 1. builddeepexportnode 中通过 config.metadata.langgraph_node 获取 group_id
        # 2. export_reviewer_node 中通过 group_id 获取配置
        expert_config = getattr(settings.multi_expert_diagnosis_agent, group_id)
        graph.add_node(group_id, create_deep_export_node(expert_config))
        expert_nodes.append(group_id)

    # 3. 添加专家互审节点
    graph.add_node("expert_review", expert_reviewer_node)

    # 4. 添加路由判断节点
    graph.add_node("routing_decision", routing_decision_node)

    # 5. 添加扇出节点（重新分发到各专家）
    graph.add_node("fan_out", fan_out_node)

    # 6. 连接边
    # START → triage_to_mdt_node
    graph.add_edge(START, "triage_to_mdt_node")

    # triage_to_mdt_node → 各专家节点（并行）
    for node in expert_nodes:
        graph.add_edge("triage_to_mdt_node", node)

    # 各专家节点 → expert_review
    for node in expert_nodes:
        graph.add_edge(node, "expert_review")

    # expert_review → routing_decision
    graph.add_edge("expert_review", "routing_decision")

    # routing_decision → 条件边（决定是结束还是继续）
    graph.add_conditional_edges(
        "routing_decision",
        should_continue_or_end,  # 路由函数
        {
            "end": END,
            "continue": "fan_out"  # 继续 → 扇出节点
        }
    )

    # fan_out → 各专家节点（并行，开始新一轮）
    for node in expert_nodes:
        graph.add_edge("fan_out", node)

    return graph.compile(name="MDTGraph")









if __name__ == "__main__":
    import asyncio
    import pprint

    mdt_graph = create_mdt_graph()
    init_state = {
        "patient_info": {
            "base_info": {"name": "张三", "age": 30, "gender": "男", "occupation": "程序员"},
            "symptoms": [
                {"id": "S1", "name": "头痛", "description": "剧烈胀痛，伴随恶心"},
                {"id": "S2", "name": "发热", "value": "38.5℃"}
            ],
            "vitals": [
                {"id": "V1", "type": "体温", "value": "38.5"},
                {"id": "V2", "type": "血压", "value": "120/80"}
            ],
            "exams": [],
            "medications": [],
            "family_history": [],
            "others": []
        },
        "summary_with_dialogue": ""
    }

    # 使用 ainvoke 异步运行
    result = asyncio.run(mdt_graph.ainvoke(init_state))
    pprint.pprint(result)
