from typing import Any, Dict


def format_message_for_display(message) -> str:
    """
    将单个消息对象转换为可读文本格式。
    处理不同的消息类型。
    """
    message_type = type(message).__name__  # HumanMessage, AIMessage 等
    content = message.content
    
    if isinstance(content, str):
        return f"[{message_type}] {content}"
    else:
        # 处理复杂内容（如包含工具调用的消息）
        return f"[{message_type}] {str(content)}"


def parse_and_display_messages(state: Dict[str, Any]) -> str:
    """
    提取和格式化 messages，返回完整的对话历史文本。
    """
    messages = state.get("messages", [])
    
    if not messages:
        return "没有消息记录"
    
    formatted_output = []
    formatted_output.append("=" * 60)
    formatted_output.append(f"📋 对话历史 (共 {len(messages)} 条消息)")
    formatted_output.append("=" * 60)
    
    for index, message in enumerate(messages, 1):
        # 获取消息类型和内容
        message_type = type(message).__name__
        content = message.content["text"] if isinstance(message.content, Dict) and "text" in message.content else message.content 
        if isinstance(message.content, list) and any(isinstance(item, Dict) and "text" in item for item in message.content):
            content = "\n".join(
                item["text"] for item in message.content if isinstance(item, Dict) and "text" in item
            )
        
        # 为不同类型的消息添加符号
        icon = "👤" if message_type == "HumanMessage" else "🤖"
        icon = "⚙️" if message_type == "SystemMessage" else icon
        icon = "🔧" if message_type == "ToolMessage" else icon
        
        formatted_output.append(f"\n{icon} 消息 #{index} [{message_type}]")
        formatted_output.append("-" * 40)
        
        if isinstance(content, str):
            formatted_output.append(content)
        else:
            # 处理复杂内容结构
            formatted_output.append(str(content))
        
        # 添加消息的额外属性（如果有）
        if hasattr(message, "tool_calls") and message.tool_calls:
            formatted_output.append(f"  └─ 工具调用: {message.tool_calls}")
    
    formatted_output.append("\n" + "=" * 60)
    return "\n".join(formatted_output)