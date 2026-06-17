"""
数据获取节点
负责从数据库获取产品相关的销售数据和预测数据
"""

from typing import Dict, Any
from datetime import date, timedelta
from .base_node import BaseNode
from ..database.repository import SalesRepository
from ..database.models import ProductAnalysisData


class DataFetchNode(BaseNode):
    """数据获取节点"""

    def __init__(self, llm_client, repository: SalesRepository):
        super().__init__(llm_client, "DataFetch")
        self.repository = repository

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行数据获取

        Args:
            input_data: {
                "product_code": str,
                "product_name": str,
                "history_days": int (可选，默认90天),
                "future_days": int (可选，默认30天)
            }

        Returns:
            {
                "fetched": bool,
                "historical_data": List[Dict],
                "model_predictions": List[Dict],
                "future_predictions": List[Dict],
                "statistics": Dict,
                "error_message": str
            }
        """
        product_code = input_data.get("product_code", "")

        if not product_code:
            return {
                "fetched": False,
                "historical_data": [],
                "model_predictions": [],
                "future_predictions": [],
                "statistics": {},
                "error_message": "产品代码为空"
            }

        history_days = input_data.get("history_days", 90)
        future_days = input_data.get("future_days", 30)

        self.log_info(f"正在获取产品 {product_code} 的数据...")

        try:
            # 获取完整的分析数据
            analysis_data = self.repository.get_product_analysis_data(
                product_code=product_code,
                history_days=history_days,
                future_days=future_days
            )

            # 转换为可序列化的格式
            historical_data = self._convert_historical_data(analysis_data)
            model_predictions = self._convert_predictions(analysis_data.model_predictions)
            future_predictions = self._convert_predictions(analysis_data.future_predictions)

            # 获取统计信息
            statistics = self.repository.get_product_statistics(product_code, history_days)

            result = {
                "fetched": True,
                "historical_data": historical_data,
                "model_predictions": model_predictions,
                "future_predictions": future_predictions,
                "statistics": statistics,
                "error_message": ""
            }

            self.log_info(f"数据获取成功: 历史数据 {len(historical_data)} 条, "
                         f"模型预测 {len(model_predictions)} 条, "
                         f"未来预测 {len(future_predictions)} 条")

            return result

        except Exception as e:
            self.log_error(f"数据获取失败: {str(e)}")
            return {
                "fetched": False,
                "historical_data": [],
                "model_predictions": [],
                "future_predictions": [],
                "statistics": {},
                "error_message": str(e)
            }

    def _convert_historical_data(self, analysis_data: ProductAnalysisData) -> list:
        """转换历史数据"""
        result = []
        sorted_sales = sorted(analysis_data.sales_history, key=lambda x: x.sale_date)

        # 构建预测值映射
        prediction_map = {}
        for p in analysis_data.model_predictions:
            date_str = p.prediction_date.isoformat() if p.prediction_date else ""
            prediction_map[date_str] = p.predicted_value

        for sale in sorted_sales:
            date_str = sale.sale_date.isoformat() if sale.sale_date else ""
            result.append({
                "date": date_str,
                "actual_value": sale.quantity,
                "predicted_value": prediction_map.get(date_str, None)
            })

        return result

    def _convert_predictions(self, predictions: list) -> list:
        """转换预测数据"""
        return [
            {
                "date": p.prediction_date.isoformat() if p.prediction_date else "",
                "predicted_value": p.predicted_value,
                "confidence": p.confidence
            }
            for p in sorted(predictions, key=lambda x: x.prediction_date)
        ]

    def fetch_mock_data(self, product_code: str, product_name: str,
                        history_days: int = 90, future_days: int = 30) -> Dict[str, Any]:
        """
        生成模拟数据（用于测试或没有真实数据时）

        Args:
            product_code: 产品代码
            product_name: 产品名称
            history_days: 历史天数
            future_days: 未来天数

        Returns:
            模拟数据
        """
        import random
        from datetime import datetime, timedelta

        today = date.today()
        historical_data = []
        future_predictions = []

        # 生成历史数据（带趋势和季节性）
        base_value = random.randint(80, 200)
        for i in range(history_days):
            d = today - timedelta(days=history_days - i - 1)
            # 模拟趋势
            trend = i * 0.3
            # 模拟周季节性
            weekday_factor = 1.2 if d.weekday() < 5 else 0.8
            # 模拟随机波动
            noise = random.uniform(0.9, 1.1)
            actual = int((base_value + trend) * weekday_factor * noise)

            # 模拟模型预测（略有偏差）
            predicted = actual * random.uniform(0.95, 1.05)

            historical_data.append({
                "date": d.isoformat(),
                "actual_value": actual,
                "predicted_value": round(predicted, 2)
            })

        # 生成未来预测
        for i in range(1, future_days + 1):
            d = today + timedelta(days=i)
            weekday_factor = 1.2 if d.weekday() < 5 else 0.8
            predicted = int((base_value + trend + i * 0.3) * weekday_factor)

            future_predictions.append({
                "date": d.isoformat(),
                "predicted_value": predicted,
                "confidence": round(0.95 - i * 0.01, 2)  # 越远期置信度越低
            })

        # 计算统计信息
        actual_values = [d["actual_value"] for d in historical_data]
        avg_daily = sum(actual_values) / len(actual_values)

        mid = len(actual_values) // 2
        first_half_avg = sum(actual_values[:mid]) / mid
        second_half_avg = sum(actual_values[mid:]) / (len(actual_values) - mid)
        trend_change = ((second_half_avg - first_half_avg) / first_half_avg) * 100 if first_half_avg > 0 else 0

        return {
            "fetched": True,
            "historical_data": historical_data,
            "model_predictions": [],  # 模拟数据中没有单独的模型预测
            "future_predictions": future_predictions,
            "statistics": {
                "product_code": product_code,
                "period_days": history_days,
                "avg_daily_sales": round(avg_daily, 2),
                "trend_change_percent": round(trend_change, 2),
                "trend_direction": "up" if trend_change > 5 else ("down" if trend_change < -5 else "stable")
            },
            "error_message": ""
        }
