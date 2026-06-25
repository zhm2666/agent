"""
反思节点

在 LangGraph 里，验证失败后的重试由条件边决定，
这个节点负责执行一次验证，并把结果写回 reflection 状态。
"""

from typing import Any, Dict, Optional


def reflection_node(
    state: Dict[str, Any],
    evaluator: Optional[Any] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    对当前步骤执行结果进行验证，并更新 reflection 状态。

    这个节点本身不做流程跳转；
    跳转由 graph/conditional_routing.py 里的条件边决定。
    """
    step = state.get("prediction_state", {}).get("step", "")
    if not step:
        return {}

    input_data, output_data = _collect_step_io(state, step)

    validation = None
    if evaluator is not None:
        try:
            validation = evaluator.evaluate(step, input_data, output_data)
        except Exception:
            validation = None

    reflection_state = _build_reflection_state(
        state.get("reflection", {}),
        step,
        input_data,
        output_data,
        validation,
    )

    return {"reflection": reflection_state}


def _collect_step_io(
    state: Dict[str, Any], step: str
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    prediction_state = state.get("prediction_state", {})
    input_data = {"user_query": state.get("user_query", "")}
    if step == "product_identification":
        output_data = dict(prediction_state.get("product_identification", {}))
    elif step == "data_fetch":
        output_data = dict(prediction_state.get("data_fetch", {}))
    elif step == "chart_generation":
        output_data = dict(prediction_state.get("chart_generation", {}))
    elif step == "analysis":
        output_data = dict(prediction_state.get("analysis", {}))
    else:
        output_data = {}
    return input_data, output_data


def _build_reflection_state(
    current_reflection: Dict[str, Any],
    step: str,
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
    validation: Optional[Any],
) -> Dict[str, Any]:
    records = list(current_reflection.get("records", []))
    records.append({
        "step": step,
        "timestamp": _now_iso(),
        "input_data": input_data,
        "output_data": output_data,
        "validation": _serialize_validation(validation),
        "retry_count": len(records),
        "final_action": "",
        "notes": "",
    })

    reflection_count = current_reflection.get("reflection_count", 0) + 1
    validation_dict = _serialize_validation(validation)

    summary = list(current_reflection.get("reflection_summary", []))
    if validation_dict and not validation_dict.get("is_valid", True):
        summary.append(f"[{step}] {validation_dict.get('error_message', '验证失败')}")

    return {
        "enabled": True,
        "reflection_count": reflection_count,
        "max_reflections": current_reflection.get("max_reflections", 5),
        "current_validation": validation_dict,
        "retry_strategy": current_reflection.get(
            "retry_strategy", _default_retry_strategy()
        ),
        "is_reflecting": True,
        "reflection_summary": summary,
        "records": records,
    }


def _serialize_validation(validation: Optional[Any]) -> Optional[Dict[str, Any]]:
    if validation is None:
        return None
    try:
        return validation.to_dict()
    except AttributeError:
        return {
            "is_valid": getattr(validation, "is_valid", True),
            "score": getattr(validation, "score", 1.0),
            "error_type": _enum_value(getattr(validation, "error_type", None)),
            "error_message": getattr(validation, "error_message", ""),
            "suggestions": getattr(validation, "suggestions", []),
            "metadata": getattr(validation, "metadata", {}),
        }


def _enum_value(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    try:
        return value.value
    except AttributeError:
        return str(value)


def _default_retry_strategy() -> Dict[str, Any]:
    return {
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
    }


def _now_iso() -> str:
    from datetime import datetime
    return datetime.now().isoformat()
