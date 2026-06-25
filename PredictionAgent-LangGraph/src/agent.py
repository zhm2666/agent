"""
LangGraph 版预测分析 Agent

对外保留类似 PredictionAgent.analyze(query=...) 的调用方式，
但底层已经改成 LangGraph StateGraph 执行。
"""

import os
from typing import Any, Dict, Optional

from .graph.builder import create_prediction_graph
from .state.prediction_state import AgentState
from .utils.config import Config, load_config


class PredictionAgent:
    """
    LangGraph 版预测分析 Agent

    与原版最大的区别：
    - analyze() 不再手动顺序调用各 step；
    - 而是往图里写入初始状态，由 LangGraph 按图执行。
    """

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or load_config()
        self._initialize_dependencies()
        self.app = create_prediction_graph(
            repository=self.repository,
            mcp_client=self.mcp_client,
        )
        os.makedirs(self.config.chart_output_dir, exist_ok=True)
        os.makedirs(self.config.output_dir, exist_ok=True)

    def _initialize_dependencies(self) -> None:
        self.repository = None
        self.mcp_client = None

        db_config = {
            "host": self.config.mysql_host,
            "port": self.config.mysql_port,
            "user": self.config.mysql_user,
            "password": self.config.mysql_password,
            "database": self.config.mysql_database,
        }

        try:
            import mysql.connector

            connection = mysql.connector.connect(**db_config)
            connection.close()
            self.repository = _DatabaseRepository(db_config)
        except Exception:
            self.repository = None

    def analyze(
        self,
        query: str,
        chart_type: str = "combined",
        use_mock_data: bool = False,
        product_code: Optional[str] = None,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        执行预测分析

        Args:
            query: 用户问题
            chart_type: 图表类型
            use_mock_data: 是否强制使用模拟数据
            product_code: 直接指定产品代码
            thread_id: LangGraph 线程 ID，用于多轮对话续跑
            user_id: 业务用户 ID，用于审计/统计
            session_id: 应用层会话 ID，可选透传到状态

        Returns:
            分析结果字典
        """
        repository = None if use_mock_data else self.repository

        initial_state: AgentState = {
            "user_query": query,
            "chart_type": chart_type,
            "prediction_state": {
                "step": "product_identification",
                "product_identification": self._initial_identification(product_code),
                "data_fetch": self._initial_data_fetch(),
                "chart_generation": self._initial_chart_generation(),
                "analysis": self._initial_analysis(),
            },
            "reflection": self._initial_reflection(),
            "is_completed": False,
            "error_message": "",
            "session_id": session_id,
            "user_id": user_id,
            "created_at": self._now_iso(),
            "updated_at": self._now_iso(),
        }

        config = {
            "configurable": {
                "thread_id": thread_id or f"prediction-{id(initial_state)}",
                "user_id": user_id,
            }
        }

        try:
            final_state = self.app.invoke(initial_state, config)
            return self._build_response(final_state)
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
                "state": self._serialize_state(initial_state),
            }

    def stream_analysis(
        self,
        query: str,
        chart_type: str = "combined",
        use_mock_data: bool = False,
        product_code: Optional[str] = None,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        """
        流式执行分析，便于做进度展示。
        """
        repository = None if use_mock_data else self.repository

        initial_state: AgentState = {
            "user_query": query,
            "chart_type": chart_type,
            "prediction_state": {
                "step": "product_identification",
                "product_identification": self._initial_identification(product_code),
                "data_fetch": self._initial_data_fetch(),
                "chart_generation": self._initial_chart_generation(),
                "analysis": self._initial_analysis(),
            },
            "reflection": self._initial_reflection(),
            "is_completed": False,
            "error_message": "",
            "session_id": session_id,
            "user_id": user_id,
            "created_at": self._now_iso(),
            "updated_at": self._now_iso(),
        }

        config = {
            "configurable": {
                "thread_id": thread_id or f"prediction-{id(initial_state)}",
                "user_id": user_id,
            }
        }

        for event in self.app.stream(initial_state, config):
            yield event

    def get_state(self, thread_id: str) -> Optional[Dict[str, Any]]:
        config = {"configurable": {"thread_id": thread_id}}
        try:
            state = self.app.get_state(config)
            return state.values if hasattr(state, "values") else dict(state)
        except Exception:
            return None

    def _initial_identification(self, product_code: Optional[str]) -> Dict[str, Any]:
        return {
            "identified": bool(product_code),
            "product_code": product_code or "",
            "product_name": "",
            "confidence": 1.0 if product_code else 0.0,
            "reasoning": "直接指定产品代码" if product_code else "",
            "alternatives": [],
        }

    def _initial_data_fetch(self) -> Dict[str, Any]:
        return {
            "fetched": False,
            "historical_data": [],
            "model_predictions": [],
            "future_predictions": [],
            "statistics": {},
            "error_message": "",
        }

    def _initial_chart_generation(self) -> Dict[str, Any]:
        return {
            "generated": False,
            "chart_type": "",
            "chart_url": "",
            "chart_filepath": "",
            "chart_id": "",
            "error": "",
        }

    def _initial_analysis(self) -> Dict[str, Any]:
        return {
            "analyzed": False,
            "analysis_result": "",
            "key_insights": [],
            "recommendations": [],
        }

    def _initial_reflection(self) -> Dict[str, Any]:
        return {
            "enabled": True,
            "reflection_count": 0,
            "max_reflections": 5,
            "current_validation": None,
            "retry_strategy": {
                "max_retries": 3,
                "current_attempts": 0,
                "backoff_multiplier": 2.0,
                "initial_delay": 1.0,
                "step_configs": {
                    "product_identification": {
                        "max_retries": 2,
                        "fallback_action": "ask_user",
                        "validate_after": True,
                    },
                    "data_fetch": {
                        "max_retries": 3,
                        "fallback_action": "use_fallback",
                        "validate_after": True,
                    },
                    "chart_generation": {
                        "max_retries": 2,
                        "fallback_action": "skip_step",
                        "validate_after": True,
                    },
                    "analysis": {
                        "max_retries": 2,
                        "fallback_action": "refetch_data",
                        "validate_after": True,
                    },
                },
            },
            "is_reflecting": False,
            "reflection_summary": [],
            "records": [],
        }

    def _build_response(self, final_state: Dict[str, Any]) -> Dict[str, Any]:
        prediction_state = final_state.get("prediction_state", {})
        identification = prediction_state.get("product_identification", {})
        data_fetch = prediction_state.get("data_fetch", {})
        chart_generation = prediction_state.get("chart_generation", {})
        analysis = prediction_state.get("analysis", {})

        success = (
            prediction_state.get("step") == "analysis"
            and identification.get("identified")
        )
        return {
            "success": success,
            "product": {
                "code": identification.get("product_code", ""),
                "name": identification.get("product_name", ""),
                "confidence": identification.get("confidence", 0.0),
            },
            "data": {
                "historical_data": data_fetch.get("historical_data", []),
                "future_predictions": data_fetch.get("future_predictions", []),
                "statistics": data_fetch.get("statistics", {}),
            },
            "chart": {
                "url": chart_generation.get("chart_url", ""),
                "type": chart_generation.get("chart_type", ""),
                "filepath": chart_generation.get("chart_filepath", ""),
            },
            "analysis": {
                "result": analysis.get("analysis_result", ""),
                "key_insights": analysis.get("key_insights", []),
                "recommendations": analysis.get("recommendations", []),
            },
            "reflection": final_state.get("reflection", {}),
            "state": self._serialize_state(final_state),
        }

    def _serialize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "user_query": state.get("user_query", ""),
            "chart_type": state.get("chart_type", ""),
            "prediction_state": state.get("prediction_state", {}),
            "is_completed": state.get("is_completed", False),
            "error_message": state.get("error_message", ""),
            "session_id": state.get("session_id"),
            "user_id": state.get("user_id"),
            "created_at": state.get("created_at", self._now_iso()),
            "updated_at": self._now_iso(),
        }

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime
        return datetime.now().isoformat()


class _DatabaseRepository:
    """简化版数据库仓库，只实现节点需要用到的几个方法。"""

    def __init__(self, db_config: Dict[str, Any]):
        import mysql.connector
        self._db_config = db_config
        self._conn = mysql.connector.connect(**db_config)

    def get_all_products(self):
        import mysql.connector
        cursor = self._conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products ORDER BY product_name")
        rows = cursor.fetchall()
        cursor.close()
        return [_Product.from_dict(r) for r in rows]

    def get_product_by_code(self, code: str):
        import mysql.connector
        cursor = self._conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM products WHERE product_code = %s", (code,))
        row = cursor.fetchone()
        cursor.close()
        return _Product.from_dict(row) if row else None

    def get_product_analysis_data(self, product_code: str, history_days: int = 90, future_days: int = 30):
        from datetime import date, timedelta

        product = self.get_product_by_code(product_code)
        if not product:
            raise ValueError(f"产品不存在: {product_code}")

        today = date.today()
        start_date = today - timedelta(days=history_days)

        import mysql.connector
        cursor = self._conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM sales_data WHERE product_code = %s AND sale_date >= %s ORDER BY sale_date",
            (product_code, start_date),
        )
        sales_history = [_SalesData.from_dict(r) for r in cursor.fetchall()]

        cursor.execute(
            "SELECT * FROM prediction_results WHERE product_code = %s AND prediction_date >= %s AND prediction_date <= %s",
            (product_code, start_date, today),
        )
        model_predictions = [_PredictionResult.from_dict(r) for r in cursor.fetchall()]

        cursor.execute(
            "SELECT * FROM prediction_results WHERE product_code = %s AND prediction_date > %s",
            (product_code, today),
        )
        future_predictions = [_PredictionResult.from_dict(r) for r in cursor.fetchall()]

        cursor.close()

        return _ProductAnalysisData(
            product=product,
            sales_history=sales_history,
            model_predictions=model_predictions,
            future_predictions=future_predictions,
        )

    def get_product_statistics(self, product_code: str, days: int = 30):
        from datetime import date, timedelta

        today = date.today()
        start_date = today - timedelta(days=days)
        mid_date = start_date + timedelta(days=days // 2)

        import mysql.connector
        cursor = self._conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT AVG(daily_total) as avg_daily_sales FROM ("
            "  SELECT SUM(quantity) as daily_total FROM sales_data "
            "  WHERE product_code = %s AND sale_date >= %s GROUP BY sale_date"
            ") as daily_sales",
            (product_code, start_date),
        )
        row = cursor.fetchone()
        avg_daily = row["avg_daily_sales"] if row else 0

        cursor.execute(
            "SELECT "
            "  SUM(CASE WHEN sale_date < %s THEN quantity ELSE 0 END) as first_half, "
            "  SUM(CASE WHEN sale_date >= %s THEN quantity ELSE 0 END) as second_half "
            "FROM sales_data WHERE product_code = %s AND sale_date >= %s",
            (mid_date, mid_date, product_code, start_date),
        )
        row = cursor.fetchone()
        first = row["first_half"] or 0
        second = row["second_half"] or 0
        trend_change = ((second - first) / first) * 100 if first > 0 else 0

        cursor.close()

        return {
            "product_code": product_code,
            "period_days": days,
            "avg_daily_sales": round(avg_daily, 2) if avg_daily else 0,
            "trend_change_percent": round(trend_change, 2),
            "trend_direction": "up" if trend_change > 5 else ("down" if trend_change < -5 else "stable"),
        }


class _Product:
    def __init__(self, product_code: str, product_name: str,
                 category: str = "", description: str = ""):
        self.product_code = product_code
        self.product_name = product_name
        self.category = category
        self.description = description

    @classmethod
    def from_dict(cls, row: dict):
        if row is None:
            return None
        return cls(
            product_code=row.get("product_code", ""),
            product_name=row.get("product_name", ""),
            category=row.get("category", ""),
            description=row.get("description", ""),
        )

    def to_dict(self):
        return {
            "product_code": self.product_code,
            "product_name": self.product_name,
            "category": self.category,
            "description": self.description,
        }


class _SalesData:
    def __init__(self, product_code: str, sale_date, quantity: int, price=0.0, region=""):
        self.product_code = product_code
        self.sale_date = sale_date
        self.quantity = quantity
        self.price = price
        self.region = region

    @classmethod
    def from_dict(cls, row: dict):
        return cls(
            product_code=row.get("product_code", ""),
            sale_date=row.get("sale_date"),
            quantity=row.get("quantity", 0),
            price=row.get("price", 0.0),
            region=row.get("region", ""),
        )


class _PredictionResult:
    def __init__(self, product_code: str, prediction_date, predicted_value: float,
                 confidence: float = 0.0, model_type: str = ""):
        self.product_code = product_code
        self.prediction_date = prediction_date
        self.predicted_value = predicted_value
        self.confidence = confidence
        self.model_type = model_type

    @classmethod
    def from_dict(cls, row: dict):
        return cls(
            product_code=row.get("product_code", ""),
            prediction_date=row.get("prediction_date"),
            predicted_value=row.get("predicted_value", 0.0),
            confidence=row.get("confidence", 0.0),
            model_type=row.get("model_type", ""),
        )


class _ProductAnalysisData:
    def __init__(self, product, sales_history, model_predictions, future_predictions):
        self.product = product
        self.sales_history = sales_history
        self.model_predictions = model_predictions
        self.future_predictions = future_predictions


def create_agent(config_file: Optional[str] = None) -> PredictionAgent:
    config = load_config(config_file)
    return PredictionAgent(config)
