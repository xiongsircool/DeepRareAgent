import asyncio
import os
import json5
from typing import Any, Dict, List, Optional, Callable
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from DeepRareAgent.schema import MDTGraphState, ExpertGroupState, SharedBlackboard
from DeepRareAgent.config import settings
from DeepRareAgent.tools.patientinfo import patient_info_to_text
from langchain_core.runnables import RunnableConfig
from DeepRareAgent.utils.model_factory import create_llm_from_config
from DeepRareAgent.utils.json_utils import parse_json_from_markdown

def build_reviewer_messages(state: MDTGraphState):
    """
    1 基于export_pool 更新MDTGraphState 黑板, 如果report存在且不存在has_error: True且黑板中存在一份报告则不需要重制黑板中报告，否则不变

    2 构建后续reviewer时候的messages.
    """
    # 1. 基于export_pool 更新黑板
    export_pool = state.get("expert_pool", {})
    blackboard = state.get("blackboard", {})
    
    # 初始化 published_reports
    if "published_reports" not in blackboard:
        blackboard["published_reports"] = {}

    for group_id, expert in export_pool.items():
        if expert.get("has_error", False) or expert.get("is_satisfied", False):
            continue
        # Update blackboard if report not present or changed (though logic here updates if NOT present)
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

        # reviewer_prompt 1,表示你和你的组已经完成了诊断 2,设置格式化输出要求输出 reinvestigate_reason，is_satisfied 两个字段

        # Load reviewer prompt from file
        prompt_path = getattr(settings.mdt_config, "reviewer_prompt_path", None)
        
        if not prompt_path:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Updated filename
            prompt_path = os.path.join(current_dir, "..", "prompts", "02deepagent_reviewer_prompt.txt")

        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                reviewer_prompt_template = f.read()
            reviewer_prompt = reviewer_prompt_template.replace("{round_count}", str(state.get("round_count", 1)))
        except Exception as e:
            print(f"Warning: Could not load reviewer prompt from {prompt_path}: {e}")
            reviewer_prompt = f"""这是第{state.get("round_count", 1)}轮的专家审核，请你基于其他专家的报告，进行大胆自信的评估。
            最后的输出格式为json:
            {{
                "reinvestigate_reason": "",
                "is_satisfied": True
            }}
            """

        patient_report = state.get("patient_portrait", "")
        # 在1的位置插入患者病例信息
        # Check if we haven't already inserted it (simple check to avoid dupes if node re-runs oddly, though standard langgraph flow is fine)
        # For simplicity, assuming messages are fresh or we append. But here we insert at 1.
        # Be careful not to mutate global state objects repeatedly if they persist inappropriately, but here we modify the dict which is passed by ref.
        # Ideally we should clone messages, but for 'need_update_expert' which is used for the *next* step, modifying it is the intention.
        
        # 插入患者信息
        need_update_expert[group_id]["messages"].insert(1, HumanMessage(content=f"诊断的信息如下:\n\n{patient_report}"))
        
        # 追加审核指令
        need_update_expert[group_id]["messages"].append(HumanMessage(content=f"你已经完成了审核，现在给你提供其他专家的报告，一共有{len(other_reports)}份报告，分别如下:\n\n{other_reports}"))
        need_update_expert[group_id]["messages"].append(HumanMessage(content=reviewer_prompt))

    return state, need_update_expert    


async def process_single_expert_review(group_id: str, expert: ExpertGroupState):
    """
    Async helper to process a single expert's review.
    """
    try:
        # 1. 构架model
        group_id_model_config = getattr(settings.multi_expert_diagnosis_agent, group_id)
        group_id_main_model_config = group_id_model_config.main_agent
        model = create_llm_from_config(group_id_main_model_config)
        
        # Bind output format if supported, but our parsing utility handles loose JSON too.
        # Most providers support json_object, but some might not. Keep it for safety if config allows.
        # model = model.bind(response_format={"type": "json_object"}) 

        # 2. 请求model (Async)
        response = await model.ainvoke(expert["messages"])
        
        # 3. 解析结果
        result = parse_json_from_markdown(response.content)
        
        return group_id, result, response
        
    except Exception as e:
        print(f"[ERROR] Agent {group_id} review failed: {e}")
        # Return a fallback failure result so we don't crash the whole graph
        return group_id, {"is_satisfied": False, "reinvestigate_reason": f"System Error during review: {str(e)}", "has_error": True}, None


async def expert_reviewer_node(state: MDTGraphState, config: RunnableConfig) -> MDTGraphState:
    """
    专家与专家之间讨论的节点(把各个专家的诊断结果更新到黑板，然后分别进行自己报告是否存在与对方冲突，存在冲突情况下是否需要重新进行诊断。)
    
    Optimized: 使用 asyncio.gather 并行处理所有专家的审核。
    """

    # 1. 基于export_pool 更新黑板并构建消息
    state, need_update_expert = build_reviewer_messages(state)
    
    state["blackboard"]["conflicts"] = {} # 重置冲突

    # 2. 并行执行审核
    tasks = []
    for group_id, expert in need_update_expert.items():
        tasks.append(process_single_expert_review(group_id, expert))
    
    if not tasks:
        print("[Review] No experts need review (all satisfied or errored).")
    else:
        results = await asyncio.gather(*tasks)
        
        # 3. 处理结果
        for group_id, result, response in results:
            # Handle potential hard failure in helper
            if result.get("has_error"):
                print(f"[WARN] {group_id} review process returned error.")
                # Can choose to mark expert as errored or just continue
                state["expert_pool"][group_id]["has_error"] = True
                continue

            is_satisfied = result.get("is_satisfied", False)
            reinvestigate_reason = result.get("reinvestigate_reason", "")

            state["expert_pool"][group_id]["is_satisfied"] = is_satisfied
            state["expert_pool"][group_id]["reinvestigate_reason"] = reinvestigate_reason

            # 输出专家审阅结果（方便调试和解读）
            print(f"\n{'=' * 60}")
            print(f">>> [专家审阅] {group_id}")
            print(f"{'=' * 60}")
            print(f"  满意度: {'[PASS] 满意' if is_satisfied else '[FAIL] 不满意'}")
            if reinvestigate_reason:
                print(f"  复查原因: {reinvestigate_reason}")
            print(f"{'=' * 60}\n")

            # 添加模型的审阅回复到messages
            if response:
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

    # 4. 整合结果后更新MDTGraphState中round_count、consensus_reached
    state["round_count"] += 1
    
    # 检查是否所有专家都满意（排除有错误的专家）
    # Note: need to re-check the full expert pool state
    active_experts = [e for e in state["expert_pool"].values() if not e.get("has_error", False)]
    
    if not active_experts:
        # If all experts errored out, maybe end?
        all_satisfied = True 
        print("[WARN] All experts have errors. Forcing end of loop.")
    else:
        all_satisfied = all(expert.get("is_satisfied", False) for expert in active_experts)
        
    state["consensus_reached"] = all_satisfied

    # 添加进度消息到主图
    satisfied_count = sum(1 for e in active_experts if e.get("is_satisfied", False))
    total_count = len(active_experts)

    progress_msg = f"[PASS] 第 {state['round_count'] - 1} 轮专家互审完成 (满意度: {satisfied_count}/{total_count})"
    if all_satisfied:
        progress_msg += " - 已达成共识！"
    elif state["round_count"] > state.get("max_rounds", 3):
        progress_msg += " - 已达最大轮数"

    state["messages"] = [AIMessage(content=progress_msg)]

    return state
