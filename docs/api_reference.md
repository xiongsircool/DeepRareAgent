# LangGraph API 接口文档

## 服务信息

当运行 `uv run langgraph dev` 时，会启动一个本地 HTTP 服务器：

- **默认地址**: `http://localhost:2024`
- **Graph ID**: `agent` (来自 `langgraph.json` 的配置)
- **API 版本**: LangGraph API v0.6.x

## API 端点总览

### 基础 URL
```
http://localhost:2024
```

### 主要端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/info` | 获取服务信息 |
| GET | `/assistants/search` | 搜索可用的助手 |
| POST | `/threads` | 创建新会话 |
| GET | `/threads/{thread_id}` | 获取会话信息 |
| POST | `/threads/{thread_id}/runs` | 创建新的运行 |
| POST | `/threads/{thread_id}/runs/stream` | 流式运行（推荐） |
| GET | `/threads/{thread_id}/state` | 获取当前状态 |
| GET | `/threads/{thread_id}/history` | 获取历史记录 |

---

## 详细 API 说明

### 1. 获取服务信息

```bash
curl http://localhost:2024/info
```

**响应示例**：
```json
{
  "version": "0.6.15",
  "graphs": ["agent"]
}
```

---

### 2. 创建会话（Thread）

```bash
curl -X POST http://localhost:2024/threads \
  -H "Content-Type: application/json" \
  -d '{}'
```

**响应示例**：
```json
{
  "thread_id": "abc123-def456-...",
  "created_at": "2026-01-06T12:00:00Z",
  "metadata": {}
}
```

---

### 3. 运行 Graph（流式，推荐）⭐

这是最常用的接口，用于实际执行诊断流程。

#### 请求格式

```bash
curl -X POST http://localhost:2024/threads/{thread_id}/runs/stream \
  -H "Content-Type: application/json" \
  -d @request.json
```

**request.json**:
```json
{
  "assistant_id": "agent",
  "input": {
    "messages": [
      {
        "role": "human",
        "content": "医生你好，我头痛3天了"
      }
    ]
  },
  "stream_mode": ["values", "messages"],
  "config": {
    "configurable": {}
  }
}
```

#### 完整输入状态示例

```json
{
  "assistant_id": "agent",
  "input": {
    "messages": [
      {
        "role": "human",
        "content": "医生你好，我25岁男性，头痛3天，搏动性疼痛8/10分，母亲有偏头痛史"
      }
    ],
    "patient_info": {
      "base_info": {},
      "symptoms": [],
      "vitals": [],
      "exams": [],
      "medications": [],
      "family_history": [],
      "others": []
    },
    "start_diagnosis": false,
    "summary_with_dialogue": "",
    "patient_portrait": "",
    "final_report": "",
    "expert_pool": {},
    "blackboard": {
      "published_reports": {},
      "conflicts": {},
      "common_understandings": {}
    },
    "consensus_reached": false,
    "round_count": 0,
    "max_rounds": 3
  },
  "stream_mode": ["values", "messages", "updates"],
  "config": {
    "configurable": {
      "thread_id": "user-123"
    }
  }
}
```

#### 响应格式（Server-Sent Events）

响应是一个流式的 SSE (Server-Sent Events) 格式：

```
event: metadata
data: {"run_id": "019b932e-..."}

event: values
data: {
  "messages": [...],
  "patient_info": {...},
  ...
}

event: messages/partial
data: [{
  "role": "ai",
  "content": "您好，我是..."
}]

event: values
data: {
  "messages": [...],
  "start_diagnosis": true,
  "summary_with_dialogue": "患者25岁男性...",
  ...
}

event: end
data: null
```

**事件类型说明**：

| 事件 | 描述 |
|------|------|
| `metadata` | 运行元数据（run_id等） |
| `values` | 完整的图状态 |
| `messages/partial` | 流式消息片段 |
| `messages/complete` | 完整消息 |
| `updates` | 状态更新 |
| `end` | 运行结束 |

---

### 4. 运行 Graph（非流式）

```bash
curl -X POST http://localhost:2024/threads/{thread_id}/runs \
  -H "Content-Type: application/json" \
  -d '{
    "assistant_id": "agent",
    "input": {
      "messages": [{"role": "human", "content": "你好"}]
    }
  }'
```

**响应示例**：
```json
{
  "run_id": "019b932e-...",
  "status": "success",
  "output": {
    "messages": [...],
    "patient_info": {...},
    "final_report": "...",
    ...
  }
}
```

---

### 5. 获取当前状态

```bash
curl http://localhost:2024/threads/{thread_id}/state
```

**响应示例**：
```json
{
  "values": {
    "messages": [
      {
        "type": "human",
        "content": "医生你好"
      },
      {
        "type": "ai",
        "content": "您好，请问..."
      }
    ],
    "patient_info": {
      "base_info": {"age": 25, "gender": "男"},
      "symptoms": [...]
    },
    "start_diagnosis": true,
    "summary_with_dialogue": "患者25岁...",
    "final_report": "..."
  },
  "next": [],
  "config": {...},
  "metadata": {...}
}
```

---

### 6. 获取历史记录

```bash
curl http://localhost:2024/threads/{thread_id}/history
```

**响应示例**：
```json
{
  "values": [
    {
      "checkpoint_id": "1",
      "values": {...},
      "next": ["prediagnosis"]
    },
    {
      "checkpoint_id": "2",
      "values": {...},
      "next": ["prepare_mdt"]
    }
  ]
}
```

---

## 状态结构详解

### MainGraphState 完整结构

```typescript
interface MainGraphState {
  // === 消息历史 ===
  messages: Message[];  // 对话消息列表
  
  // === 控制字段 ===
  start_diagnosis: boolean;  // 是否开始深度诊断
  
  // === 患者信息 ===
  patient_info: {
    base_info: Record<string, any>;      // 基础信息（年龄、性别等）
    symptoms: Array<any>;                // 症状列表
    vitals: Array<any>;                  // 生命体征
    exams: Array<any>;                   // 检查结果
    medications: Array<any>;             // 用药史
    family_history: Array<any>;          // 家族史
    others: Array<any>;                  // 其他信息
  };
  
  summary_with_dialogue: string;         // 对话总结
  patient_portrait: string;              // 患者画像
  
  // === MDT 相关 ===
  expert_pool: Record<string, ExpertGroupState>;  // 专家组状态
  blackboard: {
    published_reports: Record<string, string>;    // 已发布报告
    conflicts: Record<string, string>;            // 冲突点
    common_understandings: Record<string, string>; // 共识
  };
  
  consensus_reached: boolean;            // 是否达成共识
  round_count: number;                   // 当前轮数
  max_rounds: number;                    // 最大轮数
  
  // === 输出 ===
  final_report: string;                  // 最终诊断报告
}
```

### Message 格式

```typescript
interface Message {
  role: "human" | "ai" | "system" | "tool";
  content: string;
  name?: string;
  tool_calls?: Array<{
    name: string;
    args: Record<string, any>;
    id: string;
  }>;
}
```

---

## 实际使用示例

### Python 客户端示例

```python
import httpx
import json

BASE_URL = "http://localhost:2024"

async def run_diagnosis(user_message: str):
    """运行诊断流程"""
    
    async with httpx.AsyncClient() as client:
        # 1. 创建会话
        thread_resp = await client.post(f"{BASE_URL}/threads")
        thread_id = thread_resp.json()["thread_id"]
        print(f"创建会话: {thread_id}")
        
        # 2. 发送消息并流式接收
        async with client.stream(
            "POST",
            f"{BASE_URL}/threads/{thread_id}/runs/stream",
            json={
                "assistant_id": "agent",
                "input": {
                    "messages": [{"role": "human", "content": user_message}]
                },
                "stream_mode": ["values", "messages"]
            },
            timeout=300.0  # 5分钟超时
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]  # 移除 "data: " 前缀
                    if data and data != "[DONE]":
                        try:
                            event_data = json.loads(data)
                            print(f"收到事件: {event_data}")
                        except json.JSONDecodeError:
                            pass
        
        # 3. 获取最终状态
        state_resp = await client.get(f"{BASE_URL}/threads/{thread_id}/state")
        final_state = state_resp.json()
        
        return final_state

# 使用
import asyncio
result = asyncio.run(run_diagnosis("我头痛3天了"))
print("最终报告:", result["values"]["final_report"])
```

### JavaScript/TypeScript 示例

```typescript
const BASE_URL = "http://localhost:2024";

async function runDiagnosis(userMessage: string) {
  // 1. 创建会话
  const threadResp = await fetch(`${BASE_URL}/threads`, {
    method: "POST",
  });
  const { thread_id } = await threadResp.json();
  
  // 2. 流式运行
  const response = await fetch(
    `${BASE_URL}/threads/${thread_id}/runs/stream`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        assistant_id: "agent",
        input: {
          messages: [{ role: "human", content: userMessage }],
        },
        stream_mode: ["values", "messages"],
      }),
    }
  );
  
  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split("\n");
    
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (data && data !== "[DONE]") {
          try {
            const event = JSON.parse(data);
            console.log("Event:", event);
          } catch {}
        }
      }
    }
  }
  
  // 3. 获取最终状态
  const stateResp = await fetch(`${BASE_URL}/threads/${thread_id}/state`);
  const finalState = await stateResp.json();
  
  return finalState;
}
```

---

## 高级功能

### 1. 中断和恢复

```python
# 运行到某个节点后暂停
await client.post(
    f"{BASE_URL}/threads/{thread_id}/runs",
    json={
        "assistant_id": "agent",
        "input": {...},
        "config": {
            "configurable": {
                "interrupt_before": ["mdt_diagnosis"]  # 在MDT前暂停
            }
        }
    }
)

# 恢复执行
await client.post(
    f"{BASE_URL}/threads/{thread_id}/runs",
    json={
        "assistant_id": "agent",
        "input": None,  # 使用保存的状态
    }
)
```

### 2. 手动更新状态

```bash
curl -X POST http://localhost:2024/threads/{thread_id}/state \
  -H "Content-Type: application/json" \
  -d '{
    "values": {
      "patient_info": {
        "base_info": {"age": 30, "gender": "男"}
      }
    }
  }'
```

### 3. 获取特定 checkpoint

```bash
curl http://localhost:2024/threads/{thread_id}/state/{checkpoint_id}
```

---

## 错误处理

### 常见错误响应

```json
{
  "error": {
    "type": "validation_error",
    "message": "Invalid input format",
    "details": {...}
  }
}
```

### 错误类型

| 错误类型 | HTTP状态码 | 描述 |
|---------|-----------|------|
| `validation_error` | 400 | 输入验证失败 |
| `not_found` | 404 | 会话或运行不存在 |
| `runtime_error` | 500 | 图执行错误 |
| `timeout` | 504 | 执行超时 |

---

## 性能优化建议

1. **使用流式模式** - 减少等待时间，实时获取反馈
2. **合理设置超时** - 诊断流程可能需要数分钟
3. **缓存 thread_id** - 同一用户可复用会话
4. **异步处理** - 使用异步客户端提高并发

---

## 调试技巧

### 查看详细日志

```bash
# 启动时启用详细日志
LANGCHAIN_TRACING_V2=true \
LANGCHAIN_API_KEY=your-key \
uv run langgraph dev
```

### 使用 LangGraph Studio

启动后访问：
```
http://localhost:2024
```

可以在浏览器中可视化调试图的执行过程。

---

## 下一步

- 📖 查看 `examples/` 目录中的完整示例
- [TOOL] 根据您的需求调整 stream_mode
- 🚀 集成到您的前端应用
