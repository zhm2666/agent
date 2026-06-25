"""
数据获取节点

复用 PredictionAgent-Demo 的仓库查询与模拟数据生成逻辑。
"""

from typing import Any, Dict, List, Optional
from datetime import date, timedelta


def data_fetch_node(
    state: Dict[str, Any],
    repository: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    获取产品分析数据，并更新 data_fetch 子状态。

    - 若 repository 可用，则查询真实数据；
    - 否则使用模拟数据，保证流程仍可继续执行。
    """
    product_code = (
        state.get("prediction_state", {})
        .get("product_identification", {})
        .get("product_code", "")
    )
    product_name = (
        state.get("prediction_state", {})
        .get("product_identification", {})
        .get("product_name", "")
    )

    if not product_code:
        return {
            "prediction_state": {
                **state.get("prediction_state", {}),
                "step": "data_fetch",
                "data_fetch": {
                    "fetched": False,
                    "historical_data": [],
                    "model_predictions": [],
                    "future_predictions": [],
                    "statistics": {},
                    "error_message": "产品代码为空",
                },
            }
        }

    history_days = 90
    future_days = 30

    if repository:
        try:
            analysis_data = repository.get_product_analysis_data(
                product_code=product_code,
                history_days=history_days,
                future_days=future_days,
            )
            historical_data = _convert_historical_data(analysis_data)
            model_predictions = _convert_predictions(analysis_data.model_predictions)
            future_predictions = _convert_predictions(analysis_data.future_predictions)
            statistics = repository.get_product_statistics(product_code, history_days)
            return {
                "prediction_state": {
                    **state.get("prediction_state", {}),
                    "step": "data_fetch",
                    "data_fetch": {
                        "fetched": True,
                        "historical_data": historical_data,
                        "model_predictions": model_predictions,
                        "future_predictions": future_predictions,
                        "statistics": statistics,
                        "error_message": "",
                    },
                }
            }
        except Exception as exc:
            return _build_mock_data_fetch_state(state, product_code, product_name, str(exc))

    return _build_mock_data_fetch_state(state, product_code, product_name)


def _build_mock_data_fetch_state(
    state: Dict[str, Any],
    product_code: str,
    product_name: str,
    error_message: str = "",
) -> Dict[str, Any]:
    import random

    today = date.today()
    history_days = 90
    future_days = 30

    base_value = random.randint(80, 200)
    historical_data = []
    trend = 0.0
    for i in range(history_days):
        current_date = today - timedelta(days=history_days - i - 1)
        trend = i * 0.3
        weekday_factor = 1.2 if current_date.weekday() < 5 else 0.8
        noise = random.uniform(0.9, 1.1)
        actual = int((base_value + trend) * weekday_factor * noise)
        predicted = actual * random.uniform(0.95, 1.05)
        historical_data.append(
            {
                "date": current_date.isoformat(),
                "actual_value": actual,
                "predicted_value": round(predicted, 2),
            }
        )

    future_predictions = []
    for i in range(1, future_days + 1):
        current_date = today + timedelta(days=i)
        weekday_factor = 1.2 if current_date.weekday() < 5 else 0.8
        predicted = int((base_value + trend + i * 0.3) * weekday_factor)
        future_predictions.append(
            {
                "date": current_date.isoformat(),
                "predicted_value": predicted,
                "confidence": round(0.95 - i * 0.01, 2),
            }
        )

    actual_values = [d["actual_value"] for d in historical_data]
    avg_daily = sum(actual_values) / len(actual_values)
    mid = len(actual_values) // 2
    first_half_avg = sum(actual_values[:mid]) / mid
    second_half_avg = sum(actual_values[mid:]) / (len(actual_values) - mid)
    trend_change = (
        ((second_half_avg - first_half_avg) / first_half_avg) * 100
        if first_half_avg > 0
        else 0
    )

    data_fetch = {
        "fetched": True,
        "historical_data": historical_data,
        "model_predictions": [],
        "future_predictions": future_predictions,
        "statistics": {
            "product_code": product_code,
            "period_days": history_days,
            "avg_daily_sales": round(avg_daily, 2),
            "trend_change_percent": round(trend_change, 2),
            "trend_direction": (
                "up" if trend_change > 5 else ("down" if trend_change < -5 else "stable")
            ),
        },
        "error_message": error_message or "",
    }

    return {
        "prediction_state": {
            **state.get("prediction_state", {}),
            "step": "data_fetch",
            "data_fetch": data_fetch,
        }
    }


def _convert_historical_data(analysis_data: Any) -> List[Dict[str, Any]]:
    sorted_sales = sorted(
        getattr(analysis_data, "sales_history", []),
        key=lambda item: getattr(item, "sale_date", None),
    )
    prediction_map = {}
    for prediction in getattr(analysis_data, "model_predictions", []):
        date_str = (
            prediction.prediction_date.isoformat()
            if hasattr(prediction, "prediction_date") and prediction.prediction_date
            else ""
        )
        prediction_map[date_str] = getattr(prediction, "predicted_value", None)

    result = []
    for sale in sorted_sales:
        date_str = (
            sale.sale_date.isoformat()
            if hasattr(sale, "sale_date") and sale.sale_date
            else ""
        )
        result.append(
            {
                "date": date_str,
                "actual_value": getattr(sale, "quantity", 0),
                "predicted_value": prediction_map.get(date_str),
            }
        )
    return result


def _convert_predictions(predictions: List[Any]) -> List[Dict[str, Any]]:
    return [
        {
            "date": (
                item.prediction_date.isoformat()
                if hasattr(item, "prediction_date") and item.prediction_date
                else ""
            ),
            "predicted_value": getattr(item, "predicted_value", 0),
            "confidence": getattr(item, "confidence", 0.0),
        }
        for item in sorted(
            predictions,
            key=lambda item: getattr(item, "prediction_date", None),
        )
    ]
