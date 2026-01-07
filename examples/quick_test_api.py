#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试 LangGraph API 连接和功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.api_client import DeepRareAgentClient, print_stream_events


async def test_connection():
    """测试 1: 连接测试"""
    print("=" * 80)
    print("测试 1: 服务连接")
    print("=" * 80)
    
    try:
        async with DeepRareAgentClient() as client:
            info = await client.get_info()
            print(f"[PASS] 连接成功!")
            print(f"   版本: {info.get('version')}")
            print(f"   可用图: {info.get('graphs')}")
            return True
    except Exception as e:
        print(f"[FAIL] 连接失败: {e}")
        print("\n请确保已启动 LangGraph 服务:")
        print("   uv run langgraph dev")
        return False


async def test_create_thread():
    """测试 2: 创建会话"""
    print("\n" + "=" * 80)
    print("测试 2: 创建会话")
    print("=" * 80)
    
    try:
        async with DeepRareAgentClient() as client:
            thread_id = await client.create_thread(
                metadata={"test": "quick_test"}
            )
            print(f"[PASS] 会话创建成功!")
            print(f"   Thread ID: {thread_id}")
            return thread_id
    except Exception as e:
        print(f"[FAIL] 创建会话失败: {e}")
        return None


async def test_simple_message(thread_id: str):
    """测试 3: 发送简单消息"""
    print("\n" + "=" * 80)
    print("测试 3: 发送消息")
    print("=" * 80)
    
    try:
        async with DeepRareAgentClient() as client:
            print("\n发送: 医生你好")
            events = await client.send_message(thread_id, "医生你好")
            
            # 收集AI回复
            ai_response = ""
            async for event in events:
                if event.event == "messages/partial":
                    for msg in event.data:
                        if msg.get("type") == "ai":
                            content = msg.get("content", "")
                            ai_response += content
                            print(content, end="", flush=True)
            
            print(f"\n\n[PASS] 消息发送成功!")
            print(f"   AI 回复长度: {len(ai_response)} 字符")
            return True
    except Exception as e:
        print(f"\n[FAIL] 发送消息失败: {e}")
        return False


async def test_diagnosis_flow(thread_id: str):
    """测试 4: 完整诊断流程"""
    print("\n" + "=" * 80)
    print("测试 4: 完整诊断流程")
    print("=" * 80)
    
    try:
        async with DeepRareAgentClient() as client:
            # 模拟多轮对话
            messages = [
                "我25岁，男性",
                "我头痛3天了",
                "搏动性疼痛，8/10分",
                "我妈妈有偏头痛史",
                "请帮我深度诊断"
            ]
            
            for msg in messages:
                print(f"\n用户: {msg}")
                events = await client.send_message(thread_id, msg)
                
                # 只打印关键事件
                async for event in events:
                    if event.event == "values":
                        data = event.data
                        if data.get("start_diagnosis"):
                            print("[LAB] 触发深度诊断!")
                        if data.get("summary_with_dialogue"):
                            summary = data["summary_with_dialogue"]
                            print(f"[NOTE] 对话总结: {summary[:100]}...")
                        if data.get("final_report"):
                            print(f"[PASS] 诊断完成!")
                
                await asyncio.sleep(1)  # 避免请求过快
            
            # 获取最终状态
            state = await client.get_state(thread_id)
            final_report = state["values"].get("final_report", "")
            
            print("\n" + "=" * 80)
            print("最终诊断报告")
            print("=" * 80)
            if final_report:
                print(final_report[:500] + "..." if len(final_report) > 500 else final_report)
                return True
            else:
                print("[WARN] 未生成最终报告")
                return False
                
    except Exception as e:
        print(f"\n[FAIL] 诊断流程失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_state_retrieval(thread_id: str):
    """测试 5: 状态查询"""
    print("\n" + "=" * 80)
    print("测试 5: 状态查询")
    print("=" * 80)
    
    try:
        async with DeepRareAgentClient() as client:
            # 获取当前状态
            state = await client.get_state(thread_id)
            
            print("[PASS] 状态查询成功!")
            print(f"   消息数: {len(state['values'].get('messages', []))}")
            print(f"   诊断状态: {state['values'].get('start_diagnosis', False)}")
            print(f"   共识达成: {state['values'].get('consensus_reached', False)}")
            
            # 获取历史
            history = await client.get_history(thread_id)
            print(f"   历史记录数: {len(history)}")
            
            return True
    except Exception as e:
        print(f"[FAIL] 状态查询失败: {e}")
        return False


async def main():
    """主测试流程"""
    print("\n" + "[LAB] " * 20)
    print("DeepRareAgent API 快速测试")
    print("[LAB] " * 20 + "\n")
    
    # 测试 1: 连接
    if not await test_connection():
        return
    
    # 测试 2: 创建会话
    thread_id = await test_create_thread()
    if not thread_id:
        return
    
    # 测试 3: 简单消息
    if not await test_simple_message(thread_id):
        return
    
    # 测试 4: 完整诊断（可选，时间较长）
    print("\n[TIME]  完整诊断测试需要几分钟时间，是否继续？")
    print("   按 Enter 继续，Ctrl+C 跳过...")
    try:
        input()
        await test_diagnosis_flow(thread_id)
    except KeyboardInterrupt:
        print("\n[SKIP]  跳过诊断测试")
    
    # 测试 5: 状态查询
    await test_state_retrieval(thread_id)
    
    print("\n" + "=" * 80)
    print("[PASS] 所有测试完成!")
    print("=" * 80)
    print(f"\n💡 提示:")
    print(f"   - 会话 ID: {thread_id}")
    print(f"   - 可以在 LangGraph Studio 中查看: http://localhost:2024")
    print(f"   - 运行完整示例: python examples/api_client.py")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 测试已取消")
