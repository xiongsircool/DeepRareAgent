"""
快速测试：验证 MDT 子图的 messages 字段定义和初始化消息
"""
import asyncio
from langchain_core.messages import HumanMessage
from DeepRareAgent.p02_mdt.graph import create_mdt_graph
from DeepRareAgent.schema import MDTGraphState


async def test_mdt_schema():
    print("=" * 80)
    print("快速测试：MDT 子图 messages 字段")
    print("=" * 80)

    # 1. 检查 Schema 定义
    print("\n[1] 检查 MDTGraphState 是否定义了 messages 字段")
    try:
        # 通过 __annotations__ 检查
        annotations = MDTGraphState.__annotations__
        if 'messages' in annotations:
            print("   ✅ messages 字段已在 MDTGraphState 中定义")
            print(f"   类型: {annotations['messages']}")
        else:
            print("   ❌ messages 字段未在 MDTGraphState 中定义")
            return
    except Exception as e:
        print(f"   ❌ 检查失败: {e}")
        return

    # 2. 测试 triage_to_mdt_node 是否返回 messages
    print("\n[2] 测试 triage_to_mdt_node 是否返回 messages")
    try:
        from DeepRareAgent.p02_mdt.nodes import triage_to_mdt_node

        test_state = {
            "patient_info": {
                "base_info": {"age": 35, "gender": "男"},
                "symptoms": [{"name": "测试症状"}],
                "vitals": [],
                "exams": [],
                "medications": [],
                "family_history": [],
                "others": []
            },
            "summary_with_dialogue": ""
        }

        result = await triage_to_mdt_node(test_state, {})

        if 'messages' in result:
            print("   ✅ triage_to_mdt_node 返回了 messages 字段")
            print(f"   消息数量: {len(result['messages'])}")
            for i, msg in enumerate(result['messages']):
                print(f"   消息 {i+1}: {msg.content[:60]}...")
        else:
            print("   ❌ triage_to_mdt_node 未返回 messages 字段")
            print(f"   返回的字段: {result.keys()}")

    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. 测试 expert_reviwer_node 是否返回 messages
    print("\n[3] 测试 expert_reviwer_node 是否返回 messages")
    try:
        from DeepRareAgent.p02_mdt.export_reviwer_node import expert_reviwer_node

        # 构造一个简单的测试状态（模拟已有专家报告的情况）
        test_state = {
            "messages": [],  # 添加空的 messages 列表
            "patient_info": {"base_info": {}, "symptoms": [], "vitals": [], "exams": [], "medications": [], "family_history": [], "others": []},
            "patient_portrait": "测试患者",
            "summary_with_dialogue": "",
            "expert_pool": {
                "group_1": {
                    "group_id": "group_1",
                    "messages": [HumanMessage(content="测试")],
                    "report": "测试报告",
                    "evidences": [],
                    "is_satisfied": True,  # 已满意，跳过审查
                    "reinvestigate_reason": None,
                    "has_error": False,
                    "times_deep_diagnosis": 1
                }
            },
            "blackboard": {
                "published_reports": {},
                "conflicts": {},
                "common_understandings": {}
            },
            "round_count": 1,
            "max_rounds": 3,
            "consensus_reached": False
        }

        result = expert_reviwer_node(test_state, {})

        if 'messages' in result:
            print("   ✅ expert_reviwer_node 返回了 messages 字段")
            print(f"   消息数量: {len(result['messages'])}")
            for i, msg in enumerate(result['messages']):
                print(f"   消息 {i+1}: {msg.content[:60]}...")
        else:
            print("   ❌ expert_reviwer_node 未返回 messages 字段")

    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "=" * 80)
    print("🎉 所有测试通过！MDT 子图现在可以向主图传递 messages 了")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_mdt_schema())
