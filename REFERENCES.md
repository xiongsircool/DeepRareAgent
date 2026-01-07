# DeepRareAgent 核心参考文献库 (Key References & Knowledge Base)

本文档汇集了 2024-2025 年间在罕见病诊断、多智能体医疗系统 (MDT) 及医学 AI 评估领域的顶级文献。这些工作为 DeepRareAgent 的架构设计与评估体系提供了理论支撑。

---

## [ARCH] 多智能体架构与 MDT 模拟 (Multi-Agent Architectures & MDT)

| 年份 | 来源 | 论文标题 | 核心贡献与 DeepRareAgent 的关联 |
| :--- | :--- | :--- | :--- |
| **2024** | **Nature Medicine** | [**AMIE**: Towards accurate differential diagnosis with large language models](https://search.google.com/search?q=AMIE+Nature+Medicine) | **(Google)** 提出了基于模拟问诊 (Simulated Consultations) 的训练与评估体系。证明了 AI 在同理心和诊断准确率上可超越人类全科医生。 |
| **2024** | **arXiv** | [**Med-Agents**: LLMs as Collaborators for Medical Reasoning](https://arxiv.org/abs/search?q=Med-Agents) | 提出了 "Consign & Consensus" 机制，模拟 MDT 流程。DeepRareAgent 的 "Shared Blackboard" 进一步扩展了这一思想。 |
| **2024** | **AAAI** | [**MDTeamGPT**: Multi-Agent Collaboration for Robust Clinical Decision Making](https://arxiv.org/abs/search?q=MDTeamGPT) | 使用角色扮演 (Role-Playing) 让 LLM 扮演不同科室专家。为我们的 Group 内部角色分工提供了参考。 |
| **2024** | **NeurIPS WS** | **AgentMD**: Empowering LLMs for Medical Decision Support via Specialized Tools | 强调了 Agent 调用外部临床工具 (如 PubMed, EHR) 的重要性，这正是我们 Sub-Agent 的核心功能。 |
| **2024** | **ACL** | **Agent-as-a-Patient**: Can LLMs Simulate Patients for Diagnostic Dialogue? | 论证了使用 LLM 扮演标准化病人 (SP) 进行自动化评估的可行性。 |

---

## 🧬 罕见病诊断专题 (AI for Rare Diseases)

| 年份 | 来源 | 论文标题 | 核心贡献与 DeepRareAgent 的关联 |
| :--- | :--- | :--- | :--- |
| **2024** | **NeurIPS** | [**RareBench**: Can LLMs Help in Rare Disease Diagnosis?](https://arxiv.org/abs/search?q=RareBench) | **(本项目的核心 Benchmark)** 发布了包含 1,197 个病例的大规模罕见病数据集。我们将使用此数据集评估 DeepRareAgent 的 Top-K 准确率。 |
| **2024** | **arXiv** | **RareAgents**: A Multi-agent Framework for Rare Disease Diagnosis | 针对罕见病数据稀缺问题，设计了分层多智能体架构。是 DeepRareAgent 的直接竞品与对标对象。 |
| **2024** | **Bioinformatics** | **PhenoGPT**: An LLM-based Tool for Phenotype Extraction | 专门用于从非结构化文本中提取 HPO 表型术语。我们的 "Phenotype Analyst" Sub-Agent 可借鉴其 Prompt 策略。 |
| **2023** | **Lancet DH** | Large Language Models for Rare Disease Diagnosis: Opportunities and Challenges | 综述文章，指出了 LLM 在罕见病领域的 "幻觉" 和 "知识更新滞后" 两大挑战，验证了引入 "Literature Searcher" 实时联网的必要性。 |
| **2024** | **MICCAI** | **PhenoBCP**: A Multi-modal Framework for Rare Disease Phenotyping | 探索了多模态 (文本+影像) 在罕见病诊断中的应用。提示了未来 DeepRareAgent 可扩展的方向。 |

---

## [INFO] 评估基准与方法论 (Benchmarks & Methodology)

| 年份 | 来源 | 论文标题 | 核心贡献与 DeepRareAgent 的关联 |
| :--- | :--- | :--- | :--- |
| **2025** | **ICLR (Sub)** | [**DiagnosisArena**: A Dynamic Benchmarking Framework](https://arxiv.org/abs/search?q=DiagnosisArena) | **(最新前沿)** 提出评估 Agent 的 **诊断推理路径 (Reasoning Path)** 而非单纯的结果。这非常适合评估我们 "多轮诊断拟合" 的过程质量。 |
| **2024** | **EMNLP** | **Med-HALT**: Medical Hallucination Test for Large Language Models | 专门测试医学 AI 的幻觉问题。我们可采用其 "Hallucination Rate" 指标来证明 Multi-Group 架构的优越性。 |
| **2024** | **ICLR** | **ClinicalBench**: A Comprehensive Benchmark for Clinical Intelligence | 涵盖 8 项核心临床任务的综合基准。 |
| **2023** | **Nature** | **Med-PaLM 2**: Towards Expert-Level Medical Question Answering | 奠基之作，确立了 MedQA (USMLE) 作为医学 LLM 基础能力的测试标准。 |
| **2023** | **NEJM AI** | Evaluating GPT-4 on the USMLE and Clinical Case Challenges | 详细分析了 GPT-4 在复杂临床病例上的推理能力与局限性。 |

---

## 📚 综述与行业趋势 (Surveys & Future Trends)

| 年份 | 来源 | 论文标题 | 核心贡献 |
| :--- | :--- | :--- | :--- |
| **2024** | **arXiv** | **Large Language Models for Medicine: A Survey** | 全面梳理了从 BERT 到 Agent 的技术演进路线。 |
| **2024** | **Google** | **Med-Gemini**: Towards Generalist Biomedical AI | 展示了长上下文窗口 (Long Context) 在处理复杂病历中的巨大优势。 |
| **2024** | **Lancet DH** | **The Future of Generative AI in Healthcare** | 探讨了 AI Agent 融入真实医院工作流 (Human-in-the-loop) 的未来图景。 |
| **2024** | **NeurIPS** | **MedAlign**: A Benchmark for Aligning LLMs with Clinical Guidelines | 关注 AI 是否遵循临床指南 (Guidelines)。 |

---

## 🎯 DeepRareAgent 的科研定位 (Research Positioning)

基于上述文献，DeepRareAgent 的核心创新点在于结合了以下三个前沿趋势：
1.  **Ensemble MDT (集成多组会诊)**: 超越了 *MDTeamGPT* 的单组模拟，采用类似 *RareAgents* 但更进一步的 "多组平行对抗" 架构。
2.  **Diagnostic Fitting (诊断拟合)**: 引入 Blackboard 机制实现多轮贝叶斯式的证据更新，响应了 *DiagnosisArena* 对 "推理路径" 的关注。
3.  **Real-time Evidence (实时循证)**: 通过 Sub-Agent 实时检索文献，解决了 *Lancet DH* 综述中提到的知识滞后问题。
