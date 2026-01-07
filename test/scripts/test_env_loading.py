#!/usr/bin/env python
"""
测试环境变量加载
"""
import os
from pathlib import Path
from dotenv import load_dotenv


def test_env_file():
    """测试 .env 文件加载"""
    print("\n" + "=" * 60)
    print("测试环境变量加载")
    print("=" * 60)

    # 项目根目录
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"

    print(f"\n📁 .env 文件路径: {env_file}")
    print(f"[PASS] .env 文件存在: {env_file.exists()}")

    if not env_file.exists():
        print("[FAIL] .env 文件不存在")
        return False

    # 读取 .env 文件内容（不加载到环境变量）
    print(f"\n📄 .env 文件内容:")
    with open(env_file, 'r') as f:
        lines = f.readlines()
        for i, line in enumerate(lines, 1):
            if line.strip() and not line.startswith('#'):
                # 隐藏 API key 的值
                if '=' in line:
                    key, value = line.split('=', 1)
                    masked_value = value[:20] + "..." if len(value) > 20 else value
                    print(f"   {i}: {key}={masked_value.strip()}")
                else:
                    print(f"   {i}: {line.strip()}")

    # 加载 .env 文件
    print(f"\n🔄 加载 .env 文件...")
    load_dotenv(env_file, override=True)

    # 检查 LANGSMITH_API_KEY
    langsmith_key = os.environ.get('LANGSMITH_API_KEY')

    print(f"\n🔑 LANGSMITH_API_KEY 检查:")
    if langsmith_key:
        print(f"   [PASS] 已设置: {langsmith_key[:20]}...")
        print(f"   [PASS] 长度: {len(langsmith_key)} 字符")
        return True
    else:
        print(f"   [FAIL] 未设置")
        return False


def test_langgraph_json():
    """测试 langgraph.json 配置"""
    print("\n" + "=" * 60)
    print("测试 langgraph.json 配置")
    print("=" * 60)

    import json
    project_root = Path(__file__).parent.parent.parent
    langgraph_json = project_root / "langgraph.json"

    with open(langgraph_json, 'r') as f:
        config = json.load(f)

    env_file = config.get('env', 'NOT SET')
    print(f"\n📄 langgraph.json env 配置: {env_file}")

    if env_file == '.env':
        print(f"   [PASS] 正确指向 .env 文件")
        return True
    elif env_file == '.env.example':
        print(f"   [WARN] 指向 .env.example（应该改为 .env）")
        return False
    else:
        print(f"   [FAIL] 配置异常: {env_file}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("环境变量配置测试")
    print("=" * 60)

    results = []

    # 测试 1: langgraph.json 配置
    results.append(("langgraph.json 配置", test_langgraph_json()))

    # 测试 2: .env 文件加载
    results.append((".env 文件加载", test_env_file()))

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
        print("[SUCCESS] 环境变量配置正确！")
        print("[PASS] LANGSMITH_API_KEY 可以正常加载")
        print("[PASS] 可以运行 uv run langgraph dev")
    else:
        print("[WARN] 环境变量配置有问题，请检查")
    print("=" * 60 + "\n")

    return all_passed


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
