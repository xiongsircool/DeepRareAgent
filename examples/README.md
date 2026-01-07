# DeepRareAgent API 示例

本目录包含使用 DeepRareAgent API 的各种示例代码。

## [LIST] 文件说明

| 文件 | 说明 | 难度 |
|------|------|------|
| `api_client.py` | 完整的 Python 客户端封装 | ⭐⭐⭐ |
| `quick_test_api.py` | 快速测试脚本 | ⭐ |
| `web_demo.html` | Web 前端示例 | ⭐⭐ |

## 🚀 快速开始

### 1. 启动 LangGraph 服务

首先确保服务正在运行：

```bash
cd /path/to/DeepRareAgent
uv run langgraph dev
```

服务将在 `http://localhost:2024` 启动。

### 2. 运行快速测试

验证 API 连接和基本功能：

```bash
python examples/quick_test_api.py
```

这将测试：
- [PASS] 服务连接
- [PASS] 创建会话
- [PASS] 发送消息
- [PASS] 状态查询
- [TIME] 完整诊断流程（可选）

### 3. 使用 Python 客户端

```python
from examples.api_client import DeepRareAgentClient

async def example():
    async with DeepRareAgentClient() as client:
        # 创建会话
        thread_id = await client.create_thread()
        
        # 发送消息
        events = await client.send_message(
            thread_id,
            "我头痛3天了，25岁男性"
        )
        
        # 处理流式响应
        async for event in events:
            if event.event == "messages/partial":
                print(event.data)

import asyncio
asyncio.run(example())
```

### 4. 使用 Web 界面

直接在浏览器中打开：

```bash
open examples/web_demo.html
```

或者通过 HTTP 服务器（推荐）：

```bash
python -m http.server 8000 --directory examples
# 然后访问 http://localhost:8000/web_demo.html
```

## 📚 详细示例

### 示例 1: 基础对话

```python
from examples.api_client import DeepRareAgentClient, print_stream_events

async def basic_chat():
    async with DeepRareAgentClient() as client:
        thread_id = await client.create_thread()
        
        # 发送消息并打印事件
        events = await client.send_message(thread_id, "医生你好")
        await print_stream_events(events)
        
        # 获取最终状态
        state = await client.get_state(thread_id)
        print(state["values"])
```

### 示例 2: 直接诊断

跳过预诊断，直接开始深度诊断：

```python
async def direct_diagnosis():
    async with DeepRareAgentClient() as client:
        thread_id = await client.create_thread()
        
        # 准备患者信息
        patient_info = {
            "base_info": {"age": 25, "gender": "男"},
            "symptoms": [
                {"name": "头痛", "duration": "3天", "severity": "8/10"}
            ],
            "family_history": [{"condition": "偏头痛"}],
            # ... 其他字段
        }
        
        # 开始诊断
        events = await client.start_diagnosis(thread_id, patient_info)
        
        # 监听诊断过程
        async for event in events:
            if event.event == "values":
                if event.data.get("final_report"):
                    print("诊断完成!")
                    print(event.data["final_report"])
```

### 示例 3: 多轮对话

```python
async def multi_turn_conversation():
    async with DeepRareAgentClient() as client:
        thread_id = await client.create_thread()
        
        messages = [
            "医生你好",
            "我头痛3天了",
            "我25岁，男性",
            "搏动性疼痛，8/10分",
            "我妈妈有偏头痛",
            "请帮我诊断"
        ]
        
        for msg in messages:
            print(f"用户: {msg}")
            events = await client.send_message(thread_id, msg)
            
            # 打印AI回复
            async for event in events:
                if event.event == "messages/partial":
                    for m in event.data:
                        if m.get("type") == "ai":
                            print(f"AI: {m.get('content')}")
```

### 示例 4: 监控诊断进度

```python
async def monitor_diagnosis():
    async with DeepRareAgentClient() as client:
        thread_id = await client.create_thread()
        
        events = await client.send_message(
            thread_id,
            "我25岁男性，头痛3天，搏动性8/10分，母亲偏头痛，请深度诊断"
        )
        
        async for event in events:
            if event.event == "values":
                data = event.data
                
                # 检测诊断开始
                if data.get("start_diagnosis"):
                    print("[LAB] 深度诊断已启动")
                
                # 检测对话总结
                if data.get("summary_with_dialogue"):
                    print(f"[NOTE] 对话总结已生成")
                
                # 检测专家组状态
                if data.get("expert_pool"):
                    pool = data["expert_pool"]
                    print(f"👥 {len(pool)} 个专家组正在分析")
                
                # 检测共识
                if data.get("consensus_reached"):
                    print("[PASS] 专家达成共识")
                
                # 检测最终报告
                if data.get("final_report"):
                    print("[LIST] 最终报告已生成")
                    print(data["final_report"])
```

## [TOOL] API 端点速查

### 基础操作

```python
# 获取服务信息
info = await client.get_info()

# 创建会话
thread_id = await client.create_thread(metadata={...})

# 获取当前状态
state = await client.get_state(thread_id)

# 获取历史记录
history = await client.get_history(thread_id)
```

### 运行操作

```python
# 同步运行（等待完成）
result = await client.run(thread_id, input_data)

# 流式运行（实时获取）
events = await client.stream(thread_id, input_data)
async for event in events:
    print(event)

# 简化的消息发送
events = await client.send_message(thread_id, "你好")
```

## [INFO] 状态结构

### 主图状态 (MainGraphState)

```python
{
    # 对话消息
    "messages": [...],
    
    # 控制字段
    "start_diagnosis": False,
    
    # 患者信息
    "patient_info": {
        "base_info": {...},
        "symptoms": [...],
        "vitals": [...],
        "exams": [...],
        "medications": [...],
        "family_history": [...],
        "others": [...]
    },
    
    # 对话总结和画像
    "summary_with_dialogue": "",
    "patient_portrait": "",
    
    # MDT 相关
    "expert_pool": {...},
    "blackboard": {...},
    "consensus_reached": False,
    "round_count": 0,
    "max_rounds": 3,
    
    # 最终结果
    "final_report": ""
}
```

### 流式事件类型

```python
# metadata - 运行元数据
{
    "run_id": "...",
    ...
}

# values - 完整状态更新
{
    "messages": [...],
    "patient_info": {...},
    ...
}

# messages/partial - 流式消息片段
[
    {
        "type": "ai",
        "content": "..."
    }
]

# end - 运行结束
null
```

## 🎨 Web 示例说明

`web_demo.html` 提供了一个完整的浏览器端实现：

**特性**：
- [DONE] 现代化 UI 设计
- 💬 实时流式对话
- [INFO] 诊断进度显示
- [USER] 患者信息跟踪
- 🔄 状态实时更新

**使用方法**：
1. 确保 LangGraph 服务运行在 `localhost:2024`
2. 在浏览器中打开 `web_demo.html`
3. 开始对话

**注意**：由于浏览器的 CORS 限制，建议通过 HTTP 服务器访问。

## [DEV] 进阶开发

### 自定义客户端

基于 `api_client.py` 创建自己的客户端：

```python
from examples.api_client import DeepRareAgentClient

class MyCustomClient(DeepRareAgentClient):
    async def analyze_symptoms(self, symptoms: List[str]):
        """自定义方法：分析症状"""
        thread_id = await self.create_thread()
        
        # 构造输入
        input_data = {
            "patient_info": {
                "symptoms": [{"name": s} for s in symptoms]
            },
            "start_diagnosis": True
        }
        
        # 运行并返回
        async for event in self.stream(thread_id, input_data):
            if event.data.get("final_report"):
                return event.data["final_report"]
```

### 集成到应用

```python
# FastAPI 示例
from fastapi import FastAPI
from examples.api_client import DeepRareAgentClient

app = FastAPI()
client = DeepRareAgentClient()

@app.post("/diagnose")
async def diagnose(message: str):
    thread_id = await client.create_thread()
    events = await client.send_message(thread_id, message)
    
    # 收集结果
    result = []
    async for event in events:
        if event.event == "values":
            result.append(event.data)
    
    return result[-1]  # 返回最终状态
```

## 📖 更多资源

- **完整 API 文档**: [`../docs/api_reference.md`](../docs/api_reference.md)
- **系统架构**: [`../docs/system_structure.md`](../docs/system_structure.md)
- **问题修复记录**: [`../docs/fix_summary_passing.md`](../docs/fix_summary_passing.md)

## ❓ 常见问题

### Q: 连接被拒绝？
A: 确保 LangGraph 服务正在运行：`uv run langgraph dev`

### Q: 超时错误？
A: 诊断流程可能需要数分钟，增加 timeout 参数：
```python
client = DeepRareAgentClient(timeout=600.0)  # 10分钟
```

### Q: CORS 错误？
A: Web 示例需要通过 HTTP 服务器访问，不能直接打开 HTML 文件。

### Q: 如何调试？
A: 查看 LangGraph 服务的日志输出，或使用 `stream_mode=["debug"]`

## 🤝 贡献

欢迎提交新的示例！请确保：
1. 代码清晰易懂
2. 包含注释说明
3. 测试通过
