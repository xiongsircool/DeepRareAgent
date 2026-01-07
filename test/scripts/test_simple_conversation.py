#!/usr/bin/env python
"""
简单测试多轮对话是否正常
"""
import asyncio
from langchain_core.messages import HumanMessage
from DeepRareAgent.p01pre_diagnosis_agent import create_pre_diagnosis_node


async def test_simple():
    """简单测试"""
    print("\n" + "=" * 60)
    print("简单多轮对话测试")
    print("=" * 60)

    prediag_node = create_pre_diagnosis_node()

    initial_patient_info = {
        "base_info": {},
        "symptoms": [],
        "vitals": [],
        "exams": [],
        "medications": [],
        "family_history": [],
        "others": []
    }

    # 第1轮
    print("\n📍 第1轮对话")
    state1 = {
        "messages": [HumanMessage(content="你好，我头晕")],
        "patient_info": initial_patient_info,
        "start_diagnosis": False
    }

    try:
        result1 = await prediag_node(state1)
        print(f"[PASS] 第1轮成功")
        print(f"   Messages 数量: {len(result1['messages'])}")
        print(f"   回复: {result1['messages'][0].content[:80]}...")
    except Exception as e:
        print(f"[FAIL] 第1轮失败: {e}")
        return False

    # 第2轮
    print("\n📍 第2轮对话")
    state2 = {
        "messages": state1['messages'] + result1['messages'] + [HumanMessage(content="已经一周了")],
        "patient_info": result1['patient_info'],
        "start_diagnosis": False
    }

    try:
        result2 = await prediag_node(state2)
        print(f"[PASS] 第2轮成功")
        print(f"   Messages 数量: {len(result2['messages'])}")
        print(f"   回复: {result2['messages'][0].content[:80]}...")
    except Exception as e:
        print(f"[FAIL] 第2轮失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 第3轮
    print("\n📍 第3轮对话")
    state3 = {
        "messages": state2['messages'] + result2['messages'] + [HumanMessage(content="还有恶心")],
        "patient_info": result2['patient_info'],
        "start_diagnosis": False
    }

    try:
        result3 = await prediag_node(state3)
        print(f"[PASS] 第3轮成功")
        print(f"   Messages 数量: {len(result3['messages'])}")
        print(f"   回复: {result3['messages'][0].content[:80]}...")
    except Exception as e:
        print(f"[FAIL] 第3轮失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("[SUCCESS] 所有轮次对话成功！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    import sys
    success = asyncio.run(test_simple())
    sys.exit(0 if success else 1)
