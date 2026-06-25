"""
LangGraph 图构建器

把 PredictionAgent-Demo 的线性流程组装成 LangGraph StateGraph，
保留原有节点实现，只替换“顺序调用”为“图执行 + 条件边 + 检查点”。
"""

from typing import Any, Dict, Optional

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from ..state.prediction_state import AgentState
from ..nodes import (
    product_identification_node,
    data_fetch_node,
    chart_node,
    analysis_node,
    reflection_node,
)
from .conditional_routing import (
    is_terminal,
    next_step,
    should_continue_from_analysis,
    should_retry_step,
)


def create_prediction_graph(
    repository: Optional[Any] = None,
    mcp_client: Optional[Any] = None,
    checkpointer: Optional[Any] = None,
) -> StateGraph:
    """
    创建预测分析 LangGraph。

    Args:
        repository: 销售数据仓库，可选
        mcp_client: MCP 图表客户端，可选
        checkpointer: LangGraph 检查点后端，默认 MemorySaver

    Returns:
        可执行的 compiled graph app
    """
    builder = StateGraph(AgentState)

    builder.add_node(
        "product_identification",
        _wrap(product_identification_node, repository=repository),
    )
    builder.add_node(
        "data_fetch",
        _wrap(data_fetch_node, repository=repository),
    )
    builder.add_node(
        "chart_generation",
        _wrap(chart_node, mcp_client=mcp_client),
    )
    builder.add_node(
        "analysis",
        _wrap(analysis_node),
    )
    builder.add_node(
        "reflection",
        _wrap(reflection_node),
    )

    builder.add_edge("__start__", "product_identification")

    builder.add_edge("product_identification", "data_fetch")
    builder.add_edge("data_fetch", "chart_generation")
    builder.add_edge("chart_generation", "analysis")

    builder.add_conditional_edges(
        "analysis",
        should_continue_from_analysis,
        {
            "product_identification": "product_identification",
            "data_fetch": "data_fetch",
            "chart_generation": "chart_generation",
            "analysis": "analysis",
            "END": END,
        },
    )

    compiled = builder.compile(
        checkpointer=checkpointer or MemorySaver(),
    )
    return compiled


def _wrap(node_fn, **fixed_kwargs):
    """
    给节点函数包一层，把 repository / mcp_client 固定进去，
    只让 LangGraph 传 state。
    """

    def _inner(state: Dict[str, Any]) -> Dict[str, Any]:
        kwargs = {"state": state, **fixed_kwargs}
        try:
            return node_fn(**kwargs)
        except TypeError:
            return node_fn(state)

    return _inner
