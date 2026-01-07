#!/usr/bin/env python
"""
测试路由逻辑是否正确
"""
from DeepRareAgent import graph


def test_routing():
    """测试路由逻辑"""
    print("\n" + "=" * 60)
    print("测试路由逻辑")
    print("=" * 60)

    graph_obj = graph.get_graph()

    # 获取所有边
    edges = graph_obj.edges

    print(f"\n[INFO] Graph 结构:")
    print(f"   节点: {list(graph_obj.nodes.keys())}")

    # 检查 prediagnosis 节点的条件边
    print(f"\n🔀 prediagnosis 节点的条件边:")

    # 查找从 prediagnosis 出发的边
    prediag_edges = []
    for edge in edges:
        if hasattr(edge, 'source') and edge.source == 'prediagnosis':
            prediag_edges.append(edge)

    if prediag_edges:
        for edge in prediag_edges:
            print(f"   - {edge}")
    else:
        print("   找不到条件边信息（这是正常的，边信息在编译后可能不可见）")

    # 测试路由函数
    from DeepRareAgent.graph import route_after_prediagnosis

    print(f"\n[TEST] 测试路由函数:")

    # 测试 1: start_diagnosis=False
    state_false = {"start_diagnosis": False}
    result_false = route_after_prediagnosis(state_false)
    print(f"\n   测试 1: start_diagnosis=False")
    print(f"      返回: {result_false}")
    if result_false == "__end__":
        print(f"      [PASS] 正确：返回 __end__（结束对话）")
    else:
        print(f"      [FAIL] 错误：应该返回 __end__，实际返回 {result_false}")

    # 测试 2: start_diagnosis=True
    state_true = {"start_diagnosis": True}
    result_true = route_after_prediagnosis(state_true)
    print(f"\n   测试 2: start_diagnosis=True")
    print(f"      返回: {result_true}")
    if result_true == "mdt_diagnosis":
        print(f"      [PASS] 正确：返回 mdt_diagnosis（进入会诊）")
    else:
        print(f"      [FAIL] 错误：应该返回 mdt_diagnosis，实际返回 {result_true}")

    # 测试 3: start_diagnosis 不存在（默认 False）
    state_none = {}
    result_none = route_after_prediagnosis(state_none)
    print(f"\n   测试 3: start_diagnosis 不存在")
    print(f"      返回: {result_none}")
    if result_none == "__end__":
        print(f"      [PASS] 正确：返回 __end__（默认结束对话）")
    else:
        print(f"      [FAIL] 错误：应该返回 __end__，实际返回 {result_none}")

    # 检查是否所有测试通过
    all_passed = (
        result_false == "__end__" and
        result_true == "mdt_diagnosis" and
        result_none == "__end__"
    )

    return all_passed


def main():
    """运行测试"""
    print("\n" + "=" * 60)
    print("路由逻辑测试")
    print("=" * 60)

    success = test_routing()

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    if success:
        print("[PASS] 所有路由测试通过")
        print("\n[PASS] 正确行为：")
        print("   - start_diagnosis=False → 结束对话，等待用户下次输入")
        print("   - start_diagnosis=True → 进入 MDT 会诊")
        print("\n💡 对话流程：")
        print("   1. 用户发送消息")
        print("   2. Prediagnosis agent 回复（添加到 messages）")
        print("   3. 如果未准备好诊断 → 返回 END")
        print("   4. 用户看到回复，可以继续输入")
        print("   5. 下次调用：messages = [历史对话] + [新的用户输入]")
    else:
        print("[FAIL] 路由测试失败")

    print("=" * 60 + "\n")

    return success


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
