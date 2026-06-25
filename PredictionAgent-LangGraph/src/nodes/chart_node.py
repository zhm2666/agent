"""
图表生成节点

把原来 ChartNode 的逻辑收进一个 LangGraph 节点，
并通过 tool 层做统一调用，便于后续换成 MCP / Agent 工具。
"""

from typing import Any, Dict, List, Optional


def chart_node(
    state: Dict[str, Any],
    mcp_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    根据当前状态中的 data_fetch 数据生成图表。

    优先使用 mcp_client；
    若没有提供 mcp_client，则使用本地 quick_plot 兜底。
    """
    prediction_state = state.get("prediction_state", {})
    data_fetch = prediction_state.get("data_fetch", {})
    chart_generation = prediction_state.get("chart_generation", {})
    identification = prediction_state.get("product_identification", {})

    product_name = identification.get("product_name", "Unknown Product")
    chart_type = state.get("chart_type", "combined") or chart_generation.get(
        "chart_type", "combined"
    )
    historical_data = data_fetch.get("historical_data", [])
    future_predictions = data_fetch.get("future_predictions", [])
    model_predictions = data_fetch.get("model_predictions", [])

    if not historical_data:
        return {
            "prediction_state": {
                **prediction_state,
                "step": "chart_generation",
                "chart_generation": {
                    "generated": False,
                    "chart_type": chart_type,
                    "chart_url": "",
                    "chart_filepath": "",
                    "chart_id": "",
                    "error": "没有数据可绘制",
                },
            }
        }

    dates = [item["date"] for item in historical_data]
    actual_values = [item["actual_value"] for item in historical_data]

    if model_predictions:
        predicted_values = [
            item["predicted_value"] for item in model_predictions[: len(dates)]
        ]
    else:
        predicted_values = [item.get("predicted_value", 0) for item in historical_data]

    while len(predicted_values) < len(dates):
        predicted_values.append(predicted_values[-1] if predicted_values else 0)

    future_dates = [item["date"] for item in future_predictions]
    future_pred_values = [item["predicted_value"] for item in future_predictions]

    try:
        if mcp_client is not None:
            result = mcp_client.plot_sales_forecast(
                product_name=product_name,
                dates=dates,
                actual_values=actual_values,
                predicted_values=predicted_values,
                future_dates=future_dates,
                future_predictions=future_pred_values,
                chart_type=chart_type,
            )
            chart_result = _from_mcp_result(result)
        else:
            chart_result = _local_plot(
                product_name=product_name,
                chart_type=chart_type,
                dates=dates,
                actual_values=actual_values,
                predicted_values=predicted_values,
                future_dates=future_dates,
                future_pred_values=future_pred_values,
            )
    except Exception as exc:
        chart_result = {
            "generated": False,
            "chart_type": chart_type,
            "chart_url": "",
            "chart_filepath": "",
            "chart_id": "",
            "error": str(exc),
        }

    return {
        "prediction_state": {
            **prediction_state,
            "step": "chart_generation",
            "chart_generation": chart_result,
        }
    }


def _from_mcp_result(result: Any) -> Dict[str, Any]:
    return {
        "generated": getattr(result, "success", False),
        "chart_type": getattr(result, "chart_type", "") or "",
        "chart_url": getattr(result, "url", "") or "",
        "chart_filepath": getattr(result, "filepath", "") or "",
        "chart_id": getattr(result, "chart_id", "") or "",
        "error": getattr(result, "error", "") or "",
    }


def _local_plot(
    product_name: str,
    chart_type: str,
    dates: List[str],
    actual_values: List[float],
    predicted_values: List[float],
    future_dates: List[str],
    future_pred_values: List[float],
) -> Dict[str, Any]:
    try:
        from PredictionAgent_Demo.src.mcp import quick_plot
    except ImportError as exc:
        raise ImportError(
            "本地图表生成依赖 PredictionAgent-Demo 的 mcp 模块。"
        ) from exc

    result = quick_plot(
        product_name=product_name,
        dates=dates,
        actual_values=actual_values,
        predicted_values=predicted_values,
        future_dates=future_dates,
        future_predictions=future_pred_values,
        chart_type=chart_type,
    )
    return {
        "generated": result.get("success", False),
        "chart_type": result.get("chart_type", chart_type),
        "chart_url": result.get("url", ""),
        "chart_filepath": result.get("filepath", ""),
        "chart_id": result.get("chart_id", ""),
        "error": "" if result.get("success") else "生成失败",
    }
