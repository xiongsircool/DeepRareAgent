"""
专家组深度导出节点构建器 (P02 MDT)
- 负责根据配置动态生成单个专家的诊断节点
- 支持自定义工具集、子智能体级联以及状态注入
"""
import warnings
from pathlib import Path
from typing import Annotated,Any, List, Dict, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from deepagents import SubAgent, create_deep_agent
from langchain.agents.middleware import AgentMiddleware, hook_config, wrap_tool_call
from langchain_core.runnables import RunnableConfig
from typing_extensions import TypedDict
import operator
from langchain.agents.middleware import AgentState, AgentMiddleware


# 1. 核心导入
from DeepRareAgent.config import settings
from DeepRareAgent.tools import get_all_tools, get_all_tools_with_biomcp_sync, default_TOOL_EXCLUDE_LIST
from DeepRareAgent.tools.patientinfo import patient_info_to_text
from DeepRareAgent.utils.model_factory import create_llm_from_config

warnings.filterwarnings("ignore", category=UserWarning, module="langchain")

def _format_tool_descriptions(tools: List[Any]) -> str:
    """自动提取工具信息，供主智能体任务规划使用"""
    lines = []
    for t in tools:
        name = getattr(t, "name", "未知工具")
        desc = getattr(t, "description", "暂无描述")
        lines.append(f"- {name}: {desc}")
    return "\n".join(lines)

def _load_prompt_file(path_str: str) -> str:
    """加载提示词文本，支持配置中的绝对路径"""
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"未找到提示词文件: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def create_deep_export_node(
    custom_settings: Any = None
):
    """
    深度诊断导出节点工厂。
    - 允许外部注入自定义 settings 或模型。
    - 内部自动完成 Main/Sub Agent 的级联构建。
    """
    if custom_settings is None:
        raise ValueError("create_deep_export_node 需要传入有效的 custom_settings")

    active_settings = custom_settings
    
    # 2.2 使用 main_agent 参数来初始化主模型
    llm_main = create_llm_from_config(active_settings.main_agent)
    llm_main.profile = {
        "max_input_tokens": getattr(active_settings, "max_input_tokens", 80000)
    }

    # 2.7 构建工具错误处理中间件（支持异步）
    class ToolErrorHandlerMiddleware(AgentMiddleware):
        """
        工具错误处理中间件，支持同步和异步调用。
        捕获工具执行错误，返回友好的错误消息给模型而不是中断执行。
        这样模型可以：
        1. 调整参数重试同一工具
        2. 尝试使用其他工具
        3. 向用户报告问题并继续诊断流程
        """

        def wrap_tool_call(self, request, handler):
            """同步版本的工具调用处理"""
            tool_name = request.tool_call.get("name", "未知工具")
            try:
                return handler(request)
            except Exception as e:
                error_msg = self._format_error_message(tool_name, e)
                print(f"[工具错误] 同步: {tool_name} - {str(e)}")
                return ToolMessage(
                    content=error_msg,
                    tool_call_id=request.tool_call["id"]
                )

        async def awrap_tool_call(self, request, handler):
            """异步版本的工具调用处理"""
            tool_name = request.tool_call.get("name", "未知工具")
            try:
                return await handler(request)
            except Exception as e:
                error_msg = self._format_error_message(tool_name, e)
                print(f"[工具错误] 异步: {tool_name} - {str(e)}")
                return ToolMessage(
                    content=error_msg,
                    tool_call_id=request.tool_call["id"]
                )

        def _format_error_message(self, tool_name: str, error: Exception) -> str:
            """格式化错误消息"""
            return (
                f"SYSTEM_NOTIFICATION: Tool '{tool_name}' failed to execute.\n"
                f"Error Type: {type(error).__name__}\n"
                f"Error Details: {str(error)}\n\n"
                f"GUIDANCE FOR AGENT:\n"
                f"1. Do NOT blindly retry the same operation if it persists in failing.\n"
                f"2. If acceptable, SKIP this specific step or use an ALTERNATIVE tool.\n"
                f"3. If the information is critical but verifying it is impossible, note this limitation in your final report and PROCEED with other analyses.\n"
                f"4. Your priority is to complete the overall diagnostic assessment, even with partial information."
            )
    # 构建
    class Context(AgentState):
        evidences: Annotated[list[str], operator.add]
    class ContextMiddleware(AgentMiddleware):
        """扩展 State 的 Middleware"""
        state_schema = Context
    # 2.3 使用 sub_agent 参数来初始化子模型(关于子智能体默认工具排除可以使用create_deep_agent 中)
    def build_sub_agent(sub_id: str, sub_cfg: Any) -> SubAgent:
        selected_tools = []
        for t_name in getattr(sub_cfg, "additional_tools", []):
            if not t_name: continue # Skip empty strings
            if t_name in default_TOOL_EXCLUDE_LIST:
                # pass
                selected_tools.append(default_TOOL_EXCLUDE_LIST[t_name])
                pass
            else:
                raise ValueError(f"Unsupported tool to add: {t_name}")
        system_prompt = _load_prompt_file(sub_cfg.system_prompt_path)
        # 将工具介绍添加到系统提示词中
        system_prompt = system_prompt.format(
            tool_Introduction_list=_format_tool_descriptions(selected_tools)
        )
        
        llm_sub = create_llm_from_config(sub_cfg)

        sub_agent = SubAgent(
            name=sub_id,
            description=getattr(sub_cfg, "description", "负责具体文献检索、表型分析与数据抓取的助理。"),
            system_prompt=system_prompt,
            tools=selected_tools, 
            model=llm_sub,
            middleware=[ToolErrorHandlerMiddleware(), ContextMiddleware()],
        )
        return sub_agent

    subagents = []
    if hasattr(active_settings, "sub_agent") and active_settings.sub_agent:
        for sub_id, sub_cfg in vars(active_settings.sub_agent).items():
            subagents.append(build_sub_agent(sub_id, sub_cfg))

    # 2.4 处理 Main Agent 的工具排除和添加
    exculede_tools = []
    for t_name in getattr(active_settings.main_agent, "excoulde_tools", []):
        if not t_name: continue
        if t_name in ["write_todos", "ls", "read_file", "write_file", "edit_file", "glob", "grep", "execute", "task"]:
            exculede_tools.append(t_name)
        else:
            raise ValueError(f"Unsupported tool to exclude: {t_name}")
            
    # 2.5 处理 Main Agent 的工具添加
    selected_tools = []
    for i in getattr(active_settings.main_agent, "additional_tools", []):
        if not i: continue
        if i in default_TOOL_EXCLUDE_LIST:
            selected_tools.append(default_TOOL_EXCLUDE_LIST[i])
        else:
            raise ValueError(f"Unsupported tool to add: {i}")

    #TODO:因为我感觉默认的几个工具对于子智能体还需要移除所以先不移除。后面再移除，外部还要增加参数
    # sub_exculede_tools = ["write_file", "edit_file"]
    sub_exculede_tools = []


    # 2.6 加载并注入提示词
    full_main_prompt = _load_prompt_file(active_settings.main_agent.system_prompt_path)
    full_main_prompt = full_main_prompt.format(
        tool_Introduction_list=_format_tool_descriptions(selected_tools)
    )

    # 2.8 构建 Agent 架构
    # NOTE:create_deep_agent 并不直接提供像 create_agent 那样的 schema 或 state_schema 参数，改用context_schema来存储evidences先从expert_state中获取再最后时候更新expert_state去更新MDTGraphState中的evidences
    deep_agent_executor = create_deep_agent(
        name=active_settings.main_agent.name,
        model=llm_main,
        tools=selected_tools,
        # exclude_tools=exculede_tools,
        # subagent_exclude_tools=sub_exculede_tools,
        subagents=subagents,
        system_prompt=full_main_prompt,
        middleware=[ToolErrorHandlerMiddleware(), ContextMiddleware()],  # 启用工具错误处理中间件（支持异步）
        debug=False
    )

    # 2.8 定义异步节点
    async def deep_export_node(state: Dict[str, Any], config: RunnableConfig) -> Dict[str, Any]:
        """导出专家组 LangGraph 异步节点"""
        # 当前处理的节点名字来从MDTGraphState中获取当前专家的ExpertGroupState
        group_id = config.get("metadata", {}).get("langgraph_node") #获取专家节点信息
        expert_state = state.get("expert_pool", {}).get(group_id, {})
        if not expert_state:
            # Fallback or initialization if not present, though really should be error or empty
            print(f"[{group_id}] Warning: No expert state found in pool.")
            # expert_state = {}
            # Allow fallback to generic state if needed, or just proceed expecting keys might be missing

        # 优化：如果该专家已经满意，跳过诊断，直接返回
        if expert_state.get("is_satisfied", False):
            print(f"[{group_id}] Expert already satisfied, skipping diagnosis.")
            return {}  # 返回空字典，不更新状态

        # NOTE:专家的聊天记录
        messages = expert_state.get("messages", [])
        evidences = expert_state.get("evidences", [])
        
        agent_name = active_settings.main_agent.name

        try:
            print(f">>> [{agent_name}] Starting deep agent execution...")
            response = await deep_agent_executor.ainvoke({
                "messages": messages,
                "evidences": evidences
            })

            all_msgs = response.get("messages", [])
            response_evidences = response.get("evidences", [])
            
            # TODO: Should we update expert_state  to MDTGraphState ?
            # 通常 LangGraph 节点返回一个字典来更新状态。
            # 由于 schema 中 messages 移除了 add_messages reducer，且 expert_pool 使用替换逻辑 (ior)，
            # 必须显式继承旧状态并在 messages 列表末尾追加新消息，以防止状态丢失。
            
            # 1. 成功分支：继承原有状态并更新差异字段
            report = all_msgs[-1].content
            update_export_state = expert_state.copy()  # 关键：继承原始状态（如 group_id, times_deep_diagnosis 等）
            update_export_state.update({
                "messages": messages + [all_msgs[-1]], # 关键修正：追加最新回复到历史记录
                "evidences": response_evidences,  # 使用 response 中的 evidences，而不是输入的 evidences
                "has_error": False,
                "report": report,
                "times_deep_diagnosis": expert_state.get("times_deep_diagnosis", 0) + 1
            })
            
            update_mdt_state = {
                "expert_pool": {
                    group_id: update_export_state
                }
            }
            return update_mdt_state

        except Exception as e:
            print(f"[错误] {agent_name} 执行出错: {e}")

            # 2. 异常分支：同样继承状态，仅标记错误
            update_export_state = expert_state.copy()
            update_export_state.update({
                "messages": messages, # 保持对话历史不变
                "has_error": True,
                "report": f"执行异常: {str(e)}", # 最好把错误信息也记录到 report 以便调试或后续处理
                "times_deep_diagnosis": expert_state.get("times_deep_diagnosis", 0) + 1
            })

            # 添加错误消息到主图，让用户知道出错了
            error_message = f"⚠️ 专家组 {group_id} 执行出错"
            # 如果错误信息不太长，也显示给用户
            if len(str(e)) < 100:
                error_message += f": {str(e)}"

            update_mdt_state = {
                "expert_pool": {
                    group_id: update_export_state
                },
                "messages": [AIMessage(content=error_message)]
            }
            return update_mdt_state
            
    return deep_export_node


if __name__ == "__main__":
    import asyncio
    import pprint
    from langchain_core.messages import HumanMessage
    
    async def test_single_expert_node():
        print("=== Testing Single Expert Node (Deep Export Node) ===")
        
        # 1. Pick a group config from settings
        # We'll use group_1
        if not hasattr(settings, "multi_expert_diagnosis_agent"):
            print("Error: multi_expert_diagnosis_agent setting not found.")
            return

        group_1_config = settings.multi_expert_diagnosis_agent.group_1
        print(f"Using config for: {group_1_config.main_agent.name}")

        try:
            # 2. Create the node
            node_func = create_deep_export_node(custom_settings=group_1_config)
            print("Node created successfully.")
            
            # 3. Create mock state
            # Simulate what the graph would pass: a state with 'expert_pool' populated for this group
            mock_group_id = "group_1"
            mock_state = {
                "expert_pool": {
                    mock_group_id: {
                        "messages": [
                            HumanMessage(content="Analyzing patient with symptoms: periodic pain in extremities, hypohidrosis, angiokeratomas. Family history of kidney failure. Suspect Fabry disease.")
                        ],
                        "evidences": []
                    }
                }
            }
            
            mock_config = {"metadata": {"langgraph_node": mock_group_id}}
            
            # 4. Run the node
            print("\n>>> Invoking Node...")
            result = await node_func(mock_state, mock_config)
            
            print("\n>>> Execution Result:")
            # pprint.pprint(result)
            
            # 适配新的返回值结构验证
            if "expert_pool" in result and mock_group_id in result["expert_pool"]:
                updated_state = result["expert_pool"][mock_group_id]
                
                print("\n" + "="*50)
                print(" FINAL REPORT ")
                print("="*50)
                print(updated_state.get("report", "No Report"))
                
                print("\n" + "="*50)
                print(" FINAL EVIDENCES ")
                print("="*50)
                pprint.pprint(updated_state.get("evidences", []))
            else:
                print("\nError: Return value structure does not match expected MDTGraphState update.")

        except Exception as e:
            print(f"\n[测试失败] 错误信息:")
            import traceback
            traceback.print_exc()

    asyncio.run(test_single_expert_node())
