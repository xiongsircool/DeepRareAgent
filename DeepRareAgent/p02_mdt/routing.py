"""
MDT 多专家会诊系统 - 路由控制
负责判断是否达成共识或超出最大轮数，决定流程走向
"""
from typing import Literal
from DeepRareAgent.schema import MDTGraphState


def should_continue_diagnosis(state: MDTGraphState) -> Literal["continue", "end"]:
    """
    判断是否继续诊断还是结束流程

    路由逻辑：
    1. 如果达成共识（consensus_reached=True）→ END
    2. 如果超出最大轮数（round_count >= max_rounds）→ END
    3. 否则 → 继续诊断（回到专家节点）

    Args:
        state: MDTGraphState 全局状态

    Returns:
        "continue": 继续诊断（回到专家节点）
        "end": 结束流程
    """
    round_count = state.get("round_count", 0)
    max_rounds = state.get("max_rounds", 3)
    consensus_reached = state.get("consensus_reached", False)

    # 打印当前状态
    print("\n" + "=" * 60)
    print("MDT 路由判断")
    print("=" * 60)
    print(f"当前轮数: {round_count}/{max_rounds}")
    print(f"共识状态: {consensus_reached}")

    # 判断结束条件
    if consensus_reached:
        print("所有专家达成共识，结束诊断流程")
        print("=" * 60 + "\n")
        return "end"

    if round_count >= max_rounds:
        print("已达到最大轮数限制，结束诊断流程")
        print("=" * 60 + "\n")
        return "end"

    # 继续诊断
    print(f"未达成共识，进入第 {round_count + 1} 轮诊断")
    print("=" * 60 + "\n")
    return "continue"


def get_active_experts(state: MDTGraphState) -> list[str]:
    """
    获取需要继续诊断的专家组 ID 列表

    只返回满足以下条件的专家：
    - is_satisfied = False（未满意）
    - has_error = False（无错误）

    Args:
        state: MDTGraphState 全局状态

    Returns:
        需要继续诊断的专家组 ID 列表，例如 ["group_1", "group_2"]
    """
    expert_pool = state.get("expert_pool", {})
    active_experts = [
        group_id
        for group_id, expert in expert_pool.items()
        if not expert.get("is_satisfied", False)  # 未满意
        and not expert.get("has_error", False)     # 无错误
    ]

    print(f"[SEARCH] 活跃专家组: {active_experts}")
    return active_experts


if __name__ == "__main__":
    """测试路由逻辑"""

    # 测试案例1：未达成共识，未超出轮数
    print("\n【测试1】未达成共识，未超出轮数")
    test_state_1: MDTGraphState = {
        "patient_info": {},
        "summary_with_dialogue": "",
        "patient_portrait": "",
        "expert_pool": {
            "group_1": {"is_satisfied": False, "has_error": False},
            "group_2": {"is_satisfied": False, "has_error": False},
        },
        "blackboard": {"published_reports": {}, "conflicts": {}, "common_understandings": {}},
        "round_count": 1,
        "max_rounds": 3,
        "consensus_reached": False
    }
    result_1 = should_continue_diagnosis(test_state_1)
    print(f"路由结果: {result_1}")
    assert result_1 == "continue", "应该继续诊断"

    # 测试案例2：达成共识
    print("\n【测试2】达成共识")
    test_state_2: MDTGraphState = {
        "patient_info": {},
        "summary_with_dialogue": "",
        "patient_portrait": "",
        "expert_pool": {
            "group_1": {"is_satisfied": True, "has_error": False},
            "group_2": {"is_satisfied": True, "has_error": False},
        },
        "blackboard": {"published_reports": {}, "conflicts": {}, "common_understandings": {}},
        "round_count": 2,
        "max_rounds": 3,
        "consensus_reached": True
    }
    result_2 = should_continue_diagnosis(test_state_2)
    print(f"路由结果: {result_2}")
    assert result_2 == "end", "应该结束"

    # 测试案例3：超出最大轮数
    print("\n【测试3】超出最大轮数")
    test_state_3: MDTGraphState = {
        "patient_info": {},
        "summary_with_dialogue": "",
        "patient_portrait": "",
        "expert_pool": {
            "group_1": {"is_satisfied": False, "has_error": False},
            "group_2": {"is_satisfied": False, "has_error": False},
        },
        "blackboard": {"published_reports": {}, "conflicts": {}, "common_understandings": {}},
        "round_count": 3,
        "max_rounds": 3,
        "consensus_reached": False
    }
    result_3 = should_continue_diagnosis(test_state_3)
    print(f"路由结果: {result_3}")
    assert result_3 == "end", "应该结束"

    # 测试案例4：获取活跃专家
    print("\n【测试4】获取活跃专家")
    test_state_4: MDTGraphState = {
        "patient_info": {},
        "summary_with_dialogue": "",
        "patient_portrait": "",
        "expert_pool": {
            "group_1": {"is_satisfied": False, "has_error": False},  # 活跃
            "group_2": {"is_satisfied": True, "has_error": False},   # 已满意，跳过
            "group_3": {"is_satisfied": False, "has_error": True},   # 有错误，跳过
        },
        "blackboard": {"published_reports": {}, "conflicts": {}, "common_understandings": {}},
        "round_count": 1,
        "max_rounds": 3,
        "consensus_reached": False
    }
    active = get_active_experts(test_state_4)
    print(f"活跃专家: {active}")
    assert active == ["group_1"], "只有 group_1 应该继续诊断"

    print("\n" + "=" * 60)
    print("[PASS] 所有测试通过！")
    print("=" * 60)
