# 患者信息管理工具 - 动态字段支持

## 更新说明

患者信息管理工具现已支持**动态字段自动创建**功能，不再限制于预定义的字段列表。

## 修改内容

### 之前的行为
当尝试向不存在的 bucket（如 `medical_history`）添加、更新或删除数据时，工具会抛出错误：
```
ValueError: Unknown bucket: medical_history
```

### 现在的行为
工具会**自动创建**不存在的字段，无需预先定义。这使得工具更加灵活，可以适应各种患者信息需求。

## 使用示例

### 1. 添加到新字段
```python
# 向不存在的 medical_history 字段添加数据
# 工具会自动创建该字段
upsert_patient_facts.invoke({
    "payload": {
        "medical_history": [
            {"condition": "高血压", "year": "2015"},
            {"condition": "糖尿病", "year": "2018"}
        ]
    }
})
```

### 2. 同时创建多个新字段
```python
upsert_patient_facts.invoke({
    "payload": {
        "allergies": [
            {"allergen": "青霉素", "severity": "严重"}
        ],
        "surgeries": [
            {"procedure": "阑尾切除", "date": "2020-05-15"}
        ],
        "lab_results": [
            {"test": "血糖", "value": "6.5", "unit": "mmol/L"}
        ]
    }
})
```

### 3. 从动态字段中删除
```python
# 即使字段是动态创建的，删除操作也完全正常
delete_patient_facts.invoke({
    "payload": {
        "medical_history": ["RNU3"]  # 记录 ID
    }
})
```

## 技术细节

### 字段类型自动判断
- 如果字段名为 `base_info`，初始化为 **字典 (dict)**
- 其他所有字段初始化为 **列表 (list)**

### 修改的函数
1. `upsert_patient_facts` - 支持向动态字段添加/更新数据
2. `delete_patient_facts` - 支持从动态字段删除数据
3. `test_upsert_patient_facts` - 测试版本同步更新
4. `test_delete_patient_facts` - 测试版本同步更新

### 显示支持
`patient_info_to_text` 函数已支持动态字段显示：
- 预定义字段按标准顺序显示
- 动态创建的字段会附加在后面显示
- 字段名会自动格式化（下划线转空格，全大写）

## 预定义字段列表

以下字段会在工具初始化时自动创建：
- `base_info` - 基础信息（字典类型）
- `symptoms` - 症状
- `vitals` - 生命体征
- `exams` - 检查结果
- `medications` - 用药信息
- `family_history` - 家族史
- `past_medical_history` - 既往病史
- `others` - 其他信息

## 优势

1. **无需修改代码** - 添加新类型的患者信息时，不需要修改工具代码
2. **向后兼容** - 所有现有代码继续正常工作
3. **灵活性** - 可以根据实际需求动态添加任何字段
4. **一致性** - 所有动态字段都遵循相同的数据结构（带 ID 和时间戳）

## 测试

运行以下命令测试动态字段功能：
```bash
python tests/test_dynamic_bucket.py
```

测试涵盖：
- ✅ 动态创建单个字段
- ✅ 同时创建多个字段
- ✅ 从动态字段删除数据
- ✅ 更新动态字段中的记录
