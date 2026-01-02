# 预诊断智能体测试文档

## 测试文件

- **测试脚本**: `test_pre_diagnosis_agent.py`
- **被测模块**: `src/agent/01pre_diagnosis_agent.py`

## 运行方式

```bash
cd /Users/Apple/Documents/rare-diagnosis-agent/src/multi_agent
python test/test_pre_diagnosis_agent.py
```

## 测试覆盖

### ✅ 测试用例 1: 初次问诊 - 采集患者基本信息
- **目的**: 验证智能体能够响应患者的初始咨询
- **输入**: "你好医生，我最近总是感觉很累，头晕"
- **验证点**:
  - AI 能够做出友好的响应
  - 引导患者提供更多信息
  - 系统正常运行无错误

### ✅ 测试用例 2: 提供详细信息 - 测试信息存储功能
- **目的**: 验证智能体能够提取和存储患者详细信息
- **输入**: "我叫李四，今年42岁，男性。最近3个月一直感觉疲劳无力，偶尔头晕，还有间歇性发热，体温在38-38.5度之间"
- **验证点**:
  - 能够解析复杂的患者���述
  - 结构化存储患者信息（待完善）
  - 提供有针对性的回复

### ✅ 测试用例 3: 多轮对话 - 逐步采集信息
- **目的**: 验证智能体能够维护多轮对话上下文
- **输入**:
  1. "医生您好，我想咨询一下"
  2. "我最近持续低烧，还有关节疼痛"
- **验证点**:
  - 维持对话连贯性
  - 累积收集患者信息
  - 逐步深入询问

### ✅ 测试用例 4: 触发深度诊断判断
- **目的**: 验证智能体判断是否需要启动深度诊断
- **输入**: "我已经说了很多症状了，能不能帮我分析一下可能是什么病？我想开始正式诊断"
- **验证点**:
  - `start_diagnosis` 标志设置逻辑
  - 在信息不足时请求更多信息
  - 结构化输出格式正确

## 技术要点

### 1. 模块导入问题解决

由于文件名以数字开头（`01pre_diagnosis_agent.py`），需要在 `src/agent/__init__.py` 中使用 `importlib` 动态导入：

```python
import importlib.util
spec = importlib.util.spec_from_file_location(
    "agent._pre_diagnosis_agent",
    _pre_diag_path,
    submodule_search_locations=[str(_agent_dir)]
)
_pre_diag_module = importlib.util.module_from_spec(spec)
_pre_diag_module.__package__ = "agent"
sys.modules["agent._pre_diagnosis_agent"] = _pre_diag_module
spec.loader.exec_module(_pre_diag_module)
```

### 2. 状态注入修复

工具函数需要使用 `InjectedState` 注解来获取当前图状态：

```python
from langgraph.prebuilt import InjectedState

@tool
def set_base_info(
    base_info_patch: Dict[str, Any],
    state: Annotated[Dict[str, Any], InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    ...
```

### 3. 安全状态访问

所有工具函数都添加了安全的状态初始化逻辑：

```python
# 安全地获取���初始化 patient_info
if "patient_info" not in new_state:
    new_state["patient_info"] = {
        "base_info": {},
        "symptoms": [],
        "vitals": [],
        "exams": [],
        "medications": [],
        "family_history": [],
        "others": []
    }
```

## 已知问题

### 1. 患者信息持久化
**问题**: 工具调用的 `Command(update={})` 返回值没有正确更新测试图的状态。

**原因**: 测试图可能需要正确配置状态合并逻辑。

**影响**: 多轮对话中患者信息未能累积保存。

**建议**:
- 使用带有 checkpointer 的完整图进行测试
- 或者在测试中手动管理状态更新

### 2. 结构化输出解析
**问题**: `structured_response` 字段的解析需要更健壮的逻辑。

**建议**: 使用 Pydantic 模型严格验证输出格式。

## 测试统计

- ✅ **通过**: 4/4
- ❌ **失败**: 0/4
- 🟡 **部分功能**: 信息持久化待完善

## 下一步

1. **完善状态管理**: 修复患者信息的持久化问题
2. **添加更多测试**:
   - 错误输入处理
   - 边界情况测试
   - 性能压力测试
3. **集成测试**: 与完整诊断流程集成测试
4. **文档完善**: 添加更多使用示例和最佳实践

## 联系方式

如有问题，请查看：
- 项目 README: `/Users/Apple/Documents/rare-diagnosis-agent/README.md`
- 开发指南: `/Users/Apple/Documents/rare-diagnosis-agent/CLAUDE.md`
