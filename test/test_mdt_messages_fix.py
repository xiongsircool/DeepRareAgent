"""
测试：验证 MDT 子图是否能正确向主图传递 messages
"""
import asyncio
from langchain_core.messages import HumanMessage
from DeepRareAgent.graph import create_main_graph, init_patient_info


async def test_mdt_messages():
    print("=" * 80)
    print("测试：验证 MDT 子图 messages 传递到主图")
    print("=" * 80)

    # 1. 创建主图
    graph = create_main_graph()

    # 2. 准备初始状态（直接触发深度诊断）
    initial_state = {
        "messages": [HumanMessage(content="用户输入：我想进行诊断")],
        "start_diagnosis": True,  # 直接触发深度诊断
        "final_report": "",
        "patient_info": {
            "base_info": {"age": 35, "gender": "男"},
            "symptoms": [{"name": "四肢疼痛", "duration": "10年"}],
            "vitals": [],
            "exams": [],
            "medications": [],
            "family_history": [],
            "others": []
        },
        "summary_with_dialogue": "",
        "patient_portrait": "",
        "expert_pool": {},
        "blackboard": {
            "published_reports": {},
            "conflicts": {},
            "common_understandings": {}
        },
        "consensus_reached": False,
        "round_count": 0,
        "max_rounds": 1  # 只运行 1 轮以加快测试
    }

    print("\n[初始状态]")
    print(f"  messages 数量: {len(initial_state['messages'])}")
    for i, msg in enumerate(initial_state['messages']):
        print(f"    {i+1}. {msg.__class__.__name__}: {msg.content[:50]}...")

    print("\n[开始执行主图（跳过预诊断，直接进入 MDT）]")
    print("  注意：由于 start_diagnosis=True，会直接进入 MDT 会诊")

    try:
        # 运行图（设置较短的超时时间，因为这是测试）
        result = await asyncio.wait_for(
            graph.ainvoke(initial_state),
            timeout=120  # 2 分钟超时
        )

        print("\n" + "=" * 80)
        print("[最终状态]")
        print("=" * 80)
        print(f"  messages 数量: {len(result['messages'])}")
        print("\n  messages 列表:")
        for i, msg in enumerate(result['messages']):
            content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            print(f"    {i+1}. [{msg.__class__.__name__}] {content}")

        print("\n" + "=" * 80)
        print("[结论]")
        print("=" * 80)

        # 检查预期的消息
        messages_content = [msg.content for msg in result['messages']]

        # 检查是否有 MDT 初始化消息
        has_mdt_init = any("初始化多专家会诊系统" in content for content in messages_content)
        # 检查是否有专家互审消息
        has_expert_review = any("专家互审完成" in content for content in messages_content)
        # 检查是否有最终报告
        has_final_report = result.get('final_report', '') != ''

        print(f"✅ MDT 初始化消息: {'存在' if has_mdt_init else '❌ 缺失'}")
        print(f"✅ 专家互审消息: {'存在' if has_expert_review else '❌ 缺失'}")
        print(f"✅ 最终报告: {'存在' if has_final_report else '❌ 缺失'}")

        if has_mdt_init and has_expert_review:
            print("\n🎉 成功！MDT 子图成功向主图传递 messages！")
        else:
            print("\n⚠️  部分消息缺失，请检查实现")

    except asyncio.TimeoutError:
        print("\n❌ 测试超时（可能是因为 LLM 调用较慢或配置问题）")
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mdt_messages())