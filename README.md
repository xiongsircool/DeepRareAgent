<p align="center">
  <img src="images/hero_banner.png" alt="DeepRareAgent Banner" width="100%" style="aspect-ratio: 3/1; object-fit: cover;">
</p>

# DeepRareAgent

**面向罕见病诊断的多组 MDT 集成系统 (Multi-Team MDT Ensemble for Rare Disease Diagnosis)**

---

## 项目简介

**DeepRareAgent** 是一个专为罕见病诊断设计的 AI 辅助系统。其核心不是简单的"一条路"诊断，而是模拟医院里由多个独立团队参与的 **多组多学科会诊 (Multi-Team MDT)** 机制。

**核心思想**：让多个"全能"的 MDT 团队各自独立分析同一个复杂病例，然后将各团队的诊断意见进行交叉验证与迭代拟合，最终输出一份高置信度的综合报告。

![系统架构](images/multi_team_mdt_arch.png)

---

## 核心特性

### 1. 多智能体团队并行 (Multi-Team Parallelism)

系统可配置 **N 个独立的诊断组 (Group)**，如 `group_1`, `group_2`。每个 Group 是一个功能完整的 AI 团队：

| 角色 | 说明 |
|---|---|
| **Main Agent (主控)** | 负责整体诊断规划、逻辑整合与报告撰写。 |
| **Sub-Agent 1 (Phenotype Analyst)** | 负责调用 HPO 表型本体工具，将症状标准化。 |
| **Sub-Agent 2 (Literature Researcher)** | 负责调用 PubMed、搜索引擎等工具检索证据。 |

每个团队**独立进行**从症状分析、文献检索到报告输出的完整流程，彼此不干扰。

### 2. 共识与拟合 (Consensus & Fitting)

所有团队完成诊断后，系统不会简单取平均或投票。而是：
1.  **Expert Review Node**: 一个专门的节点负责对比各组报告，提取冲突点和共同认知。
2.  **Blackboard (公共黑板)**: 各组报告、分歧与共识会被发布到黑板上。
3.  **多轮迭代 (Multi-Round Loop)**: 如果共识未达成，系统会启动新一轮诊断，各组阅读黑板上的信息后重新分析，直到达成共识或轮数耗尽。

### 3. 三阶段流程

整个系统分为三个主要阶段：

| 阶段 | 节点 | 功能 |
|---|---|---|
| **P01: Pre-Diagnosis** | `prediagnosis` | 智能问诊，收集患者基本信息、症状、家族史。当信息足够时，判断是否需要启动深度诊断。 |
| **P02: MDT Diagnosis** | `mdt_diagnosis` (子图) | 多组专家并行分析，经过多轮迭代达成共识。 |
| **P03: Summary** | `summary` | 整合所有专家组报告，生成最终的综合诊断报告。 |

---

## 项目结构

```
DeepRareAgent/
├── DeepRareAgent/
│   ├── graph.py                    # 主图定义 (P01 -> P02 -> P03)
│   ├── schema.py                   # 状态定义 (MainGraphState, MDTGraphState, ExpertGroupState)
│   ├── p01pre_diagnosis_agent.py   # 预诊断智能体
│   ├── p02_mdt/
│   │   ├── graph.py                # MDT 子图定义
│   │   ├── builddeepexportnode.py  # 专家组节点工厂 (构建 Main/Sub Agent 级联)
│   │   ├── nodes.py                # 路由、扇出等辅助节点
│   │   └── export_reviwer_node.py  # 专家互审/共识节点
│   ├── p03summary_agent.py         # 汇总报告节点
│   ├── tools/                      # 各类工具 (HPO, PubMed, 搜索等)
│   └── prompts/                    # 各智能体的系统提示词
├── config.yml                      # 主配置文件 (模型、API Key、Group 定义)
└── langgraph.json                  # LangGraph 服务配置
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install -e . "langgraph-cli[inmem]"
```

### 2. 配置

```bash
# 复制配置模板
cp config.example.yml config.yml
cp .env.example .env

# 编辑 config.yml，填入你的 LLM API Key 和 Base URL
```

### 3. 启动服务

```bash
langgraph dev
```

*   **API**: `http://127.0.0.1:2024`
*   **LangGraph Studio**: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`

---

## 配置说明

在 `config.yml` 中，`multi_expert_diagnosis_agent` 下的每个 `group_*` 都是一个独立的诊断团队。你可以：
*   增加或减少 Group 数量。
*   为每个 Group 配置不同的模型（如 group_1 用 GPT-4，group_2 用 Claude）。
*   为每个 Sub-Agent 配置不同的工具集。

```yaml
multi_expert_diagnosis_agent:
  group_1:
    main_agent:
      name: "Clinical_Lead_G1"
      model_name: "gpt-4o"
      ...
    sub_agent:
      sub_agent_1:  # Phenotype Analyst
        ...
      sub_agent_2:  # Literature Researcher
        ...
  group_2:
    # ... 同上，可使用不同模型
```

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE)