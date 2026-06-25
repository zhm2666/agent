"""
分析节点

复用原有 AnalysisNode 的核心逻辑，仅包装为 LangGraph 节点。
"""

import json
from typing import Any, Dict, List, Optional

from ..llms.factory import create_llm_client
from ..utils.config import load_config


def analysis_node(state: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    """
    基于当前状态中的识别结果、数据、图表信息生成分析结果。

    LangGraph 只会传 state；额外 kwargs 是为了兼容 _wrap 固定注入的参数。
    """
    try:
        llm_client = create_llm_client(load_config())
    except Exception:
        llm_client = _create_direct_llm_client()

    prediction_state = state.get("prediction_state", {})
    identification = prediction_state.get("product_identification", {})
    data_fetch = prediction_state.get("data_fetch", {})
    chart_generation = prediction_state.get("chart_generation", {})

    product_name = identification.get("product_name", "")
    product_code = identification.get("product_code", "")
    user_query = state.get("user_query", "")
    historical_data = data_fetch.get("historical_data", [])
    future_predictions = data_fetch.get("future_predictions", [])
    statistics = data_fetch.get("statistics", {})
    chart_url = chart_generation.get("chart_url", "")

    analysis_context = {
        "product": {"name": product_name, "code": product_code},
        "user_query": user_query,
        "data_summary": {
            "historical_period": f"最近{len(historical_data)}天",
            "data_points": len(historical_data),
            "future_predictions_days": len(future_predictions),
        },
        "historical_data": (
            historical_data[-30:] if len(historical_data) > 30 else historical_data
        ),
        "future_predictions": future_predictions,
        "statistics": statistics,
    }

    system_prompt = (
        "你是一个专业的销量预测分析师。你需要根据提供的数据进行深入分析，并给出专业的预测和建议。\n"
        "请输出详细的分析报告，格式不限，但应包含：\n"
        "1. 执行摘要\n"
        "2. 趋势分析\n"
        "3. 预测评估\n"
        "4. 未来预测解读\n"
        "5. 关键洞察（最多5条）\n"
        "6. 业务建议（最多5条）\n\n"
        f"图表访问地址：{chart_url}\n"
        f"数据如下：{json.dumps(analysis_context, ensure_ascii=False, indent=2)}"
    )

    try:
        analysis_result = llm_client.invoke(system_prompt, "")
        key_insights = _extract_keywords(analysis_result, ["洞察", "发现", "关键", "重点"])
        recommendations = _extract_keywords(
            analysis_result, ["建议", "措施", "行动", "方案", "优化"]
        )
        analyzed = True
    except Exception as exc:
        analysis_result = f"分析过程中出错: {exc}"
        key_insights = []
        recommendations = []
        analyzed = False

    return {
        "prediction_state": {
            **prediction_state,
            "step": "analysis",
            "analysis": {
                "analyzed": analyzed,
                "analysis_result": analysis_result,
                "key_insights": key_insights[:5],
                "recommendations": recommendations[:5],
            },
        }
    }


def _create_direct_llm_client():
    """直接创建 LLM 客户端，不依赖 PredictionAgent-Demo 模块。"""
    try:
        from openai import OpenAI
        import os

        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("未找到 API Key，请设置 DEEPSEEK_API_KEY 或 OPENAI_API_KEY 环境变量")

        if os.getenv("DEEPSEEK_API_KEY"):
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com"
            )
            model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        else:
            client = OpenAI(api_key=api_key)
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        return _OpenAIClient(client, model)
    except ImportError as exc:
        raise ImportError("请安装 openai 库: pip install openai") from exc


class _OpenAIClient:
    """简化版 LLM 客户端，仅实现 invoke 方法。"""

    def __init__(self, client, model: str):
        self.client = client
        self.model = model

    def invoke(self, system_prompt: str, user_prompt: str, **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4000),
        )
        return response.choices[0].message.content


def _extract_keywords(text: str, keywords: List[str]) -> List[str]:
    lines = text.split("\n")
    results = []
    for line in lines:
        line = line.strip()
        if any(keyword in line for keyword in keywords):
            results.append(line)
    return results[:5]
