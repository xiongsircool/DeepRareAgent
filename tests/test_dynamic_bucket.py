"""
测试患者信息管理工具的动态 bucket 创建功能
验证工具能够自动创建不存在的字段（如 medical_history），而不是抛出错误
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from DeepRareAgent.tools.patientinfo import (
    test_upsert_patient_facts,
    test_delete_patient_facts,
    patient_info_to_text
)


def test_dynamic_bucket_creation():
    """测试动态创建不存在的 bucket"""
    print("=" * 60)
    print("测试 1: 动态创建 medical_history bucket")
    print("=" * 60)
    
    # 初始化状态，只包含标准字段
    initial_state = {
        "messages": [],
        "patient_info": {
            "base_info": {},
            "symptoms": [],
            "vitals": [],
        }
    }
    
    # 尝试向不存在的 medical_history bucket 添加数据
    print("\n尝试添加 medical_history 数据...")
    cmd = test_upsert_patient_facts(
        initial_state,
        {
            "medical_history": [
                {"condition": "高血压", "year": "2015"},
                {"condition": "糖尿病", "year": "2018"}
            ]
        }
    )
    
    current_state = cmd.update
    print("✅ 成功！medical_history bucket 已自动创建")
    print("\n当前患者信息:")
    print(patient_info_to_text.invoke({"state": current_state}))
    
    # 验证数据是否正确存储
    assert "medical_history" in current_state["patient_info"]
    assert len(current_state["patient_info"]["medical_history"]) == 2
    print("\n✅ 验证通过：medical_history 包含 2 条记录")
    
    return current_state


def test_multiple_dynamic_buckets():
    """测试同时创建多个不存在的 buckets"""
    print("\n" + "=" * 60)
    print("测试 2: 同时创建多个动态 buckets")
    print("=" * 60)
    
    initial_state = {
        "messages": [],
        "patient_info": {
            "base_info": {"name": "测试患者"},
        }
    }
    
    # 同时添加多个不存在的 buckets
    print("\n尝试添加 allergies, surgeries, 和 lab_results...")
    cmd = test_upsert_patient_facts(
        initial_state,
        {
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
    )
    
    current_state = cmd.update
    print("✅ 成功！所有 buckets 已自动创建")
    print("\n当前患者信息:")
    print(patient_info_to_text.invoke({"state": current_state}))
    
    # 验证
    assert "allergies" in current_state["patient_info"]
    assert "surgeries" in current_state["patient_info"]
    assert "lab_results" in current_state["patient_info"]
    print("\n✅ 验证通过：所有动态 buckets 创建成功")
    
    return current_state


def test_delete_from_dynamic_bucket():
    """测试从动态创建的 bucket 中删除数据"""
    print("\n" + "=" * 60)
    print("测试 3: 从动态 bucket 删除数据")
    print("=" * 60)
    
    # 先创建带数据的状态
    state = test_dynamic_bucket_creation()
    
    # 获取第一条 medical_history 记录的 ID
    medical_history = state["patient_info"]["medical_history"]
    if medical_history:
        target_id = medical_history[0]["id"]
        print(f"\n尝试删除 ID 为 {target_id} 的记录...")
        
        cmd = test_delete_patient_facts(
            state,
            {"medical_history": [target_id]}
        )
        
        current_state = cmd.update
        print("✅ 删除成功！")
        print("\n当前患者信息:")
        print(patient_info_to_text.invoke({"state": current_state}))
        
        # 验证
        assert len(current_state["patient_info"]["medical_history"]) == 1
        print("\n✅ 验证通过：medical_history 现在只有 1 条记录")


def test_update_existing_record_in_dynamic_bucket():
    """测试更新动态 bucket 中的现有记录"""
    print("\n" + "=" * 60)
    print("测试 4: 更新动态 bucket 中的现有记录")
    print("=" * 60)
    
    # 先创建带数据的状态
    state = test_dynamic_bucket_creation()
    
    # 获取第一条记录的 ID
    medical_history = state["patient_info"]["medical_history"]
    if medical_history:
        existing_id = medical_history[0]["id"]
        print(f"\n尝试更新 ID 为 {existing_id} 的记录...")
        
        cmd = test_upsert_patient_facts(
            state,
            {
                "medical_history": [
                    {
                        "id": existing_id,
                        "condition": "高血压（已控制）",
                        "year": "2015",
                        "status": "稳定"
                    }
                ]
            }
        )
        
        current_state = cmd.update
        print("✅ 更新成功！")
        print("\n当前患者信息:")
        print(patient_info_to_text.invoke({"state": current_state}))
        
        # 验证记录数量没有增加
        assert len(current_state["patient_info"]["medical_history"]) == 2
        # 验证记录已更新
        updated_record = next(
            r for r in current_state["patient_info"]["medical_history"]
            if r["id"] == existing_id
        )
        assert updated_record["condition"] == "高血压（已控制）"
        assert "status" in updated_record
        print("\n✅ 验证通过：记录已正确更新，未创建重复")


if __name__ == "__main__":
    print("\n🧪 开始测试患者信息工具的动态 bucket 功能\n")
    
    try:
        test_dynamic_bucket_creation()
        test_multiple_dynamic_buckets()
        test_delete_from_dynamic_bucket()
        test_update_existing_record_in_dynamic_bucket()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！")
        print("=" * 60)
        print("\n总结:")
        print("✅ 工具可以自动创建不存在的 bucket（如 medical_history）")
        print("✅ 工具可以同时创建多个动态 buckets")
        print("✅ 工具可以从动态 bucket 中删除数据")
        print("✅ 工具可以更新动态 bucket 中的现有记录")
        print("\n现在您可以使用任何字段名称，工具会自动适配！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
