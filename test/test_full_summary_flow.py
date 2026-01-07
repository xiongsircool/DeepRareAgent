#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整流程测试：从预诊断到MDT，检查 summary_with_dialogue 的传递

这个测试会：
1. 模拟完整的主图状态
2. 手动触发 start_diagnosis
3. 验证对话总结是否正确生成和传递给MDT
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from langchain_core.messages import HumanMessage, AIMessage
from DeepRareAgent.graph import graph, init_patient_info


async def test_full_workflow():
    """测试完整工作流"""
    
    print("=" * 80)
    print("完整工作流测试：预诊断 → MDT")
    print("=" * 80)
    
    # 场景1：手动设置 start_diagnosis=True，模拟触发诊断的情况
    print("\n场景 1: 手动触发深度诊断（模拟用户确认后）")
    print("-" * 80)
    
    initial_state = {
        # 主图专有字段
        "messages": [
            HumanMessage(content="医生你好，我最近总是头痛"),
            AIMessage(content="您好，请问您多大年龄？性别是？"),
            HumanMessage(content="我25岁，男性"),
            AIMessage(content="头痛持续多久了？是什么样的疼痛？"),
            HumanMessage(content="有3天了，是搏动性的疼痛，感觉像脉搏跳动一样，疼痛程度大概8/10分"),
            AIMessage(content="有家族史吗？之前有类似情况吗？"),
            HumanMessage(content="我妈妈有偏头痛史，我之前没有这样过"),
            AIMessage(content="好的，根据您的描述，我建议进行深度诊断分析"),
            HumanMessage(content="好的，请帮我进行深度诊断"),
        ],
        "start_diagnosis": True,  # 🔑 手动设置为 True，模拟已触发诊断
        "final_report": "",

        # 患者信息字段
        "patient_info": {
            "base_info": {"age": 25, "gender": "男"},
            "symptoms": [
                {"name": "头痛", "duration": "3天", "type": "搏动性", "severity": "8/10"}
            ],
            "vitals": [],
            "exams": [],
            "medications": [],
            "family_history": [{"condition": "偏头痛"}],
            "others": []
        },
        # 🔑 模拟已生成的对话总结（这是理想情况下预诊断应该生成的）
        "summary_with_dialogue": """**患者基本信息：**
- 年龄：25岁
- 性别：男性

**主诉：**
近期头痛，持续3天

**症状描述：**
- 疼痛性质：搏动性疼痛，类似脉搏跳动
- 严重程度：8/10分
- 持续时间：3天

**家族史：**
- 母亲有偏头痛病史

**既往史：**
- 否认既往类似发作

**患者诉求：**
希望进行深度诊断分析""",
        "patient_portrait": "",

        # MDT 输出字段（初始为空）
        "expert_pool": {},
        "blackboard": {
            "published_reports": {},
            "conflicts": {},
            "common_understandings": {}
        },
        "consensus_reached": False,
        "round_count": 0,
        "max_rounds": 3
    }
    
    print("\n初始状态:")
    print(f"  - messages 数量: {len(initial_state['messages'])}")
    print(f"  - start_diagnosis: {initial_state['start_diagnosis']}")
    print(f"  - summary_with_dialogue 长度: {len(initial_state['summary_with_dialogue'])}")
    print(f"\n对话总结内容:")
    print("-" * 80)
    print(initial_state['summary_with_dialogue'])
    print("-" * 80)
    
    try:
        print("\n开始执行主图...")
        print("=" * 80)
        
        # 运行主图
        # 由于 start_diagnosis=True，主图应该跳过预诊断，直接进入 MDT
        result = await graph.ainvoke(initial_state)
        
        print("\n" + "=" * 80)
        print("主图执行完成")
        print("=" * 80)
        
        # 检查结果
        print("\n最终状态:")
        print(f"  - 最终报告长度: {len(result.get('final_report', ''))}")
        print(f"  - expert_pool 数量: {len(result.get('expert_pool', {}))}")
        print(f"  - summary_with_dialogue: {len(result.get('summary_with_dialogue', ''))} 字符")
        
        # 检查专家组的初始消息
        expert_pool = result.get('expert_pool', {})
        if expert_pool:
            print(f"\n检查专家组初始消息:")
            for group_id, expert_state in list(expert_pool.items())[:1]:  # 只检查第一个专家组
                messages = expert_state.get('messages', [])
                if messages:
                    first_msg = messages[0].content if hasattr(messages[0], 'content') else str(messages[0])
                    print(f"\n{group_id} 的初始消息:")
                    print("-" * 80)
                    print(first_msg[:500] + "..." if len(first_msg) > 500 else first_msg)
                    print("-" * 80)
                    
                    # 关键检查
                    if "预诊问诊对话总结" in first_msg:
                        print("\n[PASS] 成功！专家组消息包含对话总结")
                    else:
                        print("\n[FAIL] 失败！专家组消息不包含对话总结")
        
        # 显示最终消息
        final_messages = result.get('messages', [])
        print(f"\n消息历史（最后3条）:")
        for msg in final_messages[-3:]:
            if hasattr(msg, 'content'):
                print(f"  - {type(msg).__name__}: {msg.content[:100]}...")
        
    except Exception as e:
        print(f"\n[FAIL] 执行失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    await test_full_workflow()


if __name__ == "__main__":
    asyncio.run(main())
