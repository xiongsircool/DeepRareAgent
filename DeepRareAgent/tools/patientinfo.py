"""
LangGraph 患者信息工具：CRUD + 文本快照。
适配 InjectedState/Command，保障患者状态安全更新。
"""

from typing import List, Dict, Any
from typing_extensions import Annotated, TypedDict

from langchain_core.messages import BaseMessage, AIMessage, ToolMessage
from langgraph.prebuilt import InjectedState
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.graph.message import add_messages


from uuid import uuid4
from datetime import datetime, timezone
from copy import deepcopy
from langgraph.types import Command
import shortuuid

def generate_short_uuid(existing_ids: set) -> str:
    """
    生成短 UUID，避免与现有 ID 冲突。
    
    使用 4 字符长度（32^4 = 1,048,576 种可能），大幅降低碰撞风险。
    添加最大重试次数保护，防止在极端情况下的无限循环。
    
    Args:
        existing_ids: 已存在的 ID 集合
        
    Returns:
        str: 新生成的唯一 ID
        
    Raises:
        RuntimeError: 如果在最大重试次数内无法生成唯一 ID
    """
    # 初始化一个针对该字母表的生成器（排除易混淆字符 0, 1, I, O）
    run = shortuuid.ShortUUID(alphabet="23456789ABCDEFGHJKLMNPQRSTUVWXYZ")
    max_retries = 1000  # 防止无限循环
    
    for attempt in range(max_retries):
        # 生成 4 位 ID（32^4 = 1,048,576 种可能，碰撞概率极低）
        new_id = run.random(length=4)
        if new_id not in existing_ids:
            return new_id
    
    # 如果达到最大重试次数仍未找到唯一 ID，抛出异常
    raise RuntimeError(
        f"无法在 {max_retries} 次尝试内生成唯一 ID。"
        f"现有 ID 数量: {len(existing_ids)}"
    )
        
        

# class PatientInfo(TypedDict):
#     base_info: Dict[str, Any]
#     symptoms: List[Dict[str, Any]]
#     vitals: List[Dict[str, Any]]
#     exams: List[Dict[str, Any]]
#     medications: List[Dict[str, Any]]
#     family_history: List[Dict[str, Any]]
#     others: List[Dict[str, Any]]

# class AgentState(TypedDict):
#     # 【关键修改】使用 Annotated 和 add_messages
#     messages: Annotated[List[BaseMessage], add_messages] 
#     # patient_info 这里的默认行为是覆盖（Overwrite），
#     # 这通常是合理的，因为我们通常希望保存最新的患者信息快照。
#     patient_info: PatientInfo

# LangGraph `Command`：用于携带对图状态的更新（以及可选的路由/消息等控制信息）。

# ==========================================================================
# 更新患者基础信息的工具
# ==========================================================================
@tool
def set_base_info(
    base_info_patch: Dict[str, Any],
    state: Annotated[Dict[str, Any], InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """更新 patient_info.base_info 并返回 Command"""
    new_state = deepcopy(state)

    # 安全地获取或初始化 patient_info
    if "patient_info" not in new_state:
        new_state["patient_info"] = {
            "base_info": {},
            "symptoms": [],
            "vitals": [],
            "exams": [],
            "medications": [],
            "family_history": [],
            "past_medical_history": [],
            "others": []
        }

    # 【修复】确保 patient_info 内部结构完整
    if not isinstance(new_state["patient_info"], dict):
        new_state["patient_info"] = {}

    if "base_info" not in new_state["patient_info"]:
        new_state["patient_info"]["base_info"] = {}

    # 确保其他字段也存在
    for field in ["symptoms", "vitals", "exams", "medications", "family_history", "past_medical_history", "others"]:
        if field not in new_state["patient_info"]:
            new_state["patient_info"][field] = []

    new_state["patient_info"]["base_info"].update(base_info_patch)
    
    tool_msg = ToolMessage(
        content=f"Base info updated successfully: {base_info_patch}",
        tool_call_id=tool_call_id
    )
    return Command(
        update={
            # 1. 更新数据
            "patient_info": new_state["patient_info"],
            # 2. 【关键】必须把 ToolMessage 加回消息历史
            "messages": [tool_msg] 
        }
    )

# ==========================================================================
# 批量 Upsert 患者事实记录的工具
# ==========================================================================

@tool
def upsert_patient_facts(
    payload: Dict[str, List[Dict[str, Any]]],
    state: Annotated[Dict[str, Any], InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """批量 upsert 患者事实，自动生成短 ID"""
    new_state = deepcopy(state)

    # 安全地获取或初始化 patient_info
    if "patient_info" not in new_state:
        new_state["patient_info"] = {
            "base_info": {},
            "symptoms": [],
            "vitals": [],
            "exams": [],
            "medications": [],
            "family_history": [],
            "past_medical_history": [],
            "others": []
        }

    # 【修复】确保 patient_info 内部结构完整
    if not isinstance(new_state["patient_info"], dict):
        new_state["patient_info"] = {}

    if "base_info" not in new_state["patient_info"]:
        new_state["patient_info"]["base_info"] = {}

    # 确保其他字段也存在
    for field in ["symptoms", "vitals", "exams", "medications", "family_history", "past_medical_history", "others"]:
        if field not in new_state["patient_info"]:
            new_state["patient_info"][field] = []

    patient_info = new_state["patient_info"]

    for bucket, records in payload.items():
        # 【修改】自动创建不存在的 bucket，而不是抛出错误
        if bucket not in patient_info:
            # 如果是 base_info，初始化为 dict；其他字段初始化为 list
            if bucket == "base_info":
                patient_info[bucket] = {}
            else:
                patient_info[bucket] = []

        existing_list = patient_info[bucket]

        # 【步骤 1】提取当前 bucket 中所有已存在的 ID 集合
        # 用于传给 generate_short_uuid 做去重检查
        existing_ids = {r["id"] for r in existing_list if "id" in r}

        # 【步骤 2】建立映射，用于快速查找需要 update 的记录
        index_by_id = {
            r["id"]: r
            for r in existing_list
            if "id" in r
        }

        for record in records:
            # 尝试获取 payload 里自带的 id
            rec_id = record.get("id")

            if rec_id and rec_id in index_by_id:
                # -------- A. 更新已有记录 --------
                existing = index_by_id[rec_id]
                existing.update(record)
                existing["t_time"] = datetime.now(timezone.utc).isoformat() 
            else:
                # -------- B. 新增记录 --------
                new_record = dict(record)

                # 如果记录里没有 ID，则生成一个新的短 ID
                if not rec_id:
                    # 调用你的生成函数，传入当前的 ID 集合
                    rec_id = generate_short_uuid(existing_ids)
                    new_record["id"] = rec_id
                
                # 【步骤 3】关键：将新 ID 加入集合
                # 这样如果 payload 里下一条数据也要生成 ID，就不会撞上刚刚生成的这个
                existing_ids.add(rec_id)
                new_record["t_time"] = datetime.now(timezone.utc).isoformat()
                existing_list.append(new_record)
    summary = ", ".join([f"{k}: {len(v)} items" for k, v in payload.items()])
    tool_msg = ToolMessage(
        content=f"Facts upserted successfully. Details: {summary}",
        tool_call_id=tool_call_id
    )
                
    return Command(
        update={
            "patient_info": new_state["patient_info"],
            "messages": [tool_msg]
        }
    )
# ==========================================================================
# 批量删除患者事实记录的工具
# ==========================================================================

@tool
def delete_patient_facts(
    payload: Dict[str, List[str]],
    state: Annotated[Dict[str, Any], InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """按 id 批量删除患者事实并返回状态"""
    new_state = deepcopy(state)

    # 安全地获取或初始化 patient_info
    if "patient_info" not in new_state:
        new_state["patient_info"] = {
            "base_info": {},
            "symptoms": [],
            "vitals": [],
            "exams": [],
            "medications": [],
            "family_history": [],
            "past_medical_history": [],
            "others": []
        }

    # 【修复】确保 patient_info 内部结构完整
    if not isinstance(new_state["patient_info"], dict):
        new_state["patient_info"] = {}

    if "base_info" not in new_state["patient_info"]:
        new_state["patient_info"]["base_info"] = {}

    # 确保其他字段也存在
    for field in ["symptoms", "vitals", "exams", "medications", "family_history", "past_medical_history", "others"]:
        if field not in new_state["patient_info"]:
            new_state["patient_info"][field] = []

    patient_info = new_state["patient_info"]

    for bucket, id_list in payload.items():
        # 【修改】自动创建不存在的 bucket，而不是抛出错误
        if bucket not in patient_info:
            # 如果是 base_info，初始化为 dict；其他字段初始化为 list
            if bucket == "base_info":
                patient_info[bucket] = {}
            else:
                patient_info[bucket] = []

        patient_info[bucket] = [
            r for r in patient_info[bucket]
            if r.get("id") not in set(id_list)
        ]

    tool_msg = ToolMessage(
        content=f"Deleted records: {payload}",
        tool_call_id=tool_call_id
    )

    return Command(
        update={
            "patient_info": patient_info,
            "messages": [tool_msg]
        }
    )
# ==========================================================================
# 渲染患者信息为文本的工具
# ==========================================================================
from typing import Any, Dict, Annotated
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

@tool
def patient_info_to_text(
    state: Annotated[Dict[str, Any], InjectedState],
) -> str:
    """将 patient_info 渲染为可读的病历文本"""
    patient_info = state.get("patient_info", {})
    if not patient_info:
        return "No patient information recorded."

    # --- 1. 定义标准展示顺序 ---
    standard_order = [
        "base_info", 
        "symptoms", 
        "vitals", 
        "exams", 
        "medications", 
        "family_history", 
        "past_medical_history",
        "others"
    ]
    
    # 找出实际存在的、但在标准顺序之外的“额外”字段
    all_actual_keys = list(patient_info.keys())
    extra_keys = [k for k in all_actual_keys if k not in standard_order]
    
    # 最终的遍历序列：先标准，后额外
    final_processing_order = standard_order + extra_keys
    
    lines = []
    processed_keys = set() # 防止重复输出

    for bucket in final_processing_order:
        if bucket not in patient_info or bucket in processed_keys:
            continue
        
        value = patient_info[bucket]
        processed_keys.add(bucket)

        # ---- 情况 A：基础信息或单层字典 (dict) ----
        if isinstance(value, dict):
            if not value:
                continue
            lines.append(f"【{bucket.upper().replace('_', ' ')}】")
            for k, v in value.items():
                lines.append(f"- {k}: {v}")
            lines.append("") # 组后空行

        # ---- 情况 B：列表型事实记录 (list[dict]) ----
        elif isinstance(value, list):
            if not value:
                continue
            lines.append(f"【{bucket.upper().replace('_', ' ')}】")
            for record in value:
                if not isinstance(record, dict):
                    continue
                
                # 提取 ID，如果缺失则显示 ??
                rec_id = record.get("id", "??")
                
                # 收集其它临床字段 (排除技术字段)
                fields = []
                for k, v in record.items():
                    if k in ("id", "t_time") or v is None:
                        continue
                    fields.append(f"{k}={v}")
                
                content = "，".join(fields)
                lines.append(f"- [ID: {rec_id}] {content}")
            lines.append("") # 组后空行
            
        # ---- 情况 C：其他类型 (防止意外格式) ----
        else:
            if value:
                lines.append(f"【{bucket.upper()}】\n- {value}\n")

    return "\n".join(lines).strip()

# ========================================== 工具打包==================================================
PatientInfoManger = [set_base_info, upsert_patient_facts, delete_patient_facts, patient_info_to_text]


# ==========================================
# 测试辅助函数（绕过 InjectedToolCallId 限制）
# ==========================================
def test_set_base_info(state: Dict[str, Any], base_info_patch: Dict[str, Any]) -> Command:
    """测试版 set_base_info，跳过 tool_call_id"""
    new_state = deepcopy(state)

    # 【修复】确保 patient_info 结构完整
    if "patient_info" not in new_state:
        new_state["patient_info"] = {}
    if "base_info" not in new_state["patient_info"]:
        new_state["patient_info"]["base_info"] = {}

    new_state["patient_info"]["base_info"].update(base_info_patch)

    tool_msg = ToolMessage(
        content=f"Base info updated successfully: {base_info_patch}",
        tool_call_id="test-call-id"  # 固定的测试ID
    )
    return Command(
        update={
            "patient_info": new_state["patient_info"],
            "messages": [tool_msg]
        }
    )

def test_upsert_patient_facts(state: Dict[str, Any], payload: Dict[str, List[Dict[str, Any]]]) -> Command:
    """测试版 upsert_patient_facts，便于单元测试"""
    new_state = deepcopy(state)

    # 【修复】确保 patient_info 结构完整
    if "patient_info" not in new_state:
        new_state["patient_info"] = {}
    if not isinstance(new_state["patient_info"], dict):
        new_state["patient_info"] = {}

    # 确保所有字段存在
    for field in ["base_info", "symptoms", "vitals", "exams", "medications", "family_history", "past_medical_history", "others"]:
        if field not in new_state["patient_info"]:
            if field == "base_info":
                new_state["patient_info"][field] = {}
            else:
                new_state["patient_info"][field] = []

    patient_info = new_state["patient_info"]

    for bucket, records in payload.items():
        # 【修改】自动创建不存在的 bucket，而不是抛出错误
        if bucket not in patient_info:
            # 如果是 base_info，初始化为 dict；其他字段初始化为 list
            if bucket == "base_info":
                patient_info[bucket] = {}
            else:
                patient_info[bucket] = []

        existing_list = patient_info[bucket]
        existing_ids = {r["id"] for r in existing_list if "id" in r}
        index_by_id = {r["id"]: r for r in existing_list if "id" in r}

        for record in records:
            rec_id = record.get("id")

            if rec_id and rec_id in index_by_id:
                existing = index_by_id[rec_id]
                existing.update(record)
                existing["t_time"] = datetime.now(timezone.utc).isoformat()
            else:
                new_record = dict(record)
                if not rec_id:
                    rec_id = generate_short_uuid(existing_ids)
                    new_record["id"] = rec_id
                existing_ids.add(rec_id)
                new_record["t_time"] = datetime.now(timezone.utc).isoformat()
                existing_list.append(new_record)

    summary = ", ".join([f"{k}: {len(v)} items" for k, v in payload.items()])
    tool_msg = ToolMessage(
        content=f"Facts upserted successfully. Details: {summary}",
        tool_call_id="test-call-id"
    )
    return Command(
        update={
            "patient_info": new_state["patient_info"],
            "messages": [tool_msg]
        }
    )

def test_delete_patient_facts(state: Dict[str, Any], payload: Dict[str, List[str]]) -> Command:
    """测试版 delete_patient_facts，便于单元测试"""
    new_state = deepcopy(state)
    patient_info = new_state["patient_info"]

    for bucket, id_list in payload.items():
        # 【修改】自动创建不存在的 bucket，而不是抛出错误
        if bucket not in patient_info:
            # 如果是 base_info，初始化为 dict；其他字段初始化为 list
            if bucket == "base_info":
                patient_info[bucket] = {}
            else:
                patient_info[bucket] = []

        patient_info[bucket] = [
            r for r in patient_info[bucket]
            if r.get("id") not in set(id_list)
        ]

    tool_msg = ToolMessage(
        content=f"Deleted records: {payload}",
        tool_call_id="test-call-id"
    )
    return Command(
        update={
            "patient_info": patient_info,
            "messages": [tool_msg]
        }
    )

# ==========================================
# 测试代码 (__main__)
# ==========================================
if __name__ == "__main__":
    # 1. 初始化
    initial_state = {
        "messages": [],
        "patient_info": {
            "base_info": {},
            "symptoms": [],
            "vitals": [],
            "exams": [],
            "medications": [],
            "family_history": [],
            "past_medical_history": [],
            "others": []
        }
    }

    current_state = initial_state
    print("=== 初始化状态 ===")
    print(patient_info_to_text.invoke({"state": current_state}) or "(无数据)")

    # 2. 设置 Base Info
    print("\n=== 测试 1: set_base_info ===")
    cmd = test_set_base_info(current_state, {"name": "张三", "age": 35})
    current_state = cmd.update
    print(patient_info_to_text.invoke({"state": current_state}))

    # 3. 新增事实 (验证 ID 前置显示)
    print("\n=== 测试 2: upsert (新增) ===")
    cmd = test_upsert_patient_facts(
        current_state,
        {
            "symptoms": [
                {"name": "咳嗽", "severity": "中度"},
                {"name": "发热", "temperature": "38.5"}
            ],
            "vitals": [{"type": "血压", "value": "120/80"}]
        }
    )
    current_state = cmd.update
    print("--- 渲染结果 (注意 [ID: XX] 在最前面) ---")
    print(patient_info_to_text.invoke({"state": current_state}))

    # 4. 删除
    existing_symptoms = current_state["patient_info"]["symptoms"]
    if existing_symptoms:
        target_id = existing_symptoms[0]["id"]
        print(f"\n=== 测试 3: delete (ID={target_id}) ===")
        cmd = test_delete_patient_facts(current_state, {"symptoms": [target_id]})
        current_state = cmd.update
        print(patient_info_to_text.invoke({"state": current_state}))

