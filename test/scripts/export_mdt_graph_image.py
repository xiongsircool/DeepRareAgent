"""
导出 MDT Graph 的可视化图像
"""
from pathlib import Path
from DeepRareAgent.p02_mdt.graph import create_mdt_graph


def export_graph_image():
    """导出 MDT Graph 为 PNG 图像"""

    print("=" * 60)
    print("MDT Graph 可视化导出")
    print("=" * 60)

    # 1. 创建图
    print("\n[1] 创建 MDT Graph...")
    mdt_graph = create_mdt_graph()
    print("✓ Graph 创建成功")

    # 2. 获取 Mermaid 格式
    print("\n[2] 获取 Mermaid 图...")
    try:
        mermaid_png = mdt_graph.get_graph().draw_mermaid_png()
        print("✓ Mermaid PNG 生成成功")
    except Exception as e:
        print(f"✗ Mermaid PNG 生成失败: {e}")
        print("\n尝试使用 ASCII 格式...")

        try:
            ascii_graph = mdt_graph.get_graph().draw_ascii()
            print("✓ ASCII 图生成成功：")
            print(ascii_graph)
        except Exception as e2:
            print(f"✗ ASCII 图生成失败: {e2}")

        mermaid_png = None

    # 3. 保存图像
    if mermaid_png:
        output_dir = Path(__file__).parent / "images"
        output_dir.mkdir(exist_ok=True)

        output_path = output_dir / "MDT_Graph.png"

        print(f"\n[3] 保存图像到: {output_path}")
        with open(output_path, "wb") as f:
            f.write(mermaid_png)

        print(f"✓ 图像已保存: {output_path}")
        print("\n" + "=" * 60)
        print("✅ 导出成功！")
        print("=" * 60)

        return str(output_path)
    else:
        print("\n" + "=" * 60)
        print("⚠️  PNG 导出失败，但你可以：")
        print("  1. 使用 LangGraph Studio 可视化")
        print("  2. 查看上面的 ASCII 图")
        print("  3. 手动绘制流程图")
        print("=" * 60)

        # 保存 Mermaid 文本
        output_dir = Path(__file__).parent / "images"
        output_dir.mkdir(exist_ok=True)
        mermaid_path = output_dir / "MDT_Graph.mermaid"

        try:
            mermaid_code = mdt_graph.get_graph().draw_mermaid()
            with open(mermaid_path, "w", encoding="utf-8") as f:
                f.write(mermaid_code)
            print(f"\n✓ Mermaid 代码已保存到: {mermaid_path}")
            print("  你可以在 https://mermaid.live 可视化")
        except Exception as e:
            print(f"\n✗ Mermaid 代码保存失败: {e}")

        return None


if __name__ == "__main__":
    export_graph_image()
