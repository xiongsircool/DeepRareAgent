#!/usr/bin/env python
"""
测试多轮对话中的消息流转
"""
import asyncio
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from DeepRareAgent.p01pre_diagnosis_agent import create_pre_diagnosis_node


async def test_multi_round():
    """测试多轮对话"""
    print("\n" + "=" * 60)
    print("多轮对话测试")
    print("=" * 60)

    # 创建预诊断节点
    prediag_node = create_pre_diagnosis_node()

    # 初始化患者信息
    initial_patient_info = {
        "base_info": {},
        "symptoms": [],
        "vitals": [],
        "exams": [],
        "medications": [],
        "family_history": [],
        "others": []
    }

    # ===== 第 1 轮对话 =====
    print("\n" + "-" * 60)
    print("第 1 轮对话")
    print("-" * 60)

    state_round1 = {
        "messages": [HumanMessage(content="你好，我最近总是头晕")],
        "patient_info": initial_patient_info,
        "start_diagnosis": False
    }

    print(f"\n📨 第1轮输入 messages 数量: {len(state_round1['messages'])}")
    print(f"   内容: {[type(m).__name__ for m in state_round1['messages']]}")

    result_round1 = await prediag_node(state_round1)

    print(f"\n📤 第1轮输出 messages 数量: {len(result_round1['messages'])}")
    print(f"   内容: {[type(m).__name__ for m in result_round1['messages']]}")
    print(f"\n   AI 回复: {result_round1['messages'][0].content[:100]}...")

    # 构建第2轮的完整 messages（模拟 LangGraph 的 add_messages 行为）
    messages_after_round1 = state_round1['messages'] + result_round1['messages']

    # ===== 第 2 轮对话 =====
    print("\n" + "-" * 60)
    print("第 2 轮对话")
    print("-" * 60)

    state_round2 = {
        "messages": messages_after_round1 + [HumanMessage(content="已经持续一周了，而且伴随恶心")],
        "patient_info": result_round1['patient_info'],  # 使用第1轮更新后的患者信息
        "start_diagnosis": False
    }

    print(f"\n📨 第2轮输入 messages 数量: {len(state_round2['messages'])}")
    print(f"   内容: {[type(m).__name__ for m in state_round2['messages']]}")

    result_round2 = await prediag_node(state_round2)

    print(f"\n📤 第2轮输出 messages 数量: {len(result_round2['messages'])}")
    print(f"   内容: {[type(m).__name__ for m in result_round2['messages']]}")
    print(f"\n   AI 回复: {result_round2['messages'][0].content[:100]}...")

    # 构建第3轮的完整 messages
    messages_after_round2 = state_round2['messages'] + result_round2['messages']

    # ===== 第 3 轮对话 =====
    print("\n" + "-" * 60)
    print("第 3 轮对话")
    print("-" * 60)

    state_round3 = {
        "messages": messages_after_round2 + [HumanMessage(content="还有失眠的症状")],
        "patient_info": result_round2['patient_info'],
        "start_diagnosis": False
    }

    print(f"\n📨 第3轮输入 messages 数量: {len(state_round3['messages'])}")
    print(f"   内容: {[type(m).__name__ for m in state_round3['messages']]}")

    result_round3 = await prediag_node(state_round3)

    print(f"\n📤 第3轮输出 messages 数量: {len(result_round3['messages'])}")
    print(f"   内容: {[type(m).__name__ for m in result_round3['messages']]}")
    print(f"\n   AI 回复: {result_round3['messages'][0].content[:100]}...")

    # ===== 分析结果 =====
    print("\n" + "=" * 60)
    print("测试分析")
    print("=" * 60)

    # 检查是否有 SystemMessage 泄漏到对话历史中
    all_messages = messages_after_round2 + result_round3['messages']

    human_count = sum(1 for m in all_messages if isinstance(m, HumanMessage))
    ai_count = sum(1 for m in all_messages if isinstance(m, AIMessage))
    system_count = sum(1 for m in all_messages if isinstance(m, SystemMessage))

    print(f"\n📊 最终 messages 统计:")
    print(f"   HumanMessage: {human_count}")
    print(f"   AIMessage: {ai_count}")
    print(f"   SystemMessage: {system_count}")

    print(f"\n✅ 预期结果:")
    print(f"   HumanMessage: 3 (3轮用户输入)")
    print(f"   AIMessage: 3 (3轮AI回复)")
    print(f"   SystemMessage: 0 (不应该保存到对话历史)")

    # 检查是否符合预期
    success = (
        human_count == 3 and
        ai_count == 3 and
        system_count == 0
    )

    if success:
        print(f"\n🎉 测试通过！SystemMessage 没有泄漏到对话历史中")
    else:
        print(f"\n⚠️ 测试失败！对话历史中出现了意外的消息")
        print(f"\n   详细消息类型:")
        for i, msg in enumerate(all_messages, 1):
            print(f"   {i}. {type(msg).__name__}: {msg.content[:50]}...")

    return success


def main():
    """运行测试"""
    print("\n" + "=" * 60)
    print("多轮对话消息流转测试")
    print("=" * 60)

    success = asyncio.run(test_multi_round())

    print("\n" + "=" * 60)
    if success:
        print("✅ 多轮对话测试通过")
        print("✅ PatientContextPlugin 修复成功")
    else:
        print("❌ 多轮对话测试失败")
    print("=" * 60 + "\n")

    return success


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
