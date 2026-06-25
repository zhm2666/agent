"""
图表生成节点

把图表生成封装成 LangGraph 节点，
优先使用 MCP 客户端，否则使用本地 matplotlib 兜底。
"""

import os
import uuid
from typing import Any, Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime


def chart_node(
    state: Dict[str, Any],
    mcp_client: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    根据当前状态中的 data_fetch 数据生成图表。

    优先级：
    1. MCP 客户端（如果有）
    2. 本地 matplotlib 绘图
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
        predicted_values = [
            item.get("predicted_value", 0) for item in historical_data
        ]

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
            chart_result = {
                "generated": getattr(result, "success", False),
                "chart_type": getattr(result, "chart_type", "") or "",
                "chart_url": getattr(result, "url", "") or "",
                "chart_filepath": getattr(result, "filepath", "") or "",
                "chart_id": getattr(result, "chart_id", "") or "",
                "error": getattr(result, "error", "") or "",
            }
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


def _local_plot(
    product_name: str,
    chart_type: str,
    dates: List[str],
    actual_values: List[float],
    predicted_values: List[float],
    future_dates: List[str],
    future_pred_values: List[float],
) -> Dict[str, Any]:
    """使用本地 matplotlib 绘制图表。"""
    output_dir = os.getenv("CHART_OUTPUT_DIR", "output/charts")
    os.makedirs(output_dir, exist_ok=True)

    chart_id = uuid.uuid4().hex[:8]
    filename = f"sales_forecast_{chart_id}.png"
    filepath = os.path.join(output_dir, filename)

    try:
        all_dates = dates + future_dates
        all_dates_dt = [datetime.strptime(d, "%Y-%m-%d") for d in all_dates]
        hist_dates = all_dates_dt[: len(dates)]
        future_all_dates = all_dates_dt[len(dates) :]

        if chart_type == "bar":
            fig, ax = plt.subplots(figsize=(14, 6))
            x = range(len(all_dates))
            width = 0.35
            all_actual = actual_values + [0] * len(future_dates)
            all_predicted = predicted_values + future_pred_values

            ax.bar([i - width / 2 for i in x], all_actual, width,
                   label="实际销量", color="#2ecc71", alpha=0.8)
            ax.bar([i + width / 2 for i in x], all_predicted, width,
                   label="预测销量", color="#3498db", alpha=0.8)
            ax.axvline(x=len(dates) - 0.5, color="red", linestyle="--",
                       linewidth=2, label="预测分界线")
            ax.set_xlabel("日期", fontsize=12)
            ax.set_ylabel("销量", fontsize=12)
            ax.set_title(f"{product_name} - 销量预测分析", fontsize=14, fontweight="bold")
            ax.legend()
            ax.grid(axis="y", alpha=0.3)

        elif chart_type == "line":
            fig, ax = plt.subplots(figsize=(14, 6))
            ax.plot(hist_dates, actual_values, "-o", linewidth=2,
                    markersize=6, label="实际销量", color="#2ecc71")
            ax.plot(hist_dates, predicted_values, "--s", linewidth=2,
                    markersize=5, label="模型预测", color="#3498db")
            ax.plot(future_all_dates, future_pred_values, "-^", linewidth=2,
                    markersize=6, label="未来预测", color="#e74c3c")
            ax.axvline(x=hist_dates[-1], color="red", linestyle="--",
                       linewidth=2, label="预测分界线")
            ax.fill_between(future_all_dates,
                            [p * 0.9 for p in future_pred_values],
                            [p * 1.1 for p in future_pred_values],
                            alpha=0.2, color="#e74c3c",
                            label="预测置信区间(±10%)")
            ax.set_xlabel("日期", fontsize=12)
            ax.set_ylabel("销量", fontsize=12)
            ax.set_title(f"{product_name} - 销量预测分析", fontsize=14, fontweight="bold")
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            plt.xticks(rotation=45, ha="right")
            ax.legend(loc="upper left")
            ax.grid(True, alpha=0.3)

        else:
            # combined
            fig, (ax1, ax2) = plt.subplots(
                2, 1, figsize=(14, 10), gridspec_kw={"height_ratios": [2, 1]}
            )
            all_dates_list = dates + future_dates
            x = range(len(all_dates_list))

            width = 0.4
            ax1.bar([i - width / 2 for i in x[: len(dates)]], actual_values, width,
                    label="实际销量", color="#2ecc71", alpha=0.8)
            ax1.bar([i + width / 2 for i in x[: len(dates)]],
                    predicted_values[: len(dates)], width,
                    label="模型预测", color="#3498db", alpha=0.8)
            ax1.bar([i for i in x[len(dates) :]], future_pred_values, width,
                    label="未来预测", color="#e74c3c", alpha=0.8)
            ax1.axvline(x=len(dates) - 0.5, color="red", linestyle="--",
                        linewidth=2, label="预测分界线")
            ax1.set_ylabel("销量", fontsize=12)
            ax1.set_title(f"{product_name} - 销量预测综合分析", fontsize=14, fontweight="bold")
            ax1.legend(loc="upper left")
            ax1.grid(axis="y", alpha=0.3)

            errors = [
                actual_values[i] - predicted_values[i]
                for i in range(min(len(actual_values), len(predicted_values)))
            ]
            colors = ["#2ecc71" if e >= 0 else "#e74c3c" for e in errors]
            ax2.bar(range(len(errors)), errors, color=colors, alpha=0.8)
            ax2.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
            ax2.set_xlabel("时间序列", fontsize=12)
            ax2.set_ylabel("预测误差", fontsize=12)
            ax2.set_title("预测误差分析 (实际值 - 预测值)", fontsize=12)
            ax2.grid(axis="y", alpha=0.3)

            if actual_values and predicted_values:
                mape = sum(
                    abs(actual_values[i] - predicted_values[i]) / actual_values[i]
                    for i in range(len(actual_values))
                    if actual_values[i] > 0
                ) / len(actual_values) * 100
                ax2.text(0.02, 0.95, f"MAPE: {mape:.2f}%", transform=ax2.transAxes,
                         fontsize=10, verticalalignment="top",
                         bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))

        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches="tight")
        plt.close()

        return {
            "generated": True,
            "chart_type": chart_type,
            "chart_url": f"/charts/{filename}",
            "chart_filepath": filepath,
            "chart_id": chart_id,
            "error": "",
        }

    except Exception as exc:
        return {
            "generated": False,
            "chart_type": chart_type,
            "chart_url": "",
            "chart_filepath": "",
            "chart_id": chart_id,
            "error": str(exc),
        }
