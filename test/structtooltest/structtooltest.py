#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试配置文件中所有模型的结构化输出支持情况
使用 LangChain 官方推荐的 create_agent + ToolStrategy/ProviderStrategy 方式
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from pydantic import BaseModel, Field
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy, ProviderStrategy
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from DeepRareAgent.config import settings


class ContactInfo(BaseModel):
    """测试用联系人信息结构"""
    answer: str = Field(description="问题的答案")
    confidence: float = Field(description="置信度 0-1", ge=0, le=1)


def get_unique_models():
    """从配置中提取所有不重复的模型配置"""
    models = []
    seen = set()

    # P01
    key = (settings.pre_diagnosis_agent.provider,
           settings.pre_diagnosis_agent.model_name,
           settings.pre_diagnosis_agent.base_url)
    if key not in seen:
        seen.add(key)
        models.append(("P01", settings.pre_diagnosis_agent))

    # P02 main
    key = (settings.deep_medical_research_agent.main_agent.provider,
           settings.deep_medical_research_agent.main_agent.model_name,
           settings.deep_medical_research_agent.main_agent.base_url)
    if key not in seen:
        seen.add(key)
        models.append(("P02-main", settings.deep_medical_research_agent.main_agent))

    # P02 sub
    key = (settings.deep_medical_research_agent.sub_agent.provider,
           settings.deep_medical_research_agent.sub_agent.model_name,
           settings.deep_medical_research_agent.sub_agent.base_url)
    if key not in seen:
        seen.add(key)
        models.append(("P02-sub", settings.deep_medical_research_agent.sub_agent))

    return models


def test_model(name, config):
    """测试单个模型"""
    print(f"\n{'='*60}")
    print(f"测试 {name}")
    print(f"  Provider: {config.provider}")
    print(f"  Model: {config.model_name}")
    print(f"  API: {config.base_url}")
    print('='*60)

    results = {"tool_strategy": False, "provider_strategy": False}

    # 初始化 LLM
    if config.provider == "openai":
        llm = ChatOpenAI(
            model=config.model_name,
            base_url=config.base_url,
            api_key=config.api_key,
            temperature=0.1,
        )
    else:  # anthropic
        llm = ChatAnthropic(
            model=config.model_name,
            base_url=config.base_url,
            api_key=config.api_key,
            temperature=0.1,
        )

    test_question = "1+1等于几？请给出答案和你的置信度"

    # 方式1: ToolStrategy (通过工具调用实现结构化输出)
    print("\n[方式1] ToolStrategy (Tool Calling)...", end=" ")
    try:
        agent = create_agent(
            model=llm,
            tools=[],  # 不需要额外工具
            response_format=ToolStrategy(ContactInfo)
        )

        result = agent.invoke({
            "messages": [{"role": "user", "content": test_question}]
        })

        structured = result.get("structured_response")
        if structured:
            print(f"✅ 成功 - {structured.answer} (置信度: {structured.confidence})")
            results["tool_strategy"] = True
        else:
            print("❌ 失败 - 未返回 structured_response")
    except Exception as e:
        print(f"❌ 失败 - {type(e).__name__}: {str(e)[:50]}")

    # 方式2: ProviderStrategy (使用模型原生结构化输出)
    print("[方式2] ProviderStrategy (Native)...", end=" ")
    try:
        agent = create_agent(
            model=llm,
            tools=[],
            response_format=ProviderStrategy(ContactInfo)
        )

        result = agent.invoke({
            "messages": [{"role": "user", "content": test_question}]
        })

        structured = result.get("structured_response")
        if structured:
            print(f"✅ 成功 - {structured.answer} (置信度: {structured.confidence})")
            results["provider_strategy"] = True
        else:
            print("❌ 失败 - 未返回 structured_response")
    except Exception as e:
        print(f"❌ 失败 - {type(e).__name__}: {str(e)[:50]}")

    return results


def main():
    print("\n🔬 LangChain Agents 结构化输出策略测试")
    print("使用官方推荐的 create_agent + ToolStrategy/ProviderStrategy\n")

    models = get_unique_models()
    print(f"找到 {len(models)} 个不重复的模型配置\n")

    all_results = {}
    for name, config in models:
        all_results[name] = test_model(name, config)

    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    print(f"{'模型':<15} {'ToolStrategy':<15} {'ProviderStrategy':<15}")
    print("-"*60)
    for name, results in all_results.items():
        ts = "✅ 支持" if results["tool_strategy"] else "❌ 不支持"
        ps = "✅ 支持" if results["provider_strategy"] else "❌ 不支持"
        print(f"{name:<15} {ts:<15} {ps:<15}")
    print("="*60)

    print("\n说明:")
    print("- ToolStrategy: 通过工具调用实现结构化输出（兼容性最好）")
    print("- ProviderStrategy: 使用模型原生结构化输出能力（如 OpenAI JSON mode）")


if __name__ == "__main__":
    main()
