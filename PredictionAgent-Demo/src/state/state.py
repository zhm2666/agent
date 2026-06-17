"""
状态管理模块
定义预测分析Agent的所有状态数据结构和操作方法
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


@dataclass
class ProductIdentificationState:
    """产品识别状态"""
    identified: bool = False
    product_code: str = ""
    product_name: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    alternatives: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identified": self.identified,
            "product_code": self.product_code,
            "product_name": self.product_name,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "alternatives": self.alternatives
        }


@dataclass
class DataFetchState:
    """数据获取状态"""
    fetched: bool = False
    historical_data: List[Dict[str, Any]] = field(default_factory=list)
    model_predictions: List[Dict[str, Any]] = field(default_factory=list)
    future_predictions: List[Dict[str, Any]] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fetched": self.fetched,
            "historical_data": self.historical_data,
            "model_predictions": self.model_predictions,
            "future_predictions": self.future_predictions,
            "statistics": self.statistics,
            "error_message": self.error_message
        }


@dataclass
class ChartState:
    """图表生成状态"""
    generated: bool = False
    chart_type: str = ""
    chart_url: str = ""
    chart_filepath: str = ""
    chart_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated": self.generated,
            "chart_type": self.chart_type,
            "chart_url": self.chart_url,
            "chart_filepath": self.chart_filepath,
            "chart_id": self.chart_id
        }


@dataclass
class AnalysisState:
    """分析状态"""
    analyzed: bool = False
    analysis_result: str = ""
    key_insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analyzed": self.analyzed,
            "analysis_result": self.analysis_result,
            "key_insights": self.key_insights,
            "recommendations": self.recommendations
        }


@dataclass
class PredictionState:
    """单个预测分析的状态"""
    step: str = "initial"  # initial, product_identification, data_fetch, chart_generation, analysis, completed
    product_identification: ProductIdentificationState = field(default_factory=ProductIdentificationState)
    data_fetch: DataFetchState = field(default_factory=DataFetchState)
    chart_generation: ChartState = field(default_factory=ChartState)
    analysis: AnalysisState = field(default_factory=AnalysisState)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "product_identification": self.product_identification.to_dict(),
            "data_fetch": self.data_fetch.to_dict(),
            "chart_generation": self.chart_generation.to_dict(),
            "analysis": self.analysis.to_dict()
        }


@dataclass
class State:
    """整个Agent的状态"""
    user_query: str = ""
    chart_type: str = "combined"  # bar, line, combined
    prediction_state: PredictionState = field(default_factory=PredictionState)
    is_completed: bool = False
    error_message: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def update_timestamp(self):
        """更新时间戳"""
        self.updated_at = datetime.now().isoformat()

    def set_step(self, step: str):
        """设置当前步骤"""
        self.prediction_state.step = step
        self.update_timestamp()

    def mark_completed(self):
        """标记为完成"""
        self.is_completed = True
        self.prediction_state.step = "completed"
        self.update_timestamp()

    def mark_error(self, error_message: str):
        """标记错误"""
        self.error_message = error_message
        self.prediction_state.step = "error"
        self.update_timestamp()

    def get_progress(self) -> float:
        """获取进度"""
        step_weights = {
            "initial": 0,
            "product_identification": 20,
            "data_fetch": 40,
            "chart_generation": 60,
            "analysis": 80,
            "completed": 100,
            "error": 0
        }
        return step_weights.get(self.prediction_state.step, 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_query": self.user_query,
            "chart_type": self.chart_type,
            "prediction_state": self.prediction_state.to_dict(),
            "is_completed": self.is_completed,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "State":
        pred_state_data = data.get("prediction_state", {})
        pred_state = PredictionState(
            step=pred_state_data.get("step", "initial"),
            product_identification=ProductIdentificationState(**pred_state_data.get("product_identification", {})),
            data_fetch=DataFetchState(**pred_state_data.get("data_fetch", {})),
            chart_generation=ChartState(**pred_state_data.get("chart_generation", {})),
            analysis=AnalysisState(**pred_state_data.get("analysis", {}))
        )

        return cls(
            user_query=data.get("user_query", ""),
            chart_type=data.get("chart_type", "combined"),
            prediction_state=pred_state,
            is_completed=data.get("is_completed", False),
            error_message=data.get("error_message", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat())
        )

    @classmethod
    def from_json(cls, json_str: str) -> "State":
        data = json.loads(json_str)
        return cls.from_dict(data)

    def save_to_file(self, filepath: str):
        """保存状态到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

    @classmethod
    def load_from_file(cls, filepath: str) -> "State":
        """从文件加载状态"""
        with open(filepath, 'r', encoding='utf-8') as f:
            json_str = f.read()
        return cls.from_json(json_str)
