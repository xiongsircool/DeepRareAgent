#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试证据引用处理功能
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from DeepRareAgent.utils.report_utils import process_expert_report_references


def test_ref_processing():
    """测试 <ref> 标签处理"""
    
    # 测试报告（包含 <ref> 标签）
    test_report = """# 诊断报告 - 专家组1

## 诊断意见
法布雷病（Fabry Disease）- 高度怀疑<ref>1</ref>

## 主要依据
1. 四肢阵发性疼痛（典型 Fabry 危象）
2. 少汗症（自主神经受累）
3. 皮肤血管角质瘤（特征性表现）<ref>2</ref>
4. 家族史符合 X-连锁遗传

## 建议检查
- α-半乳糖苷酶A活性检测
- GLA基因测序
"""

    # 测试证据列表
    test_evidences = [
        "患者自述手脚疼痛，像烧灼一样，尤其夏天严重。",
        "体检发现躯干部位有红色小点，压之不退色。"
    ]
    
    print("=" * 80)
    print("测试证据引用处理功能")
    print("=" * 80)
    
    print("\n原始报告:")
    print("-" * 80)
    print(test_report)
    print("-" * 80)
    
    print("\n证据列表:")
    for i, evidence in enumerate(test_evidences, 1):
        print(f"  [{i}] {evidence}")
    
    # 处理报告
    processed_report = process_expert_report_references(test_report, test_evidences)
    
    print("\n处理后的报告:")
    print("=" * 80)
    print(processed_report)
    print("=" * 80)
    
    # 验证是否添加了证据详情
    if "#### 引用证据详情" in processed_report:
        print("\n[PASS] 成功：证据详情已添加到报告末尾")
    else:
        print("\n[FAIL] 失败：未找到证据详情部分")
    
    # 检查引用编号
    if "[1]" in processed_report and "[2]" in processed_report:
        print("[PASS] 成功：证据编号已正确添加")
    else:
        print("[FAIL] 失败：证据编号缺失")


if __name__ == "__main__":
    test_ref_processing()
