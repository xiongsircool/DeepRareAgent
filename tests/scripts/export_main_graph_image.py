"""
导出主图（完整诊断系统）的可视化图像
"""
from pathlib import Path
from DeepRareAgent.graph import create_main_graph


def export_main_graph_image():
    """导出主图为 PNG 图像"""

    print("=" * 60)
    print("主图可视化导出")
    print("=" * 60)

    # 1. 创建主图
    print("\n[1] 创建主图...")
    try:
        main_graph = create_main_graph()
        print("    主图创建成功")
    except Exception as e:
        print(f"    错误：主图创建失败 - {str(e)}")
        import traceback
        traceback.print_exc()
        return None

    # 2. 获取 Mermaid PNG
    print("\n[2] 生成可视化图像...")
    try:
        mermaid_png = main_graph.get_graph().draw_mermaid_png()
        print("    Mermaid PNG 生成成功")
    except Exception as e:
        print(f"    警告：PNG 生成失败 - {str(e)}")
        print("    尝试生成 ASCII 图...")

        try:
            ascii_graph = main_graph.get_graph().draw_ascii()
            print("\n    ASCII 图：")
            print(ascii_graph)
        except Exception as e2:
            print(f"    错误：ASCII 图生成也失败 - {str(e2)}")

        mermaid_png = None

    # 3. 保存图像
    if mermaid_png:
        output_dir = Path(__file__).parent / "images"
        output_dir.mkdir(exist_ok=True)

        output_path = output_dir / "Main_Graph_Complete.png"

        print(f"\n[3] 保存图像到: {output_path}")
        with open(output_path, "wb") as f:
            f.write(mermaid_png)

        print(f"    图像已保存")
        print("\n" + "=" * 60)
        print("导出成功！")
        print("=" * 60)
        print(f"\n生成的文件：")
        print(f"  - {output_path}")

        return str(output_path)
    else:
        print("\n" + "=" * 60)
        print("PNG 导出失败")
        print("=" * 60)

        # 保存 Mermaid 文本
        output_dir = Path(__file__).parent / "images"
        output_dir.mkdir(exist_ok=True)
        mermaid_path = output_dir / "Main_Graph_Complete.mermaid"

        try:
            mermaid_code = main_graph.get_graph().draw_mermaid()
            with open(mermaid_path, "w", encoding="utf-8") as f:
                f.write(mermaid_code)
            print(f"\nMermaid 代码已保存到: {mermaid_path}")
            print("你可以在 https://mermaid.live 可视化")
        except Exception as e:
            print(f"\nMermaid 代码保存失败: {e}")

        return None


if __name__ == "__main__":
    export_main_graph_image()
