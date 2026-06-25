"""
图表工具

把图表生成封装成 LangGraph 可调用工具接口。
"""

from typing import Any, Dict, List, Optional


def chart_tool(
    product_name: str,
    chart_type: str,
    historical_data: List[Dict[str, Any]],
    future_predictions: List[Dict[str, Any]],
    model_predictions: Optional[List[Dict[str, Any]]] = None,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    生成销量预测图表。

    该工具保留与原有 chart_helper / MCP 客户端的兼容能力；
    若未来接入 LangGraph ToolNode，可直接复用此签名。
    """
    model_predictions = model_predictions or []
    if not historical_data:
        return {
            "generated": False,
            "chart_type": chart_type,
            "chart_url": "",
            "chart_filepath": "",
            "chart_id": "",
            "error": "没有数据可绘制",
        }

    dates = [item["date"] for item in historical_data]
    actual_values = [item["actual_value"] for item in historical_data]

    if model_predictions:
        predicted_values = [item["predicted_value"] for item in model_predictions[: len(dates)]]
    else:
        predicted_values = [item.get("predicted_value", 0) for item in historical_data]

    while len(predicted_values) < len(dates):
        predicted_values.append(predicted_values[-1] if predicted_values else 0)

    future_dates = [item["date"] for item in future_predictions]
    future_pred_values = [item["predicted_value"] for item in future_predictions]

    return {
        "product_name": product_name,
        "chart_type": chart_type,
        "dates": dates,
        "actual_values": actual_values,
        "predicted_values": predicted_values,
        "future_dates": future_dates,
        "future_predictions": future_pred_values,
    }
