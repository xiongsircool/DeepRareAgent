#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepRareAgent API 客户端封装

提供简洁的 Python 接口来调用 LangGraph 服务
"""

import httpx
import json
import asyncio
from typing import Optional, Dict, Any, AsyncIterator, List
from dataclasses import dataclass
from enum import Enum


class StreamMode(Enum):
    """流式模式"""
    VALUES = "values"           # 完整状态更新
    MESSAGES = "messages"       # 消息更新
    UPDATES = "updates"         # 增量更新
    DEBUG = "debug"             # 调试信息


@dataclass
class StreamEvent:
    """流式事件"""
    event: str                  # 事件类型: metadata, values, messages, end
    data: Any                   # 事件数据
    raw: str                    # 原始数据


class DeepRareAgentClient:
    """DeepRareAgent API 客户端"""
    
    def __init__(
        self,
        base_url: str = "http://localhost:2024",
        timeout: float = 300.0,
        assistant_id: str = "agent"
    ):
        """
        初始化客户端
        
        Args:
            base_url: LangGraph 服务地址
            timeout: 请求超时时间（秒）
            assistant_id: 助手ID（对应 langgraph.json 中的 graph 名称）
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.assistant_id = assistant_id
        self.client = httpx.AsyncClient(timeout=timeout)
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    # === 基础 API ===
    
    async def get_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        response = await self.client.get(f"{self.base_url}/info")
        response.raise_for_status()
        return response.json()
    
    async def create_thread(self, metadata: Optional[Dict] = None) -> str:
        """
        创建新会话
        
        Returns:
            thread_id: 会话ID
        """
        payload = {"metadata": metadata or {}}
        response = await self.client.post(
            f"{self.base_url}/threads",
            json=payload
        )
        response.raise_for_status()
        return response.json()["thread_id"]
    
    async def get_state(self, thread_id: str) -> Dict[str, Any]:
        """
        获取会话当前状态
        
        Args:
            thread_id: 会话ID
            
        Returns:
            状态字典，包含 values, next, config 等
        """
        response = await self.client.get(
            f"{self.base_url}/threads/{thread_id}/state"
        )
        response.raise_for_status()
        return response.json()
    
    async def get_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """
        获取会话历史
        
        Args:
            thread_id: 会话ID
            
        Returns:
            历史状态列表
        """
        response = await self.client.get(
            f"{self.base_url}/threads/{thread_id}/history"
        )
        response.raise_for_status()
        result = response.json()
        # 如果返回的是字典且有values字段，返回values；否则返回整个结果
        if isinstance(result, dict) and "values" in result:
            return result["values"]
        return result if isinstance(result, list) else []
    
    # === 运行 API ===
    
    async def run(
        self,
        thread_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        同步运行（等待完成后返回结果）
        
        Args:
            thread_id: 会话ID
            input_data: 输入数据
            config: 配置
            
        Returns:
            运行结果
        """
        payload = {
            "assistant_id": self.assistant_id,
            "input": input_data,
            "config": config or {}
        }
        
        response = await self.client.post(
            f"{self.base_url}/threads/{thread_id}/runs",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def stream(
        self,
        thread_id: str,
        input_data: Optional[Dict[str, Any]] = None,
        stream_mode: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[StreamEvent]:
        """
        流式运行（实时获取事件）
        
        Args:
            thread_id: 会话ID
            input_data: 输入数据
            stream_mode: 流式模式列表
            config: 配置
            
        Yields:
            StreamEvent: 流式事件
        """
        payload = {
            "assistant_id": self.assistant_id,
            "input": input_data,
            "stream_mode": stream_mode or ["values", "messages"],
            "config": config or {}
        }
        
        async with self.client.stream(
            "POST",
            f"{self.base_url}/threads/{thread_id}/runs/stream",
            json=payload
        ) as response:
            response.raise_for_status()
            
            current_event = None
            async for line in response.aiter_lines():
                line = line.strip()
                
                if line.startswith("event: "):
                    current_event = line[7:]  # 移除 "event: "
                    
                elif line.startswith("data: "):
                    data_str = line[6:]  # 移除 "data: "
                    
                    if data_str and data_str != "[DONE]":
                        try:
                            data = json.loads(data_str)
                            yield StreamEvent(
                                event=current_event or "unknown",
                                data=data,
                                raw=data_str
                            )
                        except json.JSONDecodeError:
                            # 忽略无法解析的数据
                            pass
    
    # === 高级 API ===
    
    async def send_message(
        self,
        thread_id: str,
        message: str,
        stream: bool = True
    ) -> AsyncIterator[StreamEvent] | Dict[str, Any]:
        """
        发送用户消息（简化接口）
        
        Args:
            thread_id: 会话ID
            message: 用户消息
            stream: 是否使用流式
            
        Returns:
            流式时返回事件迭代器，否则返回最终结果
        """
        input_data = {
            "messages": [
                {
                    "role": "human",
                    "content": message
                }
            ]
        }
        
        if stream:
            return self.stream(thread_id, input_data)
        else:
            return await self.run(thread_id, input_data)
    
    async def start_diagnosis(
        self,
        thread_id: str,
        patient_info: Dict[str, Any]
    ) -> AsyncIterator[StreamEvent]:
        """
        直接开始深度诊断（跳过预诊断）
        
        Args:
            thread_id: 会话ID
            patient_info: 患者信息
            
        Yields:
            StreamEvent: 诊断过程事件
        """
        input_data = {
            "messages": [],
            "patient_info": patient_info,
            "start_diagnosis": True,
            "summary_with_dialogue": "",
            "patient_portrait": "",
            "final_report": "",
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
        
        async for event in self.stream(thread_id, input_data):
            yield event


# === 辅助函数 ===

async def print_stream_events(events: AsyncIterator[StreamEvent]):
    """打印流式事件（用于调试）"""
    async for event in events:
        print(f"\n[{event.event.upper()}]")
        if event.event == "messages/partial":
            # 打印AI消息片段
            for msg in event.data:
                if msg.get("type") == "ai" or msg.get("role") == "ai":
                    content = msg.get("content", "")
                    print(content, end="", flush=True)
        elif event.event == "values":
            # 打印重要状态
            data = event.data
            if "start_diagnosis" in data:
                print(f"  start_diagnosis: {data['start_diagnosis']}")
            if "final_report" in data and data["final_report"]:
                print(f"  final_report 长度: {len(data['final_report'])}")
        elif event.event == "end":
            print("\n[PASS] 运行完成")


# === 使用示例 ===

async def example_basic():
    """基础使用示例"""
    async with DeepRareAgentClient() as client:
        # 1. 获取服务信息
        info = await client.get_info()
        print(f"服务版本: {info.get('version')}")
        print(f"可用图: {info.get('graphs')}")
        
        # 2. 创建会话
        thread_id = await client.create_thread(
            metadata={"user": "demo", "session": "example"}
        )
        print(f"\n会话ID: {thread_id}")
        
        # 3. 发送消息
        print("\n发送消息: 医生你好，我头痛3天了")
        events = await client.send_message(
            thread_id,
            "医生你好，我25岁男性，头痛3天，搏动性疼痛8/10分，母亲有偏头痛史，请帮我诊断"
        )
        
        await print_stream_events(events)
        
        # 4. 获取最终状态
        state = await client.get_state(thread_id)
        print(f"\n最终状态:")
        print(f"  - 消息数: {len(state['values'].get('messages', []))}")
        print(f"  - 诊断完成: {state['values'].get('start_diagnosis', False)}")
        if state['values'].get('final_report'):
            print(f"  - 最终报告: {state['values']['final_report'][:200]}...")


async def example_direct_diagnosis():
    """直接诊断示例（跳过预诊断）"""
    async with DeepRareAgentClient() as client:
        thread_id = await client.create_thread()
        print(f"会话ID: {thread_id}")
        
        # 准备患者信息
        patient_info = {
            "base_info": {"age": 25, "gender": "男"},
            "symptoms": [
                {
                    "name": "头痛",
                    "duration": "3天",
                    "type": "搏动性",
                    "severity": "8/10"
                }
            ],
            "vitals": [],
            "exams": [],
            "medications": [],
            "family_history": [{"condition": "偏头痛"}],
            "others": []
        }
        
        print("\n开始深度诊断...")
        events = await client.start_diagnosis(thread_id, patient_info)
        await print_stream_events(events)
        
        # 获取最终报告
        state = await client.get_state(thread_id)
        final_report = state['values'].get('final_report', '')
        print(f"\n最终诊断报告:\n{final_report}")


async def example_continue_conversation():
    """多轮对话示例"""
    async with DeepRareAgentClient() as client:
        thread_id = await client.create_thread()
        
        # 第一轮
        print("用户: 医生你好，我头痛")
        events = await client.send_message(thread_id, "医生你好，我头痛")
        await print_stream_events(events)
        
        # 第二轮
        print("\n用户: 我25岁，男性")
        events = await client.send_message(thread_id, "我25岁，男性")
        await print_stream_events(events)
        
        # 第三轮
        print("\n用户: 持续3天了，搏动性疼痛")
        events = await client.send_message(
            thread_id,
            "持续3天了，搏动性疼痛，程度8/10分"
        )
        await print_stream_events(events)
        
        # 触发诊断
        print("\n用户: 请帮我诊断")
        events = await client.send_message(thread_id, "请帮我深度诊断")
        await print_stream_events(events)


if __name__ == "__main__":
    # 运行示例（选择一个）
    print("=" * 80)
    print("DeepRareAgent API 客户端示例")
    print("=" * 80)
    
    # asyncio.run(example_basic())
    # asyncio.run(example_direct_diagnosis())
    asyncio.run(example_continue_conversation())
