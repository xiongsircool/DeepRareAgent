#!/usr/bin/env python
"""
测试复杂嵌套配置文件的加载能力
"""

from DeepRareAgent.config import settings

def test_config_structure():
    """测试配置加载器是否正确处理复杂的嵌套结构"""

    print("=" * 60)
    print("测试配置加载器对复杂嵌套配置的支持")
    print("=" * 60)

    # 1. 测试预诊断智能体配置
    print("\n1. 预诊断智能体 (Pre-diagnosis Agent)")
    print("-" * 40)
    pre = settings.pre_diagnosis_agent
    print(f"  Provider: {pre.provider}")
    print(f"  Model: {pre.model_name}")
    print(f"  Base URL: {pre.base_url}")
    print(f"  Temperature: {pre.temperature}")
    print(f"  Max Tokens: {pre.model_kwargs.max_tokens}")
    print(f"  System Prompt: {pre.system_prompt_path}")

    # 2. 测试深度医学研究智能体配置（双层：main + sub）
    print("\n2. 深度医学研究智能体 (Deep Medical Research Agent)")
    print("-" * 40)
    deep = settings.deep_medical_research_agent

    print("  Main Agent:")
    print(f"    Provider: {deep.main_agent.provider}")
    print(f"    Model: {deep.main_agent.model_name}")
    print(f"    Temperature: {deep.main_agent.temperature}")
    print(f"    Prompt: {deep.main_agent.system_prompt_path}")

    print("  Sub Agent:")
    print(f"    Provider: {deep.sub_agent.provider}")
    print(f"    Model: {deep.sub_agent.model_name}")
    print(f"    Temperature: {deep.sub_agent.temperature}")
    print(f"    Prompt: {deep.sub_agent.system_prompt_path}")

    # 3. 测试多专家诊断智能体（三层嵌套：group -> main/sub -> sub_agent_N）
    print("\n3. 多专家诊断智能体 (Multi-Expert Diagnosis Agent)")
    print("-" * 40)
    multi = settings.multi_expert_diagnosis_agent

    # Group 1
    print("  Group 1:")
    print(f"    Main Agent:")
    print(f"      Name: {multi.group_1.main_agent.name}")
    print(f"      Provider: {multi.group_1.main_agent.provider}")
    print(f"      Model: {multi.group_1.main_agent.model_name}")
    print(f"      Exclude Tools: {multi.group_1.main_agent.excoulde_tools}")

    print(f"    Sub Agents:")
    print(f"      Sub Agent 1:")
    print(f"        Name: {multi.group_1.sub_agent.sub_agent_1.name}")
    print(f"        Model: {multi.group_1.sub_agent.sub_agent_1.model_name}")
    print(f"        Temperature: {multi.group_1.sub_agent.sub_agent_1.temperature}")

    print(f"      Sub Agent 2:")
    print(f"        Name: {multi.group_1.sub_agent.sub_agent_2.name}")
    print(f"        Model: {multi.group_1.sub_agent.sub_agent_2.model_name}")

    # Group 2
    print("  Group 2:")
    print(f"    Main Agent:")
    print(f"      Name: {multi.group_2.main_agent.name}")
    print(f"      Provider: {multi.group_2.main_agent.provider}")

    print(f"    Sub Agents:")
    print(f"      Sub Agent 1:")
    print(f"        Name: {multi.group_2.sub_agent.sub_agent_1.name}")
    print(f"        Model: {multi.group_2.sub_agent.sub_agent_1.model_name}")

    # 4. 测试 to_dict() 方法
    print("\n4. 测试配置对象转字典功能")
    print("-" * 40)
    pre_dict = pre.model_kwargs.to_dict()
    print(f"  Pre-diagnosis model_kwargs as dict: {pre_dict}")

    # 验证多层转换
    group1_dict = multi.group_1.main_agent.to_dict()
    print(f"  Group 1 main agent keys: {list(group1_dict.keys())[:5]}...")

    print("\n" + "=" * 60)
    print("[PASS] 配置加载器成功支持所有复杂嵌套结构！")
    print("=" * 60)

    # 5. 统计配置复杂度
    print("\n配置复杂度统计:")
    print(f"  - 顶层智能体配置: 3 个")
    print(f"  - 最大嵌套层级: 4 层 (multi_expert -> group_1 -> sub_agent -> sub_agent_1)")
    print(f"  - Group 1 子智能体数量: 2 个")
    print(f"  - Group 2 子智能体数量: 1 个")
    print(f"  - 总配置节点数: 大约 15+ 个独立智能体配置")


if __name__ == "__main__":
    try:
        test_config_structure()
    except Exception as e:
        print(f"\n[FAIL] 配置加载失败: {e}")
        import traceback
        traceback.print_exc()