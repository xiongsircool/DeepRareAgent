"""
用于测试/演示维护 `state["patient_info"]` 的一组工具函数（LangChain Tool）。

这些工具遵循 LangGraph 的推荐写法：返回 `Command(update=...)` 来更新图状态，
从而让节点逻辑尽量保持“纯函数”（不就地修改入参 state，避免副作用/并发问题）。
"""

from typing import List, Dict, Any
from typing_extensions import Annotated, TypedDict

from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph.message import add_messages


from uuid import uuid4
from datetime import datetime
from copy import deepcopy
from langgraph.types import Command
import shortuuid

def generate_short_uuid(existing_ids: set) -> str:
    # 初始化一个针对该字母表的生成器
    run = shortuuid.ShortUUID(alphabet="23456789ABCDEFGHJKLMNPQRSTUVWXYZ")
    while True:
        # 生成 2 位
        new_id = run.random(length=2)
        if new_id not in existing_ids:
            return new_id
        
        

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
@tool
def set_base_info(
    state: Dict[str, Any],
    base_info_patch: Dict[str, Any],
) -> Command:
    """
    更新患者基础信息（`patient_info.base_info`）。

    用途：
    - 写入/覆盖姓名、性别、年龄、主诉等“当前快照”字段
    - 适合结构稳定的键值对信息（dict）

    行为：
    - 内部会 `deepcopy(state)`，不会就地修改入参
    - 对 `state["patient_info"]["base_info"]` 执行 `update(base_info_patch)`
    - 仅覆盖 patch 中出现的 key；不会清空其它字段
    - 不负责“删除字段”。如需删除，可将值置为 `None`，或实现专用删除工具

    参数：
    - state: LangGraph 状态对象，要求至少包含 `patient_info.base_info`
    - base_info_patch: 需要合并进去的字段补丁（只写入/覆盖提供的字段）

    返回：
    - `Command(update=new_state)`：携带更新后的 state，供 LangGraph 写回
    """
    new_state = deepcopy(state)
    new_state["patient_info"]["base_info"].update(base_info_patch)
    return Command(update=new_state)




@tool
def upsert_patient_facts(
    state: Dict[str, Any],
    payload: Dict[str, List[Dict[str, Any]]],
) -> Command:
    """
    批量 Upsert 患者“事实记录”，支持自动生成短 UUID。
    """
    new_state = deepcopy(state)
    patient_info = new_state["patient_info"]

    for bucket, records in payload.items():
        if bucket not in patient_info:
            raise ValueError(f"Unknown bucket: {bucket}")

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
                existing["t_time"] = datetime.utcnow().isoformat()
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

                new_record["t_time"] = datetime.utcnow().isoformat()
                existing_list.append(new_record)

    return Command(update=new_state)


@tool
def delete_patient_facts(
    state: Dict[str, Any],
    payload: Dict[str, List[str]],
) -> Command:
    """
    批量删除患者事实记录（按 `id` 过滤 `patient_info.<bucket>`）。

    行为：
    - 支持一次删除多个 bucket
    - bucket 不存在 → `ValueError`
    - id 不存在 → 会被自然忽略（过滤后列表不变）
    - 不会影响 `base_info`

    payload 示例：
    {
        "symptoms": ["<id1>", "<id2>"],
        "exams": ["<id3>"]
    }

    返回：
    - `Command(update=new_state)`
    """
    new_state = deepcopy(state)
    patient_info = new_state["patient_info"]

    for bucket, id_list in payload.items():
        if bucket not in patient_info:
            raise ValueError(f"Unknown bucket: {bucket}")

        patient_info[bucket] = [
            r for r in patient_info[bucket]
            if r.get("id") not in set(id_list)
        ]

    return Command(update=new_state)


@tool
def patient_info_to_text(
    state: Dict[str, Any],
) -> str:
    """
    将 `state["patient_info"]` 渲染为可读文本，便于调试/日志/上下文摘要。

    展示规则：
    - `base_info`（dict）：按 `- key: value` 逐行展示
    - 其它 bucket（list[dict]）：逐条展示，默认隐藏 `id` 与 `t_time`
    - 仅做格式化展示，不修改 state

    返回：
    - 文本字符串；若没有可展示信息则返回空字符串
    """
    patient_info = state.get("patient_info", {})
    lines = []

    for bucket, value in patient_info.items():
        # ---- base_info：dict ----
        if isinstance(value, dict):
            if not value:
                continue
            lines.append(f"【{bucket}】")
            for k, v in value.items():
                lines.append(f"- {k}: {v}")
            continue

        # ---- 其他 bucket：list[dict] ----
        if isinstance(value, list):
            if not value:
                continue
            lines.append(f"\n【{bucket}】")
            for record in value:
                fields = []
                for k, v in record.items():
                    if k in ("id", "t_time"):
                        continue
                    fields.append(f"{k}={v}")
                if fields:
                    lines.append("- " + "，".join(fields))

    return "\n".join(lines)


if __name__ == "__main__":
    from pprint import pprint

    # ---------- 1. 初始化 state ----------
    state = {
        "messages": [],
        "patient_info": {
            "base_info": {},
            "symptoms": [],
            "vitals": [],
            "exams": [],
            "medications": [],
            "family_history": [],
            "others": [],
        }
    }

    print("\n===== 初始 state =====")
    pprint(state)

    # ---------- 2. 测试 set_base_info ----------
    print("\n===== 测试 set_base_info =====")
    cmd = set_base_info.invoke({
        "state": state,
        "base_info_patch": {
            "name": "张三",
            "age": 56,
            "sex": "男"
        }
    })
    state = cmd.update
    pprint(state["patient_info"]["base_info"])

    # ---------- 3. 测试 upsert_patient_facts（首次批量导入） ----------
    print("\n===== 测试 upsert_patient_facts（新增） =====")
    cmd = upsert_patient_facts.invoke({
        "state": state,
        "payload": {
            "symptoms": [
                {"key": "头痛", "value": True, "time": "最近三天"},
                {"key": "头晕", "value": True}
            ],
            "vitals": [
                {"key": "血压", "value": "160/100", "time": "昨天晚上"}
            ],
            "family_history": [
                {"key": "高血压", "value": "父亲患有"}
            ]
        }
    })
    state = cmd.update
    pprint(state["patient_info"])

    # 记录一个 id，后面用来更新 & 删除
    symptom_id = state["patient_info"]["symptoms"][0]["id"]

    # ---------- 4. 测试 upsert_patient_facts（带 id 更新） ----------
    print("\n===== 测试 upsert_patient_facts（更新） =====")
    cmd = upsert_patient_facts.invoke({
        "state": state,
        "payload": {
            "symptoms": [
                {
                    "id": symptom_id,
                    "severity": "加重",
                    "time": "最近三天"
                }
            ]
        }
    })
    state = cmd.update
    pprint(state["patient_info"]["symptoms"])

    # ---------- 5. 测试 delete_patient_facts ----------
    print("\n===== 测试 delete_patient_facts =====")
    cmd = delete_patient_facts.invoke({
        "state": state,
        "payload": {
            "symptoms": [symptom_id]
        }
    })
    state = cmd.update
    pprint(state["patient_info"]["symptoms"])

    # ---------- 6. 测试 patient_info_to_text ----------
    print("\n===== 测试 patient_info_to_text =====")
    text = patient_info_to_text.invoke({
        "state": state
    })
    print(text)
