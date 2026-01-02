import asyncio
from typing import Any, Dict, List, Optional, Callable
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from DeepRareAgent.schema import MDTGraphState, ExpertGroupState, SharedBlackboard
from DeepRareAgent.config import settings
from DeepRareAgent.tools.patientinfo import patient_info_to_text
from langchain_core.runnables import RunnableConfig
from DeepRareAgent.utils.model_factory import create_llm_from_config
import json5



def build_reviwer_messages(state: MDTGraphState):
    """
    1 基于export_pool 更新MDTGraphState 黑板, 如果report存在且不存在has_error: True且黑板中存在一份报告则不需要重制黑板中报告，否则不变

    2 构建后续reviwer时候的messgaes.

    """
    # 1. 基于export_pool 更新黑板
    export_pool = state.get("expert_pool", {})
    blackboard = state.get("blackboard", {})
    for group_id, expert in export_pool.items():
        if expert.get("has_error", False) or expert.get("is_satisfied", False):
            continue
        if group_id not in blackboard["published_reports"]:
            blackboard["published_reports"][group_id] = expert["report"]
    state["blackboard"] = blackboard

    # export_pool中messages 进行改造注入,自己以外的专家的report注入到自己messages中
    need_update_expert = {}
    for group_id, expert in export_pool.items():
        if expert.get("has_error", False) or expert.get("is_satisfied", False):
            continue
        need_update_expert[group_id] = expert
        other_reports = ""
        for other_group_id, other_expert in export_pool.items():
            if other_group_id != group_id:
                other_reports += f"==========={other_group_id}================\n {other_expert['report']}\n"

        # reviwer_prompt 1,表示你和你的组已经完成了诊断 2,设置格式化输出要求输出 reinvestigate_reason，is_satisfied 两个字段
        reviwer_prompt = f"""这是第{state.get("round_count", 1)}轮的专家审核，请你基于其他专家的报告，进行大胆自信的平谷,假如你觉得你的结果和团队在患者诊断报告上没有什么大的修改或者疑惑的地方。请直接返回你的最终诊断报告。
        最后的输出格式为json:
        {{
            "reinvestigate_reason": "", # 如果不满意，是因为发现了什么新疑点或被其他组修正了认知。
            "is_satisfied": True # 如果满意，表示认为结论已闭环
        }}
        """

        patient_report = state.get("patient_portrait", "")
        # 在1的位置插入患者病例信息
        need_update_expert[group_id]["messages"].insert(1,HumanMessage(content=f"诊断的信息如下:\n\n{patient_report}"))
        need_update_expert[group_id]["messages"].append(HumanMessage(content=f"你已经完成了审核，现在给你提供其他专家的报告，一共有{len(other_reports)}份报告，分别如下:\n\n{other_reports}"))
        need_update_expert[group_id]["messages"].append(HumanMessage(content=reviwer_prompt))

    return state,need_update_expert    


# --------------------------------------------------------------------------------------------------------------
# 2 . 创建专家与专家之间讨论的节点(把各个专家的诊断结果更新到黑板，然后分别进行自己报告是否存在与对方冲突，存在冲突情况下是否需要重新进行诊断。)
#----------------------------------------------------------------------------------------------------------------
def expert_reviwer_node(state: MDTGraphState,config: RunnableConfig) -> MDTGraphState:
    """
    专家与专家之间讨论的节点(把各个专家的诊断结果更新到黑板，然后分别进行自己报告是否存在与对方冲突，存在冲突情况下是否需要重新进行诊断。)
    已经实现 1基于export_pool 更新黑板、2构建后续reviwer时候的messgaes.2、开始reviwer和结果处理 3、加入只有一个Group运行优化也就是一开始就不用reviwer等操作。
    TODO: 1. 改用异步来实现审查节点的速度提速优化速度。
    """

    # 1. 基于export_pool 更新黑板
    state,need_update_expert = build_reviwer_messages(state)
    # 2. 对于需要review的专家，开始review。1构架model,2开始review,3结果处理更新need_update_expert中信息。
    state["blackboard"]["conflicts"] = {} # 重置冲突
    for group_id, expert in need_update_expert.items():
        # 1. 构架model
        group_id_model_config = getattr(settings.multi_expert_diagnosis_agent, group_id)
        group_id_main_model_config = group_id_model_config.main_agent
        model = create_llm_from_config(group_id_main_model_config)
        model = model.bind(response_format={"type": "json_object"})

        # 2.请求model
        response = model.invoke(expert["messages"])
        try:
            result = json5.loads(response.content)
        except Exception as e:
            # 解析出json数据位置再解析
            result = json5.loads(response.content[response.content.find("{"): response.content.rfind("}") + 1])
        
        # 解析后处理结构更新state中expert_pool.
        is_satisfied = result.get("is_satisfied", False)
        reinvestigate_reason = result.get("reinvestigate_reason", "")

        state["expert_pool"][group_id]["is_satisfied"] = is_satisfied
        state["expert_pool"][group_id]["reinvestigate_reason"] = reinvestigate_reason

        # 添加模型的审阅回复到messages
        state["expert_pool"][group_id]["messages"].append(response)

        # 如果不满意，添加复查指令消息
        if not is_satisfied:
            state["blackboard"]["conflicts"][group_id] = reinvestigate_reason
            # 添加复查指令
            reinvestigate_message = HumanMessage(content=f"""你已经查看了其他专家的报告，并基于以下原因提出了疑问：

{reinvestigate_reason}

现在请你和你的组内成员再进行一次深入复查，重新审视患者的症状、体征和检查结果，更新你的诊断报告内容。

**重要提醒**：最后仍需按照原有格式输出完整的诊断报告。""")
            state["expert_pool"][group_id]["messages"].append(reinvestigate_message)

    # 3. 整合结果后更新MDTGraphState中round_count、consensus_reached
    state["round_count"] += 1
    # 检查是否所有专家都满意（排除有错误的专家）
    all_satisfied = all(
        expert.get("is_satisfied", False)
        for expert in state["expert_pool"].values()
        if not expert.get("has_error", False)
    )
    state["consensus_reached"] = all_satisfied

    # 添加进度消息到主图
    satisfied_count = sum(
        1 for expert in state["expert_pool"].values()
        if expert.get("is_satisfied", False) and not expert.get("has_error", False)
    )
    total_count = sum(
        1 for expert in state["expert_pool"].values()
        if not expert.get("has_error", False)
    )

    progress_msg = f"✅ 第 {state['round_count'] - 1} 轮专家互审完成 (满意度: {satisfied_count}/{total_count})"
    if all_satisfied:
        progress_msg += " - 已达成共识！"
    elif state["round_count"] > state.get("max_rounds", 3):
        progress_msg += " - 已达最大轮数"

    state["messages"] = [AIMessage(content=progress_msg)]

    return state
