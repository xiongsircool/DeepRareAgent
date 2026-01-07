import re
from typing import List

def process_expert_report_references(report_text: str, evidences: List[str]) -> str:
    """
    解析报告中的 <ref>id</ref> 标签，并将对应的证据内容追加到报告末尾。
    
    Args:
        report_text: 专家报告文本
        evidences: 该专家组的证据列表 (对应 extract_evidences 的内容)
        
    Returns:
        追加了证据详情的报告文本
    """
    if not report_text or not evidences:
        return report_text
        
    # 1. 查找所有唯一的引用 ID
    # 匹配 <ref>number</ref>
    ref_pattern = re.compile(r'<ref>(\d+)</ref>')
    matches = ref_pattern.findall(report_text)
    
    if not matches:
        return report_text
        
    # 转换 ID 并去重排序
    # ID 是 1-based (基于 extract_evidences 工具的输出格式)
    try:
        ref_ids = sorted(list(set(map(int, matches))))
    except ValueError:
        return report_text
    
    # 2. 提取对应的证据
    extracted_evidences = []
    for ref_id in ref_ids:
        # 检查 ID 是否有效 (1-based index)
        if 1 <= ref_id <= len(evidences):
            evidence_content = evidences[ref_id - 1]
            extracted_evidences.append(f"[{ref_id}] {evidence_content}")
        # 如果 ID 无效，我们可以选择忽略

    if not extracted_evidences:
        return report_text

    # 3. 拼接到报告末尾
    # 使用 Markdown 格式分隔
    formatted_evidence_section = "\n\n#### 引用证据详情\n" + "\n".join(extracted_evidences)
    
    return report_text + formatted_evidence_section
