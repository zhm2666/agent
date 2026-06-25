"""
条件路由

LangGraph 里最重要的"控制流"不是手写 if/else，
而是用条件边把上一步结果映射到下一步节点。
这里把业务规则集中放，方便后续改成 LLM 路由或规则路由。
"""

from typing import Any, Dict


def next_step(state: Dict[str, Any]) -> str:
    """
    根据当前状态决定下一个节点（仅作参考，当前图未使用此函数）。
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


def should_retry_or_end(state: Dict[str, Any]) -> str:
    """
    分析节点执行后的路由函数。

    验证通过  -> END（正常结束）
    验证失败但还有重试次数 -> 重试当前节点
    验证失败且重试次数耗尽 -> END（带 fallback 状态继续）
    """
    current_step = state.get("prediction_state", {}).get("step", "analysis")
    reflection = state.get("reflection", {})

    # 反思被禁用时直接结束
    if not reflection.get("enabled"):
        return "END"

    current_validation = reflection.get("current_validation") or {}

    # 验证通过 -> 结束
    if current_validation.get("is_valid", True):
        return "END"

    # 验证失败，检查是否还有重试次数
    retry_strategy = reflection.get("retry_strategy", {})
    step_configs = retry_strategy.get("step_configs", {})
    step_config = step_configs.get(current_step, {})
    max_retries = step_config.get(
        "max_retries", retry_strategy.get("max_retries", 3)
    )
    current_attempts = reflection.get("reflection_count", 0)

    if current_attempts < max_retries:
        return current_step

    # 重试次数耗尽 -> 结束（状态里已有 fallback 结果）
    return "END"


def should_retry_step(state: Dict[str, Any]) -> str:
    """供其他场景使用的重试判断函数。"""
    reflection = state.get("reflection", {})
    if not reflection.get("enabled"):
        return "continue"

    current_validation = reflection.get("current_validation") or {}
    if current_validation.get("is_valid", True):
        return "continue"

    return "retry"


def is_terminal(state: Dict[str, Any]) -> bool:
    """判断是否为终止状态。"""
    step = state.get("prediction_state", {}).get("step", "initial")
    return step in {"completed", "error"}
