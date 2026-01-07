# 汇总报告生成逻辑详解

## [LIST] 总览

汇总节点（`summary_node`）是诊断流程的最后一个节点，负责整合所有专家组的诊断意见，生成一份结构化的综合诊断报告。

## 🔄 完整数据流

```
MDT 专家组诊断
    ↓
expert_pool (各组状态)
blackboard.published_reports (各组报告)
    ↓
summary_node
    ↓
格式化专家报告 → 加载系统提示词 → 调用 LLM → 生成综合报告
    ↓
final_report
```

## 📥 输入数据结构

### 1. MainGraphState

汇总节点从主图状态中读取以下数据：

```python
{
    # 患者画像（可选，用于报告开头）
    "patient_portrait": "35岁男性，四肢疼痛10年...",
    
    # 专家组池（包含证据列表）
    "expert_pool": {
        "group_1": {
            "group_id": "group_1",
            "report": "...",
            "evidences": [
                "患者自述手脚疼痛，像烧灼一样",
                "体检发现躯干部位有红色小点"
            ],
            "is_satisfied": True
        },
        "group_2": {...}
    },
    
    # 公共黑板（已发布的报告）
    "blackboard": {
        "published_reports": {
            "group_1": "# 诊断报告\n...<ref>1</ref>...",
            "group_2": "# 诊断报告\n..."
        }
    }
}
```

### 2. 关键字段说明

| 字段 | 来源 | 说明 |
|------|------|------|
| `blackboard.published_reports` | expert_review 节点 | 各专家组最终发布的诊断报告 |
| `expert_pool` | 各专家诊断节点 | 包含证据列表等详细信息 |
| `patient_portrait` | triage_to_mdt 节点 | 患者信息的文本格式 |

## [SYSTEM] 处理流程

### 步骤 1: 验证输入

```python
# 检查是否有专家报告
reports = state["blackboard"]["published_reports"]

if not reports:
    raise ValueError("错误：未找到任何专家报告")
```

**失败时**：直接抛出异常，中止流程

### 步骤 2: 格式化专家报告

调用 `_format_expert_reports()` 函数处理证据引用：

#### 2.1 证据引用机制

专家在撰写报告时，可以使用 `<ref>N</ref>` 标签引用证据：

```markdown
# 专家报告示例

患者存在四肢疼痛<ref>1</ref>，伴随皮肤血管角质瘤<ref>2</ref>。

## 诊断依据
1. 疼痛性质符合神经病变<ref>1</ref>
2. 皮肤表现典型<ref>2</ref>
```

其中 `evidences` 列表为：
```python
[
    "患者自述手脚疼痛，像烧灼一样，尤其夏天严重。",  # index 0 → ref 1
    "体检发现躯干部位有红色小点，压之不退色。"      # index 1 → ref 2
]
```

#### 2.2 处理后的效果

```markdown
# 专家报告

患者存在四肢疼痛<ref>1</ref>，皮肤血管角质瘤<ref>2</ref>。

#### 引用证据详情
[1] 患者自述手脚疼痛，像烧灼一样，尤其夏天严重。
[2] 体检发现躯干部位有红色小点，压之不退色。
```

### 步骤 3: 加载系统提示词

```python
prompt_path = settings.summary_agent.system_prompt_path
# 来源: DeepRareAgent/prompts/03summary_prompt.txt
```

**系统提示词定义**：
- 汇总专家的角色和职责
- 报告的结构和格式
- 示例报告模板
- 特殊情况处理规则

### 步骤 4: 构建完整提示词

```python
System Prompt: 你是罕见病诊断汇总专家...

User Prompt:
    患者信息: ...
    
    专家组报告:
    ================
    专家组: group_1
    ================
    [报告内容 + 证据详情]
    
    ================
    专家组: group_2
    ================
    [报告内容 + 证据详情]
    
    特别注意:
    1. 辩证分析
    2. 盲点检查
    3. 具体建议
```

### 步骤 5: 调用 LLM

```python
llm = create_llm_from_config(settings.summary_agent)
# 模型: DeepSeek-V3.2
# Temperature: 0.1 (低温度保证一致性)

response = llm.invoke([system_msg, user_msg])
final_report = response.content
```

## 📤 输出格式

### 标准报告结构

```markdown
综合诊断报告

【病例摘要】
患者XXX，XX岁，性别X
主诉：...
核心表现：...

【专家组诊断意见】
1. 专家组1
   - 诊断：法布雷病（高度怀疑）
   - 依据：四肢疼痛 + 皮肤血管角质瘤 + 家族史

2. 专家组2
   - 诊断：法布雷病（高度可能）
   - 依据：肾功能异常 + 心脏异常

【共识性结论】
两组专家一致认为法布雷病可能性极高

【推荐诊断】
首要诊断：法布雷病（Fabry Disease, OMIM #301500）
鉴别诊断：其他溶酶体贮积症

【下一步建议】
1. 必要检查：
   - α-半乳糖苷酶A活性检测
   - GLA基因测序
   
2. 治疗建议：酶替代治疗

3. 随访计划：每3月复查肾功能

【重要提示】
[WARN] 进行性疾病，早诊早治至关重要
[WARN] 建议家系筛查
```

## [SEARCH] 关键特性

### 1. 证据溯源

每个诊断结论都可追溯到具体证据：

```
诊断：法布雷病
依据：四肢疼痛<ref>1</ref>

[1] 患者自述：手脚像火烧一样疼
```

### 2. 多专家整合

- [PASS] 自动识别共识
- [PASS] 客观呈现分歧
- [PASS] 权衡证据强度

### 3. 临床实用性

- 明确的下一步检查
- 具体到检查项目名称
- 包含治疗和随访建议

## [INFO] 完整示例流程

### 输入状态

```python
{
    "patient_portrait": "35岁男性，疼痛10年",
    "expert_pool": {
        "group_1": {
            "evidences": ["手脚疼痛像烧灼", "躯干红色小点"]
        }
    },
    "blackboard": {
        "published_reports": {
            "group_1": "法布雷病<ref>1</ref>皮损<ref>2</ref>"
        }
    }
}
```

### 处理过程

1. **提取报告**: `"法布雷病<ref>1</ref>皮损<ref>2</ref>"`
2. **处理引用**: 
   ```
   法布雷病<ref>1</ref>皮损<ref>2</ref>
   
   #### 引用证据详情
   [1] 手脚疼痛像烧灼
   [2] 躯干红色小点
   ```
3. **发送给LLM**: 系统提示词 + 格式化后的报告
4. **生成报告**: 结构化的综合诊断报告

### 输出结果

```python
{
    "messages": [AIMessage(content="综合诊断报告\n...")],
    "final_report": "综合诊断报告\n【病例摘要】\n..."
}
```

## 🎯 质量保证

### 1. 提示词约束

- [FAIL] 不捏造信息
- [FAIL] 不过度解读
- [PASS] 客观说明问题
- [PASS] 使用标准术语

### 2. 低温度设置

```yaml
temperature: 0.1  # 减少随机性，提高稳定性
```

### 3. 特殊要求

- 辩证分析多个候选诊断
- 检查专家的盲点
- 提供精确的检查建议

## [DEV] 代码位置

| 组件 | 文件 |
|------|------|
| 主函数 | `DeepRareAgent/p03summary_agent.py::summary_node` |
| 证据处理 | `DeepRareAgent/utils/report_utils.py::process_expert_report_references` |
| 系统提示词 | `DeepRareAgent/prompts/03summary_prompt.txt` |
| 配置 | `config.yml::summary_agent` |

## 💡 总结

汇总报告生成是一个**多步骤、结构化**的过程：

1. [PASS] 收集专家报告
2. [PASS] 处理证据引用
3. [PASS] 加载角色定义
4. [PASS] 调用强大的 LLM
5. [PASS] 生成临床可用报告

**核心优势**：
- [INFO] 证据可追溯
- 🤝 多专家整合
- [LIST] 结构化输出
- [MEDICAL] 临床实用性

**设计理念**：通过精心设计的提示词和低温度设置，确保生成的报告**准确、客观、实用**。
