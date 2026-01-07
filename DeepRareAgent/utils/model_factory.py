# -*- coding: utf-8 -*-
"""
模型工厂模块
提供统一的 LLM 初始化接口，支持 OpenAI 和 Anthropic 两种 provider
"""
from typing import Any, Optional, Union
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic


def create_llm_from_config(
    cfg: Any,
    override_model: Optional[Union[ChatOpenAI, ChatAnthropic]] = None
) -> Union[ChatOpenAI, ChatAnthropic]:
    """
    根据配置对象动态创建 LLM 实例

    Args:
        cfg: 配置对象，应包含以下字段：
            - provider: str, "openai" 或 "anthropic"
            - model_name: str, 模型名称
            - api_key: str, API 密钥
            - base_url: str, API 端点（可选）
            - temperature: float, 温度参数
            - model_kwargs: 其他模型参数（可选）
        override_model: 可选的预构建模型实例，如果提供则直接返回

    Returns:
        ChatOpenAI 或 ChatAnthropic 实例

    Examples:
        # 使用 OpenAI 兼容接口（DeepSeek）
        config.provider = "openai"
        config.model_name = "deepseek-chat"
        config.base_url = "https://api.deepseek.com/v1"
        llm = create_llm_from_config(config)

        # 使用 Anthropic 兼容接口（GLM）
        config.provider = "anthropic"
        config.model_name = "glm-4-plus"
        config.base_url = "https://open.bigmodel.cn/api/paas/v4"
        llm = create_llm_from_config(config)
    """
    # 如果提供了预构建模型，直接返回
    if override_model is not None:
        return override_model

    # 提取模型参数（支持 ConfigObject 和普通字典）
    extra_params = {}
    if hasattr(cfg, 'model_kwargs'):
        model_kwargs = cfg.model_kwargs
        if hasattr(model_kwargs, 'to_dict'):
            extra_params = model_kwargs.to_dict()
        elif hasattr(model_kwargs, '__dict__'):
            extra_params = vars(model_kwargs)
        elif isinstance(model_kwargs, dict):
            extra_params = model_kwargs

    # 获取 provider，默认为 openai（向后兼容）
    provider = getattr(cfg, 'provider', 'openai').lower()

    # 根据 provider 创建对应的 LLM 实例
    if provider == 'anthropic':
        # 构建 ChatAnthropic 参数
        anthropic_params = {
            'model': cfg.model_name,  # 注意: ChatAnthropic 使用 'model' 而非 'model_name'
            'api_key': cfg.api_key,
            'temperature': cfg.temperature,
            **extra_params
        }

        # 如果配置中有 base_url，添加进去（支持 GLM 等兼容接口）
        if hasattr(cfg, 'base_url') and cfg.base_url:
            anthropic_params['base_url'] = cfg.base_url

        return ChatAnthropic(**anthropic_params)

    elif provider == 'openai':
        # 构建 ChatOpenAI 参数
        return ChatOpenAI(
            model_name=cfg.model_name,
            api_key=cfg.api_key,
            base_url=cfg.base_url,
            temperature=cfg.temperature,
            **extra_params
        )

    else:
        raise ValueError(
            f"不支持的 provider: '{provider}'。"
            f"请使用 'openai' 或 'anthropic'。"
        )


# 向后兼容的别名
make_llm = create_llm_from_config


# ========== 测试代码 ==========
if __name__ == "__main__":
    from DeepRareAgent.config import settings

    print(">>> 测试模型工厂...")

    # 测试 P01 配置
    try:
        p01_cfg = settings.pre_diagnosis_agent
        print(f"\n[P01 配置]")
        print(f"  Provider: {getattr(p01_cfg, 'provider', 'openai (默认)')}")
        print(f"  Model: {p01_cfg.model_name}")
        print(f"  Base URL: {p01_cfg.base_url}")

        llm = create_llm_from_config(p01_cfg)
        print(f"  创建成功: {type(llm).__name__}")
    except Exception as e:
        print(f"  [FAIL] 创建失败: {e}")

    # 测试 P02 配置
    try:
        p02_cfg = settings.deep_medical_research_agent
        p02_main = p02_cfg.main_agent
        print(f"\n[P02 Main Agent 配置]")
        print(f"  Provider: {getattr(p02_main, 'provider', 'openai (默认)')}")
        print(f"  Model: {p02_main.model_name}")
        print(f"  Base URL: {p02_main.base_url}")

        llm = create_llm_from_config(p02_main)
        print(f"  创建成功: {type(llm).__name__}")
    except Exception as e:
        print(f"  [FAIL] 创建失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n[PASS] 模型工厂测试完成")
