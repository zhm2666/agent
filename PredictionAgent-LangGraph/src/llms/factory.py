"""
LLM 工厂

直接复用 PredictionAgent-Demo 里的 DeepSeek / OpenAI 实现，
不重复写客户端逻辑。
"""

from typing import Optional

from ..utils.config import Config, load_config


def create_llm_client(config: Optional[Config] = None):
    """
    按配置创建 LLM 客户端。

    为了少改原代码，这里做延迟导入；
    依赖关系仍然是 PredictionAgent-Demo 的 llms 模块。
    """
    try:
        from PredictionAgent_Demo.src.llms import DeepSeekLLM, OpenAILLM
    except ImportError as e:
        raise ImportError(
            "LangGraph 版本复用了 PredictionAgent-Demo 的 LLM 实现，"
            "请确保 PredictionAgent-Demo 在 Python 路径中可导入。"
        ) from e

    cfg = config or load_config()

    if cfg.default_llm_provider == "deepseek":
        return DeepSeekLLM(
            api_key=cfg.deepseek_api_key,
            model_name=cfg.deepseek_model,
        )

    if cfg.default_llm_provider == "openai":
        return OpenAILLM(
            api_key=cfg.openai_api_key,
            model_name=cfg.openai_model,
        )

    raise ValueError(f"不支持的 LLM 提供商: {cfg.default_llm_provider}")
