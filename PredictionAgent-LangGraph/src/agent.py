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
        try:
            from PredictionAgent_Demo.src.database import DatabaseConnection, SalesRepository
        except ImportError as exc:
            raise ImportError(
                "LangGraph 版本复用了 PredictionAgent-Demo 的数据库模块，"
                "请确保 PredictionAgent-Demo 在 Python 路径中。"
            ) from exc

        db_config = {
            "host": self.config.mysql_host,
            "port": self.config.mysql_port,
            "user": self.config.mysql_user,
            "password": self.config.mysql_password,
            "database": self.config.mysql_database,
        }
        self.db_connection = DatabaseConnection(**db_config)
        if self.db_connection.connect():
            self.repository: Optional[Any] = SalesRepository(self.db_connection)
        else:
            self.repository = None

        self.mcp_client = self._create_mcp_client()

    def _create_mcp_client(self) -> Optional[Any]:
        try:
            from PredictionAgent_Demo.src.mcp import MCPChartClient
            return MCPChartClient(mode="local")
        except Exception:
            return None

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
        if use_mock_data or self.repository is None:
            repository = None
        else:
            repository = self.repository

        initial_state: AgentState = {
            "user_query": query,
            "chart_type": chart_type,
            "prediction_state": {
                "step": "product_identification" if not product_code else "product_identification",
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
        if use_mock_data or self.repository is None:
            repository = None
        else:
            repository = self.repository

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

        success = prediction_state.get("step") == "completed" and identification.get("identified")
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


def create_agent(config_file: Optional[str] = None) -> PredictionAgent:
    config = load_config(config_file)
    return PredictionAgent(config)
