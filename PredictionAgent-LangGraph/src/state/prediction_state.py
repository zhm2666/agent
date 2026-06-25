"""
LangGraph 状态定义
将原 PredictionAgent-Demo 的状态结构映射为 TypedDict，
便于 LangGraph 持久化、检查点和路由。
"""

from typing import TypedDict, Optional, Dict, Any, List


class ProductIdentificationState(TypedDict):
    identified: bool
    product_code: str
    product_name: str
    confidence: float
    reasoning: str
    alternatives: List[Dict[str, Any]]


class DataFetchState(TypedDict):
    fetched: bool
    historical_data: List[Dict[str, Any]]
    model_predictions: List[Dict[str, Any]]
    future_predictions: List[Dict[str, Any]]
    statistics: Dict[str, Any]
    error_message: str


class ChartState(TypedDict):
    generated: bool
    chart_type: str
    chart_url: str
    chart_filepath: str
    chart_id: str


class AnalysisState(TypedDict):
    analyzed: bool
    analysis_result: str
    key_insights: List[str]
    recommendations: List[str]


class PredictionState(TypedDict):
    step: str
    product_identification: ProductIdentificationState
    data_fetch: DataFetchState
    chart_generation: ChartState
    analysis: AnalysisState


class ReflectionState(TypedDict):
    enabled: bool
    reflection_count: int
    max_reflections: int
    current_validation: Optional[Dict[str, Any]]
    retry_strategy: Dict[str, Any]
    is_reflecting: bool
    reflection_summary: List[str]
    records: List[Dict[str, Any]]


class AgentState(TypedDict):
    """
    LangGraph 主状态

    LangGraph 会按字段更新状态，不要把状态塞进一个大 dict 后手动 merge；
    这里显式声明后，节点返回值里只带需要更新的字段即可。
    """
    user_query: str
    chart_type: str
    prediction_state: PredictionState
    reflection: ReflectionState
    is_completed: bool
    error_message: str
    session_id: Optional[str]
    user_id: Optional[str]
    created_at: str
    updated_at: str
