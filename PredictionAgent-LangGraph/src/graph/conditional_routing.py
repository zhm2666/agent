"""
条件路由

LangGraph 里最重要的“控制流”不是手写 if/else，
而是用条件边把上一步结果映射到下一步节点。
这里把业务规则集中放，方便后续改成 LLM 路由或规则路由。
"""

from typing import Any, Dict, Optional


def next_step(state: Dict[str, Any]) -> str:
    """
    根据当前状态决定下一个节点。

    返回 LangGraph 节点名，不是原始业务 step。
    """
    current_step = state.get("prediction_state", {}).get("step", "initial")

    if current_step in {"completed", "error"}:
        return "END"

    step_map = {
        "initial": "product_identification",
        "product_identification": "data_fetch",
        "data_fetch": "chart_generation",
        "chart_generation": "analysis",
        "analysis": "analysis",
    }
    return step_map.get(current_step, "END")


def should_continue_from_analysis(state: Dict[str, Any]) -> str:
    """
    分析节点执行后，决定是重试当前步骤还是结束。
    """
    current_step = state.get("prediction_state", {}).get("step", "analysis")
    reflection = state.get("reflection", {})

    if not reflection.get("enabled"):
        return "END"

    current_validation = reflection.get("current_validation") or {}
    if current_validation.get("is_valid", True):
        return "END"

    retry_strategy = reflection.get("retry_strategy", {})
    step_configs = retry_strategy.get("step_configs", {})
    step_config = step_configs.get(current_step, {})
    max_retries = step_config.get("max_retries", retry_strategy.get("max_retries", 3))
    current_attempts = reflection.get("reflection_count", 0)

    if current_attempts < max_retries:
        return current_step

    return "END"


def should_retry_step(state: Dict[str, Any]) -> str:
    reflection = state.get("reflection", {})
    if not reflection.get("enabled"):
        return "continue"

    current_validation = reflection.get("current_validation") or {}
    if current_validation.get("is_valid", True):
        return "continue"

    return "retry"


def is_terminal(state: Dict[str, Any]) -> bool:
    step = state.get("prediction_state", {}).get("step", "initial")
    return step in {"completed", "error"}
