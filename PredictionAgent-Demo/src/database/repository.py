"""
销售数据仓库
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from .connection import DatabaseConnection
from .models import Product, SalesData, PredictionResult, ProductAnalysisData
import logging

logger = logging.getLogger(__name__)


class SalesRepository:
    """销售数据仓库"""

    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection

    def get_all_products(self) -> List[Product]:
        """获取所有产品"""
        query = "SELECT * FROM products ORDER BY product_name"
        results = self.db.execute_query(query)
        return [Product.from_dict(row) for row in results]

    def get_product_by_code(self, product_code: str) -> Optional[Product]:
        """根据产品代码获取产品"""
        query = "SELECT * FROM products WHERE product_code = %s"
        results = self.db.execute_query(query, (product_code,))
        if results:
            return Product.from_dict(results[0])
        return None

    def search_products(self, keyword: str) -> List[Product]:
        """搜索产品"""
        query = """
            SELECT * FROM products
            WHERE product_name LIKE %s OR product_code LIKE %s OR category LIKE %s
            ORDER BY product_name
        """
        pattern = f"%{keyword}%"
        results = self.db.execute_query(query, (pattern, pattern, pattern))
        return [Product.from_dict(row) for row in results]

    def get_sales_data(
        self,
        product_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        region: Optional[str] = None
    ) -> List[SalesData]:
        """获取销售数据"""
        query = "SELECT * FROM sales_data WHERE product_code = %s"
        params = [product_code]

        if start_date:
            query += " AND sale_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND sale_date <= %s"
            params.append(end_date)
        if region:
            query += " AND region = %s"
            params.append(region)

        query += " ORDER BY sale_date"

        results = self.db.execute_query(query, tuple(params))
        return [SalesData.from_dict(row) for row in results]

    def get_aggregated_sales(
        self,
        product_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """获取按日期聚合的销售数据"""
        query = """
            SELECT
                product_code,
                sale_date,
                SUM(quantity) as total_quantity,
                AVG(price) as avg_price
            FROM sales_data
            WHERE product_code = %s
        """
        params = [product_code]

        if start_date:
            query += " AND sale_date >= %s"
            params.append(start_date)
        if end_date:
            query += " AND sale_date <= %s"
            params.append(end_date)

        query += " GROUP BY product_code, sale_date ORDER BY sale_date"

        return self.db.execute_query(query, tuple(params))

    def get_prediction_results(
        self,
        product_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        is_future: bool = False
    ) -> List[PredictionResult]:
        """获取预测结果"""
        query = "SELECT * FROM prediction_results WHERE product_code = %s"
        params = [product_code]

        today = date.today()

        if is_future:
            query += " AND prediction_date > %s"
            params.append(today)
        else:
            if start_date:
                query += " AND prediction_date >= %s"
                params.append(start_date)
            if end_date:
                query += " AND prediction_date <= %s"
                params.append(end_date)

        query += " ORDER BY prediction_date"

        results = self.db.execute_query(query, tuple(params))
        return [PredictionResult.from_dict(row) for row in results]

    def get_product_analysis_data(
        self,
        product_code: str,
        history_days: int = 90,
        future_days: int = 30
    ) -> ProductAnalysisData:
        """
        获取产品的完整分析数据

        Args:
            product_code: 产品代码
            history_days: 历史数据天数
            future_days: 未来预测天数

        Returns:
            ProductAnalysisData
        """
        # 获取产品信息
        product = self.get_product_by_code(product_code)
        if not product:
            raise ValueError(f"产品不存在: {product_code}")

        # 计算日期范围
        today = date.today()
        start_date = today - timedelta(days=history_days)

        # 获取历史销售数据
        sales_history = self.get_sales_data(product_code, start_date, today)

        # 获取模型预测结果（历史期间）
        model_predictions = self.get_prediction_results(
            product_code, start_date, today, is_future=False
        )

        # 获取未来预测
        future_predictions = self.get_prediction_results(
            product_code, None, None, is_future=True
        )

        return ProductAnalysisData(
            product=product,
            sales_history=sales_history,
            model_predictions=model_predictions,
            future_predictions=future_predictions
        )

    def add_product(self, product: Product) -> int:
        """添加产品"""
        query = """
            INSERT INTO products (product_code, product_name, category, description)
            VALUES (%s, %s, %s, %s)
        """
        return self.db.execute_update(
            query,
            (product.product_code, product.product_name, product.category, product.description)
        )

    def add_sales_data(self, sales_data: SalesData) -> int:
        """添加销售数据"""
        query = """
            INSERT INTO sales_data (product_code, sale_date, quantity, price, region)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = VALUES(quantity), price = VALUES(price)
        """
        return self.db.execute_update(
            query,
            (
                sales_data.product_code,
                sales_data.sale_date,
                sales_data.quantity,
                sales_data.price,
                sales_data.region
            )
        )

    def add_prediction_result(self, prediction: PredictionResult) -> int:
        """添加预测结果"""
        query = """
            INSERT INTO prediction_results
            (product_code, prediction_date, predicted_value, confidence, model_type)
            VALUES (%s, %s, %s, %s, %s)
        """
        return self.db.execute_update(
            query,
            (
                prediction.product_code,
                prediction.prediction_date,
                prediction.predicted_value,
                prediction.confidence,
                prediction.model_type
            )
        )

    def batch_add_sales_data(self, sales_list: List[SalesData]) -> int:
        """批量添加销售数据"""
        query = """
            INSERT INTO sales_data (product_code, sale_date, quantity, price, region)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE quantity = VALUES(quantity)
        """
        data = [
            (s.product_code, s.sale_date, s.quantity, s.price, s.region)
            for s in sales_list
        ]
        return self.db.execute_many(query, data)

    def get_product_statistics(self, product_code: str, days: int = 30) -> Dict[str, Any]:
        """获取产品统计信息"""
        today = date.today()
        start_date = today - timedelta(days=days)

        # 日均销量
        avg_query = """
            SELECT AVG(daily_total) as avg_daily_sales
            FROM (
                SELECT SUM(quantity) as daily_total
                FROM sales_data
                WHERE product_code = %s AND sale_date >= %s
                GROUP BY sale_date
            ) as daily_sales
        """
        avg_result = self.db.execute_query(avg_query, (product_code, start_date))
        avg_daily = avg_result[0]["avg_daily_sales"] if avg_result else 0

        # 趋势（与上期对比）
        mid_date = start_date + timedelta(days=days // 2)
        trend_query = """
            SELECT
                SUM(CASE WHEN sale_date < %s THEN quantity ELSE 0 END) as first_half,
                SUM(CASE WHEN sale_date >= %s THEN quantity ELSE 0 END) as second_half
            FROM sales_data
            WHERE product_code = %s AND sale_date >= %s
        """
        trend_result = self.db.execute_query(
            trend_query, (mid_date, mid_date, product_code, start_date)
        )

        trend_change = 0
        if trend_result:
            first = trend_result[0]["first_half"] or 0
            second = trend_result[0]["second_half"] or 0
            if first > 0:
                trend_change = ((second - first) / first) * 100

        return {
            "product_code": product_code,
            "period_days": days,
            "avg_daily_sales": round(avg_daily, 2) if avg_daily else 0,
            "trend_change_percent": round(trend_change, 2),
            "trend_direction": "up" if trend_change > 5 else ("down" if trend_change < -5 else "stable")
        }
