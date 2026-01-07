#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 summary_style 自定义报告格式功能
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


# 示例1：默认格式（summary_style 为空）
default_style_example = {
    "summary_style": ""  # 空字符串，使用默认格式
}

# 示例2：简洁格式
brief_style_example = {
    "summary_style": """
报告格式要求（简洁版）：

1. **诊断结论**（1段）：直接给出明确诊断
2. **关键依据**（3-5条）：列出最重要的诊断依据
3. **必做检查**（2-3项）：列出确诊必需的检查项目
4. **治疗建议**（1段）：简要说明治疗方案
5. **注意事项**（3-5条）：患者需要知道的重要信息

要求：简洁明了，总长度控制在1000字以内
"""
}

# 示例3：学术论文格式
academic_style_example = {
    "summary_style": """
报告格式要求（学术论文式）：

## Abstract
[疾病诊断的简要摘要，100字以内]

## Introduction
[病例背景介绍]

## Clinical Presentation
[临床表现详细描述]

## Differential Diagnosis
[鉴别诊断分析，每个诊断需列出支持和反对证据]

## Final Diagnosis
[最终诊断及诊断依据]

## Management Plan
[治疗和管理方案]

## Discussion
[病例讨论和文献回顾]

## References
[如有引用证据，请使用 <ref>N</ref> 标注]

要求：使用学术化语言，结构严谨
"""
}

# 示例4：患者友好版
patient_friendly_example = {
    "summary_style": """
报告格式要求（患者友好版）：

### 您的诊断结果
[用通俗语言说明诊断，避免复杂医学术语]

### 这是什么病？
[用简单的语言解释疾病是什么、为什么会得这个病]

### 为什么是这个诊断？
[用患者能理解的方式说明诊断依据]

### 接下来要做什么？
[明确告诉患者需要做哪些检查，用什么方法治疗]

### 日常生活中要注意什么？
[生活建议、饮食注意事项、什么情况需要立即就医]

### 常见问题解答
Q: 这个病严重吗？
A: [回答]

Q: 可以治愈吗？
A: [回答]

Q: 会遗传吗？
A: [回答]

要求：语言通俗易懂，避免使用复杂医学术语，必要时加注解释
"""
}

# 示例5：临床病历格式
medical_record_example = {
    "summary_style": """
报告格式要求（临床病历格式）：

入院记录

患者姓名：[编号]
入院时间：[日期]
主诉：[主要症状]

现病史：
[详细病史]

初步诊断：
主要诊断：[诊断名称]
诊断依据：
1. [依据1]
2. [依据2]
...

诊疗计划：
1. 完善检查：[列出]
2. 治疗方案：[列出]
3. 护理要点：[列出]

医师签名：[AI生成]
日期：[当前日期]

要求：符合医院病历书写规范
"""
}

# 示例6：多语言格式（中英双语）
bilingual_example = {
    "summary_style": """
报告格式要求（中英双语）：

## 诊断结论 / Diagnosis
[中文诊断] / [English Diagnosis]

## 诊断依据 / Diagnostic Criteria
1. [中文依据1] / [English Evidence 1]
2. [中文依据2] / [English Evidence 2]

## 治疗建议 / Treatment Recommendations
[中文治疗方案] / [English Treatment Plan]

## 注意事项 / Important Notes
[中文注意事项] / [English Precautions]

要求：每个章节都提供中英双语对照
"""
}


def print_example(name, example):
    """打印示例"""
    print("\n" + "=" * 80)
    print(f"示例：{name}")
    print("=" * 80)
    print("\n使用方法：")
    print("```python")
    print("state = {")
    print("    'summary_style': '''")
    print(example['summary_style'])
    print("    '''")
    print("}")
    print("```")


if __name__ == "__main__":
    print("=" * 80)
    print("summary_style 自定义报告格式示例")
    print("=" * 80)
    
    print("\n💡 功能说明：")
    print("   - summary_style 为空：使用默认的临床诊断报告格式")
    print("   - summary_style 有值：使用自定义格式")
    print("   - 可以用自然语言描述你想要的报告格式")
    
    print_example("默认格式", default_style_example)
    print_example("简洁格式", brief_style_example)
    print_example("学术论文格式", academic_style_example)
    print_example("患者友好版", patient_friendly_example)
    print_example("临床病历格式", medical_record_example)
    print_example("中英双语格式", bilingual_example)
    
    print("\n" + "=" * 80)
    print("使用建议")
    print("=" * 80)
    print("""
1. **默认格式适用于大多数情况**
   - 专业、完整、临床可用
   
2. **自定义格式的场景**
   - 患者导向：使用"患者友好版"
   - 学术研究：使用"学术论文格式"
   - 医院归档：使用"临床病历格式"
   - 国际交流：使用"中英双语格式"
   
3. **编写自定义格式的技巧**
   - 用清晰的章节标题
   - 说明每个部分要包含什么内容
   - 可以指定语言风格（专业/通俗）
   - 可以控制报告长度
   - 可以要求特定的排版格式
    """)
