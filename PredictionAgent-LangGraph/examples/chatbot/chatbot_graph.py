"""
最小可运行示例：带分布式链路采集的 LangGraph 聊天机器人服务。

链路导出支持两路：
1. LangSmith（远程观测平台）
2. OpenTelemetry → Jaeger / 任何兼容 OTLP 的观测平台

目录结构：
examples/
  chatbot/
    chatbot_graph.py   # 图定义 + 入口
    run_chatbot.py     # 运行脚本
    README.md          # 启动与验证说明
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from langgraph.graph import END, StateGraph

from src.tracing import init_tracing, trace_node, traceable
from src.state.prediction_state import AgentState


# ============ 1. 初始化分布式追踪 ============


def init_chatbot_tracing() -> None:
    """启动链路采集，支持 LangSmith 和 OTLP 双轨输出。"""
    init_tracing(
        service_name="chatbot-service",
        otlp_endpoint=os.getenv("OTLP_ENDPOINT", "http://localhost:4318"),
        use_langsmith=os.getenv("LANGSMITH_TRACING", "false").lower() == "true",
    )


# ============ 2. 最小 LangGraph 图 ============


def build_chatbot_graph() -> StateGraph:
    """
    构建最小聊天图：
    user_input -> intent_classify -> (工具调用 / 直接回答) -> response_generation -> END
    """

    builder = StateGraph(AgentState)

    builder.add_node("user_input", user_input_node)
    builder.add_node("intent_classify", intent_classify_node)
    builder.add_node("tool_call", tool_call_node)
    builder.add_node("response_generation", response_generation_node)

    builder.set_entry_point("user_input")
    builder.add_edge("user_input", "intent_classify")

    builder.add_conditional_edges(
        "intent_classify",
        route_after_intent,
        {
            "tool_call": "tool_call",
            "response_generation": "response_generation",
        },
    )

    builder.add_edge("tool_call", "response_generation")
    builder.add_edge("response_generation", END)

    return builder.compile()


# ============ 3. 节点实现 ============


@traceable(name="chatbot.user_input")
def user_input_node(state: AgentState) -> AgentState:
    """接收用户输入并写入状态。"""
    state["user_query"] = state.get("user_query", "")
    state["prediction_state"] = state.get("prediction_state", {})
    return state


@trace_node("intent_classify")
def intent_classify_node(state: AgentState) -> AgentState:
    """简化版意图识别：含工具词则走工具。"""
    query = (state.get("user_query") or "").lower()
    needs_tool = any(keyword in query for keyword in ["时间", "天气", "价格", "库存", "销量"])

    state["prediction_state"] = state.get("prediction_state", {})
    state["prediction_state"]["intent"] = {
        "needs_tool": needs_tool,
        "confidence": 0.9 if needs_tool else 0.7,
    }
    return state


def route_after_intent(state: AgentState) -> str:
    intent = state.get("prediction_state", {}).get("intent", {})
    return "tool_call" if intent.get("needs_tool") else "response_generation"


@trace_node("tool_call")
def tool_call_node(state: AgentState) -> AgentState:
    """模拟工具调用。"""
    state["prediction_state"] = state.get("prediction_state", {})
    state["prediction_state"]["tool_result"] = {
        "tool": "mock_tool",
        "result": "tool_result_placeholder",
    }
    return state


@trace_node("response_generation")
def response_generation_node(state: AgentState) -> AgentState:
    """模拟回答生成。"""
    state["prediction_state"] = state.get("prediction_state", {})
    state["prediction_state"]["answer"] = "这是基于链路采集的最小聊天回复。"
    return state


# ============ 4. 运行入口 ============


@traceable(name="chatbot.run", tags=["chatbot", "entry"])
def run_chatbot(user_query: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
    """
    执行一次聊天，返回最终状态。

    可通过 thread_id 做多轮续跑，对应 LangGraph checkpointer。
    """
    init_chatbot_tracing()

    initial_state: AgentState = {
        "user_query": user_query,
        "chart_type": "",
        "prediction_state": {},
        "reflection": {},
        "is_completed": False,
        "error_message": "",
        "session_id": thread_id,
        "user_id": None,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    graph = build_chatbot_graph()
    config = {
        "configurable": {
            "thread_id": thread_id or "chatbot-default",
        }
    }

    try:
        final_state = graph.invoke(initial_state, config)
    except Exception as exc:  # pragma: no cover - 演示容错
        return {"success": False, "error": str(exc), "state": initial_state}

    return _build_response(final_state)


def stream_chatbot(user_query: str, thread_id: Optional[str] = None):
    """流式执行，便于实时展示节点执行情况。"""
    init_chatbot_tracing()

    initial_state: AgentState = {
        "user_query": user_query,
        "chart_type": "",
        "prediction_state": {},
        "reflection": {},
        "is_completed": False,
        "error_message": "",
        "session_id": thread_id,
        "user_id": None,
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    graph = build_chatbot_graph()
    config = {
        "configurable": {
            "thread_id": thread_id or "chatbot-default",
        }
    }

    for event in graph.stream(initial_state, config):
        yield event


def _build_response(final_state: Dict[str, Any]) -> Dict[str, Any]:
    prediction_state = final_state.get("prediction_state", {})
    return {
        "success": True,
        "query": final_state.get("user_query"),
        "intent": prediction_state.get("intent"),
        "tool_result": prediction_state.get("tool_result"),
        "answer": prediction_state.get("answer"),
        "state": final_state,
    }


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now().isoformat()
