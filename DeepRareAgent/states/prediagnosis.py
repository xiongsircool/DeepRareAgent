from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from typing import Annotated, List, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage, ToolMessage

class PreDiagnosisState(TypedDict):
    # add_messages: 自动处理消息的追加历史
    messages: Annotated[List[BaseMessage], add_messages]
    
    # patient_info: 患者信息管理
    patient_info: Dict[str, Any]
    start_diagnosis:bool