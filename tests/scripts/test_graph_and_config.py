#!/usr/bin/env python
"""
测试 LangGraph 主图和配置是否正常
"""
from DeepRareAgent import graph, init_patient_info
from DeepRareAgent.config import settings


def test_graph_import():
    """测试 graph 导入"""
    print("\n" + "=" * 60)
    print("测试 1: Graph 导入")
    print("=" * 60)

    try:
        print(f"[PASS] Graph 类型: {type(graph)}")
        print(f"[PASS] Graph 节点: {list(graph.get_graph().nodes.keys())}")
        print("[PASS] Graph 导入成功")
        return True
    except Exception as e:
        print(f"[FAIL] Graph 导入失败: {e}")
        return False


def test_mdt_config():
    """测试 mdt_config.max_rounds 配置"""
    print("\n" + "=" * 60)
    print("测试 2: MDT 配置")
    print("=" * 60)

    try:
        has_mdt_config = hasattr(settings, 'mdt_config')
        print(f"[PASS] mdt_config 存在: {has_mdt_config}")

        if has_mdt_config:
            max_rounds = getattr(settings.mdt_config, 'max_rounds', None)
            print(f"[PASS] max_rounds 值: {max_rounds}")

            if max_rounds == 5:
                print("[PASS] max_rounds 配置正确 (期望值: 5)")
                return True
            else:
                print(f"[WARN] max_rounds 值不符合预期 (期望: 5, 实际: {max_rounds})")
                return False
        else:
            print("[FAIL] mdt_config 不存在")
            return False
    except Exception as e:
        print(f"[FAIL] MDT 配置读取失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graph_structure():
    """测试 graph 结构"""
    print("\n" + "=" * 60)
    print("测试 3: Graph 结构")
    print("=" * 60)

    try:
        graph_obj = graph.get_graph()
        nodes = list(graph_obj.nodes.keys())

        expected_nodes = ['__start__', 'prediagnosis', 'mdt_diagnosis', 'summary', '__end__']

        print(f"[PASS] 预期节点: {expected_nodes}")
        print(f"[PASS] 实际节点: {nodes}")

        # 检查关键节点是否存在
        missing_nodes = [n for n in expected_nodes if n not in nodes]
        if missing_nodes:
            print(f"[WARN] 缺少节点: {missing_nodes}")
            return False

        print("[PASS] Graph 结构正确")
        return True
    except Exception as e:
        print(f"[FAIL] Graph 结构检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("DeepRareAgent - Graph & Config 测试")
    print("=" * 60)

    results = []

    # 测试 1: Graph 导入
    results.append(("Graph 导入", test_graph_import()))

    # 测试 2: MDT 配置
    results.append(("MDT 配置", test_mdt_config()))

    # 测试 3: Graph 结构
    results.append(("Graph 结构", test_graph_structure()))

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for test_name, passed in results:
        status = "[PASS] 通过" if passed else "[FAIL] 失败"
        print(f"{status} - {test_name}")

    all_passed = all(r[1] for r in results)

    print("\n" + "=" * 60)
    if all_passed:
        print("[SUCCESS] 所有测试通过！")
        print("[PASS] 可以运行 uv run langgraph dev")
        print("[PASS] mdt_config.max_rounds = 5 配置可用")
    else:
        print("[WARN] 部分测试失败，请检查配置")
    print("=" * 60 + "\n")

    return all_passed


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
