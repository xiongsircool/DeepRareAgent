# 边缘情况与潜在问题分析

## 1. 并行节点的消息处理问题 [WARN]

### 问题描述
MDT 子图中，多个专家节点（group_1, group_2, ...）是**并行执行**的。

### 当前情况
```python
# p02_mdt/builddeepexportnode.py:245-250
return {
    "expert_pool": {
        group_id: update_export_state
    }
}
# [FAIL] 没有返回 messages
```

### 潜在问题

#### 场景 1：如果添加 messages
```python
return {
    "expert_pool": {...},
    "messages": [AIMessage(content=f"专家组 {group_id} 完成诊断")]
}
```

**问题**：
- group_1 和 group_2 并行执行
- 两个节点都返回 messages
- LangGraph 的 `add_messages` reducer 会合并这些消息
- 但**顺序不确定**！

**用户可能看到**：
```
1. [LAB] 正在初始化多专家会诊系统
2. 专家组 group_2 完成诊断  ← 顺序随机
3. 专家组 group_1 完成诊断  ← 顺序随机
4. [PASS] 第 1 轮专家互审完成
```

#### 场景 2：不添加 messages（当前方案）
**优点**：
- [PASS] 避免消息顺序混乱
- [PASS] 用户体验更清晰（只看到关键节点）

**缺点**：
- [FAIL] 用户看不到专家组的工作进度
- [FAIL] 对于耗时较长的诊断，用户可能不知道系统在工作

### 建议方案
**保持当前设计**（不在并行节点添加消息），原因：
1. 专家诊断是内部过程，用户不需要看到细节
2. expert_review 节点会汇总结果，用户可以看到整体进度
3. 避免并行消息顺序混乱的问题

---

## 2. 多轮诊断的消息累积问题 [WARN]

### 问题描述
如果 MDT 进行多轮诊断（例如 3 轮），messages 会累积很多条。

### 当前情况
```
轮次 1:
- [LAB] 初始化
- [PASS] 第 1 轮专家互审完成 (满意度: 1/2)

轮次 2:
- [PASS] 第 2 轮专家互审完成 (满意度: 2/2) - 已达成共识！

最终:
- [Summary] 综合诊断报告
```

### 潜在问题
- 如果进行 3 轮，会有 4 条 MDT 消息（1 初始化 + 3 轮进度）
- 对于简单情况（1 轮就达成共识），消息较少
- 对于复杂情况（3 轮），消息较多

### 是否需要优化？
**[FAIL] 不需要**，原因：
1. 这些消息都是有用的进度提示
2. 用户需要知道系统在每轮的进展
3. messages 数量可控（最多 max_rounds + 2 条）

---

## 3. fan_out 节点的消息问题 🤔

### 问题描述
fan_out 节点在多轮诊断时会执行，但当前不返回 messages。

### 当前情况
```python
# p02_mdt/nodes.py:107-121
def fan_out_node(state: MDTGraphState, config: RunnableConfig):
    print(f">>> [MDT 扇出] 开始第 {round_count} 轮专家诊断...")
    return {}  # [FAIL] 不返回 messages
```

### 用户体验分析

#### 场景：不添加 messages（当前）
```
用户看到:
1. [LAB] 初始化
2. [PASS] 第 1 轮互审完成 (1/2)
   [系统内部: fan_out → expert nodes → expert_review]
3. [PASS] 第 2 轮互审完成 (2/2) - 已达成共识！
```

#### 场景：添加 messages
```
用户看到:
1. [LAB] 初始化
2. [PASS] 第 1 轮互审完成 (1/2)
3. 🔄 开始第 2 轮专家诊断...  ← 新增
4. [PASS] 第 2 轮互审完成 (2/2) - 已达成共识！
```

### 建议
**可选添加**，取决于用户体验偏好：
- **不添加**：消息更简洁，用户只看结果
- **添加**：用户能看到系统正在进行下一轮（对于耗时长的场景更友好）

---

## 4. 错误处理的消息问题 [WARN]

### 问题描述
当专家节点执行出错时，当前没有向用户显示错误提示。

### 当前情况
```python
# p02_mdt/builddeepexportnode.py:252-269
except Exception as e:
    print(f"[错误] {agent_name} 执行出错: {e}")
    return {
        "expert_pool": {
            group_id: {
                "has_error": True,
                "report": f"执行异常: {str(e)}"
            }
        }
    }
    # [FAIL] 没有返回 messages 告知用户
```

### 潜在问题
- 用户**看不到**专家组执行失败
- 只能从最终报告中发现（如果 summary 节点处理了错误）
- 用户体验差

### 建议方案
**建议添加错误消息**：
```python
except Exception as e:
    error_msg = f"[WARN] 专家组 {group_id} 执行出错: {str(e)[:50]}..."
    return {
        "expert_pool": {...},
        "messages": [AIMessage(content=error_msg)]  # ← 新增
    }
```

**优点**：
- [PASS] 用户立即知道出错了
- [PASS] 可以提前终止或采取措施
- [PASS] 更好的用户体验

---

## 5. Summary 节点的错误处理 [WARN]

### 当前情况
```python
# p03summary_agent.py:35-41
if not reports:
    error_msg = "错误：未能获取专家诊断报告，无法生成综合诊断。"
    return {
        "messages": [AIMessage(content=error_msg)],  # [PASS] 有消息
        "final_report": error_msg
    }
```

### 评估
[PASS] **处理正确**，summary 节点在错误情况下会返回错误消息。

---

## 总结

### [PASS] 当前修复已覆盖的必要点
1. MDT 初始化消息（triage_to_mdt_node）
2. 专家互审进度消息（expert_review）
3. Summary 错误处理

### [WARN] 需要考虑添加的点
1. **高优先级**：专家节点错误消息（builddeepexportnode 异常分支）
2. **可选**：fan_out 节点新轮次提示（取决于用户体验偏好）
3. **不推荐**：专家节点成功消息（会导致并行消息顺序混乱）

### [NOTE] 优化建议优先级
1. 🔴 **必须添加**：专家节点错误消息
2. 🟡 **可选添加**：fan_out 节点轮次提示
3. 🟢 **保持现状**：其他节点
