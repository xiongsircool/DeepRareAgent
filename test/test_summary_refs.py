#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试汇总报告是否能使用证据引用
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from DeepRareAgent.utils.report_utils import process_expert_report_references


def test_summary_with_refs():
    """测试汇总报告引用证据"""
    
    # 模拟汇总报告（LLM生成，包含 <ref> 标签）
    summary_report = """# 罕见病诊断报告

## 二、临床诊断

**法布雷病**（Fabry Disease，OMIM #301500）

**诊断依据**：
1. 典型临床表现：四肢烧灼样疼痛<ref>1</ref>
2. 特征性体征：皮肤血管角质瘤<ref>2</ref>
3. 多系统受累：肾功能异常、心脏异常<ref>3</ref>
4. 遗传模式支持：X连锁家族史<ref>4</ref>
"""

    # 所有证据（从所有专家组收集）
    all_evidences = [
        "患者自述手脚疼痛，像烧灼一样，尤其夏天严重。",
        "体检发现躯干部位有红色小点，压之不退色。",
        "实验室检查：肌酐 150 μmol/L（↑），心脏超声左室壁厚度 14mm（↑）",
        "家族史：母亲有肾衰竭病史，符合X连锁遗传模式"
    ]
    
    print("=" * 80)
    print("测试汇总报告证据引用")
    print("=" * 80)
    
    print("\n原始汇总报告:")
    print("-" * 80)
    print(summary_report)
    print("-" * 80)
    
    print("\n所有证据列表:")
    for i, evidence in enumerate(all_evidences, 1):
        print(f"  [{i}] {evidence}")
    
    # 处理引用
    processed_report = process_expert_report_references(summary_report, all_evidences)
    
    print("\n处理后的汇总报告:")
    print("=" * 80)
    print(processed_report)
    print("=" * 80)
    
    # 验证
    if "#### 引用证据详情" in processed_report:
        print("\n[PASS] 成功：汇总报告可以支持证据引用！")
        print("💡 只需要：")
        print("   1. 在提示词中告诉LLM可以使用 <ref> 标签")
        print("   2. 收集所有专家的证据形成统一编号")
        print("   3. 在最后处理一次汇总报告的引用")
    else:
        print("\n[FAIL] 失败")


if __name__ == "__main__":
    test_summary_with_refs()
