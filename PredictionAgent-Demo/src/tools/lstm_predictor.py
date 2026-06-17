"""
模拟LSTM销量预测服务
用于生成模拟的LSTM预测数据
"""

import random
from datetime import date, timedelta
from typing import List, Dict, Any


class LSTMPredictor:
    """LSTM销量预测模拟器"""

    def __init__(self, model_path: str = None):
        """
        初始化预测器

        Args:
            model_path: 模型路径（这里仅作演示）
        """
        self.model_path = model_path

    def predict_future(
        self,
        historical_data: List[Dict[str, Any]],
        product_code: str,
        future_days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        使用LSTM模型预测未来销量

        Args:
            historical_data: 历史销量数据
            product_code: 产品代码
            future_days: 预测天数

        Returns:
            预测结果列表
        """
        predictions = []

        # 计算历史数据的基本统计
        if not historical_data:
            base_value = 100
        else:
            values = [d.get("actual_value", d.get("quantity", 100)) for d in historical_data]
            base_value = sum(values) / len(values)

        today = date.today()

        for i in range(1, future_days + 1):
            pred_date = today + timedelta(days=i)

            # 模拟LSTM预测（带季节性和趋势）
            trend = i * 0.5
            weekday_factor = 1.3 if pred_date.weekday() < 5 else 0.7

            # 添加一些随机波动
            noise = random.uniform(0.95, 1.05)

            predicted_value = max(0, int((base_value + trend) * weekday_factor * noise))

            # 置信度随时间递减
            confidence = max(0.6, 0.98 - i * 0.01)

            predictions.append({
                "product_code": product_code,
                "prediction_date": pred_date,
                "predicted_value": predicted_value,
                "confidence": round(confidence, 3),
                "model_type": "LSTM"
            })

        return predictions

    def evaluate_model(
        self,
        historical_data: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        评估模型性能

        Args:
            historical_data: 包含实际值和预测值的历史数据

        Returns:
            评估指标
        """
        if not historical_data:
            return {"mape": 0, "rmse": 0, "mae": 0}

        actual_values = []
        predicted_values = []

        for d in historical_data:
            actual = d.get("actual_value", d.get("quantity"))
            predicted = d.get("predicted_value")

            if actual is not None and predicted is not None:
                actual_values.append(actual)
                predicted_values.append(predicted)

        if not actual_values:
            return {"mape": 0, "rmse": 0, "mae": 0}

        # 计算MAPE
        mape = sum(abs(actual_values[i] - predicted_values[i]) / actual_values[i]
                   for i in range(len(actual_values)) if actual_values[i] > 0) / len(actual_values) * 100

        # 计算RMSE
        mse = sum((actual_values[i] - predicted_values[i]) ** 2
                  for i in range(len(actual_values))) / len(actual_values)
        rmse = mse ** 0.5

        # 计算MAE
        mae = sum(abs(actual_values[i] - predicted_values[i])
                  for i in range(len(actual_values))) / len(actual_values)

        return {
            "mape": round(mape, 2),
            "rmse": round(rmse, 2),
            "mae": round(mae, 2)
        }


def generate_lstm_predictions(
    product_code: str,
    start_date: date,
    end_date: date,
    base_value: int = 150
) -> List[Dict[str, Any]]:
    """
    生成LSTM预测数据（模拟）

    Args:
        product_code: 产品代码
        start_date: 开始日期
        end_date: 结束日期
        base_value: 基础销量值

    Returns:
        预测数据列表
    """
    predictions = []
    current = start_date
    trend = 0

    while current <= end_date:
        weekday_factor = 1.2 if current.weekday() < 5 else 0.8
        noise = random.uniform(0.9, 1.1)

        predicted = int(base_value * weekday_factor * noise + trend)

        predictions.append({
            "product_code": product_code,
            "prediction_date": current,
            "predicted_value": predicted,
            "confidence": round(random.uniform(0.85, 0.98), 2),
            "model_type": "LSTM"
        })

        trend += random.uniform(-2, 3)
        current += timedelta(days=1)

    return predictions
