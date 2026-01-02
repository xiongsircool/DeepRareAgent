# LangGraph 项目模板

这是一个基于 LangGraph 的空白项目模板，支持生成式 UI。

## 🚀 快速开始

### 1. 环境要求

- Python 3.11+
- Node.js (可选，用于 UI 组件开发)

### 2. 安装依赖

```bash
# 安装 Python 依赖
pip install -e . "langgraph-cli[inmem]"
```

### 3. 配置环境变量（可选）

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件添加你的 API 密钥
```

### 4. 启动开发服务器

```bash
# 启动 LangGraph 开发服务器
langgraph dev
```

服务器将在以下地址启动：
- 🚀 **API**: http://127.0.0.1:2024
- 🎨 **Studio UI**: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- 📚 **API 文档**: http://127.0.0.1:2024/docs

## 📁 项目结构

```
multi_agent/
├── src/
│   ├── __init__.py
│   └── agent/
│       ├── __init__.py
│       └── graph.py      # 你的图定义在这里
├── pyproject.toml        # Python 项目配置
├── langgraph.json         # LangGraph 配置
├── .env.example          # 环境变量模板
└── README.md             # 项目说明
```

## 🔧 自定义你的智能体

### 1. 修改图定义

在 `src/agent/graph.py` 中定义你的智能体逻辑：

```python
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import StateGraph
from typing_extensions import TypedDict

class State(TypedDict):
    messages: list[HumanMessage | AIMessage]
    # 添加你的状态字段

def your_node(state: State) -> Dict:
    # 实现你的节点逻辑
    return {
        "messages": [AIMessage(content="Hello!")]
    }

# 构建图
graph = (
    StateGraph(State)
    .add_node("your_node", your_node)
    .add_edge("__start__", "your_node")
    .compile(name="your_agent")
)
```

### 2. 添加生成式 UI 组件（可选）

1. 创建 UI 组件文件 `src/agent/ui.tsx`
2. 在 `langgraph.json` 中添加 UI 配置
3. 在节点中使用 `push_ui_message` 发送 UI 组件

### 3. 更新配置

修改 `langgraph.json` 以匹配你的图结构：

```json
{
  "$schema": "https://langgra.ph/schema.json",
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/agent/graph.py:graph"
  },
  "ui": {
    "agent": "./src/agent/ui.tsx"  // 可选
  },
  "env": ".env.example",
  "python_version": "3.12"
}
```

## 🎨 生成式 UI 支持

这个模板支持 LangGraph 的生成式 UI 功能，允许你：

- 在后端定义 React 组件
- 动态生成用户界面
- 无需前端代码即可创建交互式应用

更多详情请参考 [LangGraph 生成式 UI 文档](https://langchain-ai.github.io/langgraph/how-tos/generative_ui/)。

## 📚 相关资源

- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph API 参考](https://api.langchain.com/)
- [LangSmith](https://smith.langchain.com/) - 用于调试和监控

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件