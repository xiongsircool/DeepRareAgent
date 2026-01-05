# -*- coding: utf-8 -*-
from langchain_core.messages import BaseMessage
from typing import List, Dict, Optional, Annotated,Any
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
import operator


#----------------------------------定义MDT图的状态----------------------------------
# 定义专家讨论的状体啊情况
#------------------------------------
class ExpertGroupState(TypedDict):
    """单个专家组的私有状态 (Private Workspace)"""
    group_id: str
    # 1. 保留组长的关键聊天messages，用于作为单次诊断的对话延续性（记忆）
    # 使用 add_messages 允许在多轮循环中追加记忆
    messages:List[BaseMessage]
    times_deep_diagnosis: int # 专家组的诊断次数
    report: str            # 本组阶段性或最终研究报告
    evidences: List[str]  # 本组挖掘出的硬核证据链 (与 EvidenceManager 工具链匹配)
    is_satisfied: bool     # 专家组长自评：是否认为结论已闭环 (Silent State 判定)
    reinvestigate_reason: Optional[str] # 如果不满意，是因为发现了什么新疑点或被其他组修正了认知
    has_error: bool # 在任何过程中导致智能体执行错误导致该专家直接转化为结束状态且不参与后续的任何状态更新操作了
    
class SharedBlackboard(TypedDict):
    """跨组可见的公共黑板 (Public Bulletin Board)"""
    # 存储各组已发布的最新版本报告，方便其他组在“辩论节点”一键读取
    published_reports: Dict[str, str]  # group_id -> report_content

    # TODO: 目前整个系统还不支持一个高级讨论模式所以后面两个字段暂时不使用
    # 存储系统在此轮提取的冲突点
    conflicts: Dict[str, str]
    # 跨组达成一致的共识事实
    common_understandings: Dict[str, str]

class MDTGraphState(TypedDict):
    """多专家联合会诊系统全局状态 (Main Graph State)"""
    messages: Annotated[List[BaseMessage], add_messages]  # 对话历史（用于向主图传递进度消息）
    patient_info: Dict[str, Any]
    summary_with_dialogue : str
    patient_portrait: str               # 统一的患者结构化画像 (Structured Portrait)
    expert_pool: Annotated[Dict[str, ExpertGroupState], operator.ior] # 专家组档案袋 (含私有记忆)
    blackboard: SharedBlackboard        # 公共黑板 (辩论与同步核心)

    round_count: int                    # 当前博弈轮数
    max_rounds: int                     # 最大限制轮数
    consensus_reached: bool             # 全局共识收敛标志



# -------------------定义主图的schema-------------------
class MainGraphState(TypedDict):
    """主图的全局状态"""
    # === 主图专有字段 ===
    messages: Annotated[List[BaseMessage], add_messages]  # 对话历史
    start_diagnosis: bool                                  # 是否开始诊断的标志
    final_report: str                                      # 最终综合诊断报告（由 summary_node 生成）

    # === 患者信息字段（传递给各子图）===
    patient_info: Dict[str, Any]                          # 结构化患者信息
    summary_with_dialogue: str                            # 预诊断对话的摘要（对话历史总结）
    patient_portrait: str                                 # 患者结构化画像（文本形式）

    # === MDT 子图输出字段（从 MDT 接收）===
    expert_pool: Annotated[Dict[str, ExpertGroupState], operator.ior]  # 专家组档案袋
    blackboard: SharedBlackboard                                        # 公共黑板（专家报告、冲突）
    consensus_reached: bool                                             # 专家是否达成共识（MDT 输出）
    round_count: int                                                    # 当前博弈轮数
    max_rounds: int                                                     # 最大限制轮数


