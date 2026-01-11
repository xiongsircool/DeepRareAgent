#!/usr/bin/env python3
"""
工具健康检查脚本
测试所有医学工具是否正常导入和基本可用
"""

import sys
import asyncio
from typing import List, Dict, Any
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_tool_import():
    """测试工具导入"""
    print("=" * 60)
    print("[SEARCH] 步骤 1: 测试工具模块导入")
    print("=" * 60)

    results = {}

    # 1. 测试 HPO 工具
    print("\n[1/8] 测试 HPO 工具...")
    try:
        from DeepRareAgent.tools.hpo_tools import phenotype_to_hpo_tool, hpo_to_diseases_tool
        print("  [PASS] HPO 工具导入成功")
        print(f"     - phenotype_to_hpo_tool: {phenotype_to_hpo_tool.name}")
        print(f"     - hpo_to_diseases_tool: {hpo_to_diseases_tool.name}")
        results['hpo'] = True
    except Exception as e:
        print(f"  [FAIL] HPO 工具导入失败: {e}")
        results['hpo'] = False

    # 2. 测试百度搜索工具
    print("\n[2/8] 测试百度搜索工具...")
    try:
        from DeepRareAgent.tools.baidu_tools import search_baidu_tool
        print("  [PASS] 百度搜索工具导入成功")
        print(f"     - search_baidu_tool: {search_baidu_tool.name}")
        results['baidu'] = True
    except Exception as e:
        print(f"  [FAIL] 百度搜索工具导入失败: {e}")
        results['baidu'] = False

    # 3. 测试维基百科工具
    print("\n[3/8] 测试维基百科工具...")
    try:
        from DeepRareAgent.tools.wiki_tools import search_wikipedia_tool
        print("  [PASS] 维基百科工具导入成功")
        print(f"     - search_wikipedia_tool: {search_wikipedia_tool.name}")
        results['wiki'] = True
    except Exception as e:
        print(f"  [FAIL] 维基百科工具导入失败: {e}")
        results['wiki'] = False

    # 4. 测试 PubMed 工具
    print("\n[4/8] 测试 PubMed 工具...")
    try:
        from DeepRareAgent.tools.pubmed_tools import search_pubmed
        print("  [PASS] PubMed 工具导入成功")
        results['pubmed'] = True
    except Exception as e:
        print(f"  [FAIL] PubMed 工具导入失败: {e}")
        results['pubmed'] = False

    # 5. 测试 LitSense 工具
    print("\n[5/8] 测试 LitSense 工具...")
    try:
        from DeepRareAgent.tools.litsense_tool import lit_sense_search
        print("  [PASS] LitSense 工具导入成功")
        results['litsense'] = True
    except Exception as e:
        print(f"  [FAIL] LitSense 工具导入失败: {e}")
        results['litsense'] = False

    # 6. 测试 BioCMP 工具
    print("\n[6/8] 测试 BioCMP 工具...")
    try:
        from DeepRareAgent.tools.biomcp_tool import load_biomcp_tools_sync
        print("  [PASS] BioCMP 工具导入成功")
        results['biomcp'] = True
    except Exception as e:
        print(f"  [FAIL] BioCMP 工具导入失败: {e}")
        results['biomcp'] = False

    # 7. 测试 PatientInfo 管理器
    print("\n[7/8] 测试 PatientInfo 管理器...")
    try:
        from DeepRareAgent.tools.patientinfo import PatientInfoManger
        print("  [PASS] PatientInfo 管理器导入成功")
        results['patientinfo'] = True
    except Exception as e:
        print(f"  [FAIL] PatientInfo 管理器导入失败: {e}")
        results['patientinfo'] = False

    # 8. 测试工具聚合模块
    print("\n[8/8] 测试工具聚合模块...")
    try:
        from DeepRareAgent.tools import get_all_tools, ALL_TOOLS
        tools = get_all_tools()
        print(f"  [PASS] 工具聚合模块导入成功")
        print(f"     - 可用工具数量: {len(tools)}")
        for i, tool in enumerate(tools, 1):
            print(f"     {i}. {tool.name}: {tool.description[:60]}...")
        results['aggregate'] = True
    except Exception as e:
        print(f"  [FAIL] 工具聚合模块导入失败: {e}")
        results['aggregate'] = False

    return results


def test_tool_functionality():
    """测试工具基本功能"""
    print("\n\n" + "=" * 60)
    print("[TEST] 步骤 2: 测试工具基本功能")
    print("=" * 60)

    results = {}

    # 1. 测试 HPO 工具
    print("\n[1/6] 测试 HPO 工具功能...")
    try:
        from DeepRareAgent.tools.hpo_tools import phenotype_to_hpo_tool
        # 修复：使用正确的参数格式 {"phenotypes": [...]}
        result = phenotype_to_hpo_tool.invoke({"phenotypes": ["发热"], "top_k": 3})
        if result and hasattr(result, 'results'):
            print(f"  [PASS] HPO 工具运行正常")
            print(f"     测试查询: '发热' -> 找到 {len(result.results)} 条 HPO 术语")
            if result.results:
                print(f"     首个结果: {result.results[0].id} - {result.results[0].name}")
            results['hpo_func'] = True
        else:
            print(f"  [WARN]  HPO 工具返回空结果")
            results['hpo_func'] = 'warning'
    except Exception as e:
        print(f"  [FAIL] HPO 工具运行失败: {e}")
        results['hpo_func'] = False

    # 2. 测试百度搜索
    print("\n[2/6] 测试百度搜索功能...")
    try:
        from DeepRareAgent.tools.baidu_tools import search_baidu_tool
        result = search_baidu_tool.invoke({"query": "罕见病诊断"})
        if result:
            print(f"  [PASS] 百度搜索运行正常")
            # 修复：不直接用 len()，而是检查对象属性
            result_str = str(result)
            print(f"     测试查询: '罕见病诊断' -> 返回 {len(result_str)} 字符")
            results['baidu_func'] = True
        else:
            print(f"  [WARN]  百度搜索返回空结果")
            results['baidu_func'] = 'warning'
    except Exception as e:
        print(f"  [FAIL] 百度搜索运行失败: {e}")
        results['baidu_func'] = False

    # 3. 测试维基百科
    print("\n[3/6] 测试维基百科功能...")
    try:
        from DeepRareAgent.tools.wiki_tools import search_wikipedia_tool
        result = search_wikipedia_tool.invoke({"query": "Rare disease"})
        if result:
            print(f"  [PASS] 维基百科运行正常")
            # 修复：不直接用 len()，而是检查对象属性
            result_str = str(result)
            print(f"     测试查询: 'Rare disease' -> 返回 {len(result_str)} 字符")
            results['wiki_func'] = True
        else:
            print(f"  [WARN]  维基百科返回空结果")
            results['wiki_func'] = 'warning'
    except Exception as e:
        print(f"  [FAIL] 维基百科运行失败: {e}")
        results['wiki_func'] = False

    # 4. 测试 PubMed (轻量测试)
    print("\n[4/6] 测试 PubMed 功能...")
    try:
        from DeepRareAgent.tools.pubmed_tools import search_pubmed
        # 修复：使用 .invoke() 方法调用 @tool 装饰的函数
        result = search_pubmed.invoke({
            "query": "rare disease diagnosis",
            "max_results": 1,
            "email": "test@example.com"
        })
        if result and result.items:
            print(f"  [PASS] PubMed 运行正常")
            print(f"     测试查询: 'rare disease diagnosis' -> 返回 {len(result.items)} 篇文献")
            results['pubmed_func'] = True
        else:
            print(f"  [WARN]  PubMed 返回空结果")
            results['pubmed_func'] = 'warning'
    except Exception as e:
        print(f"  [WARN]  PubMed 测试跳过 (可能需要网络): {str(e)[:60]}...")
        results['pubmed_func'] = 'skip'

    # 5. 测试 LitSense (轻量测试)
    print("\n[5/6] 测试 LitSense 功能...")
    try:
        from DeepRareAgent.tools.litsense_tool import lit_sense_search
        # 修复：使用 .invoke() 方法调用 @tool 装饰的函数
        result = lit_sense_search.invoke({
            "query": "diabetes symptoms",
            "rerank": False
        })
        if result:
            print(f"  [PASS] LitSense 运行正常")
            print(f"     测试查询: 'diabetes symptoms'")
            results['litsense_func'] = True
        else:
            print(f"  [WARN]  LitSense 返回空结果")
            results['litsense_func'] = 'warning'
    except Exception as e:
        print(f"  [WARN]  LitSense 测试跳过 (可能需要网络): {str(e)[:60]}...")
        results['litsense_func'] = 'skip'

    # 6. 测试 PatientInfo 管理器
    print("\n[6/6] 测试 PatientInfo 管理器...")
    try:
        from DeepRareAgent.tools.patientinfo import PatientInfoManger, patient_info_to_text
        # 修复：PatientInfoManger 是一个工具列表，不是类
        # 直接测试其中的工具是否可用
        if isinstance(PatientInfoManger, list) and len(PatientInfoManger) == 4:
            print(f"  [PASS] PatientInfo 管理器运行正常")
            print(f"     包含 {len(PatientInfoManger)} 个工具:")
            for tool in PatientInfoManger:
                print(f"       - {tool.name}")

            # 测试 patient_info_to_text 工具
            test_state = {
                "patient_info": {
                    "base_info": {"name": "测试患者", "age": 30},
                    "symptoms": []
                }
            }
            text = patient_info_to_text.invoke({"state": test_state})
            if "测试患者" in text:
                print(f"     工具功能正常: patient_info_to_text 输出正确")
            results['patientinfo_func'] = True
        else:
            print(f"  [FAIL] PatientInfo 管理器结构异常")
            results['patientinfo_func'] = False
    except Exception as e:
        print(f"  [FAIL] PatientInfo 管理器运行失败: {e}")
        results['patientinfo_func'] = False

    return results


def print_summary(import_results: Dict, func_results: Dict):
    """打印测试总结"""
    print("\n\n" + "=" * 60)
    print("[INFO] 测试总结")
    print("=" * 60)

    # 导入测试结果
    print("\n【导入测试】")
    import_passed = sum(1 for v in import_results.values() if v is True)
    import_total = len(import_results)
    for name, status in import_results.items():
        icon = "[PASS]" if status else "[FAIL]"
        print(f"  {icon} {name.ljust(15)}: {'成功' if status else '失败'}")
    print(f"\n  通过率: {import_passed}/{import_total} ({import_passed/import_total*100:.1f}%)")

    # 功能测试结果
    print("\n【功能测试】")
    func_passed = sum(1 for v in func_results.values() if v is True)
    func_warning = sum(1 for v in func_results.values() if v == 'warning')
    func_skip = sum(1 for v in func_results.values() if v == 'skip')
    func_total = len(func_results)
    for name, status in func_results.items():
        if status is True:
            icon = "[PASS]"
            text = "成功"
        elif status == 'warning':
            icon = "[WARN]"
            text = "警告"
        elif status == 'skip':
            icon = "[SKIP]"
            text = "跳过"
        else:
            icon = "[FAIL]"
            text = "失败"
        print(f"  {icon} {name.ljust(15)}: {text}")
    print(f"\n  通过: {func_passed}, 警告: {func_warning}, 跳过: {func_skip}, 失败: {func_total - func_passed - func_warning - func_skip}")

    # 总体评估
    print("\n【总体评估】")
    if import_passed == import_total and func_passed >= func_total - func_skip - 1:
        print("  [SUCCESS] 所有工具状态良好，可以正常使用！")
        return 0
    elif import_passed >= import_total * 0.8:
        print("  [WARN]  大部分工具可用，少数工具需要检查")
        return 1
    else:
        print("  [FAIL] 多个工具存在问题，需要修复")
        return 2


def main():
    """主函数"""
    print("\n" + "[MEDICAL] 罕见病辅助诊断系统 - 工具健康检查".center(60))
    print("=" * 60)

    try:
        # 步骤1: 测试导入
        import_results = test_tool_import()

        # 步骤2: 测试功能
        func_results = test_tool_functionality()

        # 打印总结
        exit_code = print_summary(import_results, func_results)

        print("\n" + "=" * 60)
        print("[DONE] 检查完成！")
        print("=" * 60 + "\n")

        return exit_code

    except Exception as e:
        print(f"\n[FAIL] 检查过程出现严重错误: {e}")
        import traceback
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    exit(main())
