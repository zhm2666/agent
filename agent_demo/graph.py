"""翻译质检图 + 人工审核 interrupt + OpenTelemetry 链路追踪"""

from typing import TypedDict, Optional
from opentelemetry import trace

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command


# ============ State ============
class State(TypedDict):
    text: str
    translation: str
    attempts: int
    quality: str
    human_decision: str


# ============ Tracer setup ============
_tracer: Optional[trace.Tracer] = None


def _get_tracer() -> trace.Tracer:
    """Lazy load tracer to avoid circular imports."""
    global _tracer
    if _tracer is None:
        from otel_setup import get_tracer
        _tracer = get_tracer("langgraph")
    return _tracer


# ============ Nodes (带追踪) ============
def translate(state: State) -> dict:
    """
    翻译节点：执行翻译任务。
    带 OpenTelemetry 追踪。
    """
    text = state["text"]
    attempts = state["attempts"]
    tracer = _get_tracer()

    with tracer.start_as_current_span(
        "translate_node",
        attributes={
            "node.name": "translate",
            "input.text_preview": text[:100] if text else "",
            "input.attempts": attempts,
        },
    ) as span:
        # 模拟：前两次翻译差，第三次变好
        if attempts < 2:
            result = f"[BAD_TRANSLATION] {text}"
        else:
            result = f"Hello World! (from: {text})"

        span.set_attribute("output.translation_preview", result[:100])
        span.set_attribute("output.translation_length", len(result))
        span.set_attribute("output.is_bad", "[BAD" in result)

        print(f"  [translate] attempt #{attempts + 1} → {result[:40]}...")

        return {
            "translation": result,
            "attempts": attempts + 1,
            "quality": "",
            "human_decision": "",
        }


def evaluate(state: State) -> dict:
    """
    评估节点：判断翻译质量。
    带 OpenTelemetry 追踪。
    """
    translation = state["translation"]
    attempts = state["attempts"]
    tracer = _get_tracer()

    with tracer.start_as_current_span(
        "evaluate_node",
        attributes={
            "node.name": "evaluate",
            "input.translation_preview": translation[:100] if translation else "",
            "input.attempts": attempts,
        },
    ) as span:
        quality = "good" if "[BAD" not in translation else "bad"

        span.set_attribute("output.quality", quality)
        span.set_attribute("output.decision", "end" if quality == "good" else "human_review")

        print(f"  [evaluate] quality={quality}")

        return {"quality": quality}


def human_review(state: State) -> dict:
    """
    人工审核节点 —— interrupt 暂停。
    带 OpenTelemetry 追踪。
    """
    translation = state["translation"]
    attempts = state["attempts"]
    tracer = _get_tracer()

    with tracer.start_as_current_span(
        "human_review_node",
        attributes={
            "node.name": "human_review",
            "input.translation_preview": translation[:100] if translation else "",
            "input.attempts": attempts,
        },
    ) as span:
        # 记录进入审核节点
        span.add_event("Entering human review, waiting for interrupt")

        # 暂停！把上下文交给调用方，等外部 resume
        decision = interrupt({
            "message": "请审核以下翻译结果",
            "translation": translation,
            "attempts": attempts,
            "instruction": "输入 'retry' 重试，或 'approve' 接受当前翻译",
        })

        span.set_attribute("input.decision", decision)
        span.add_event("Received human decision from interrupt")

        print(f"  [human_review] 收到人工决定: {decision}")

        return {"human_decision": decision}


# ============ Routers ============
def route_after_evaluate(state: State) -> str:
    """
    评估后的路由决策。
    带追踪。
    """
    tracer = _get_tracer()

    quality = state["quality"]
    attempts = state["attempts"]

    with tracer.start_as_current_span(
        "route_after_evaluate",
        attributes={
            "router.name": "route_after_evaluate",
            "input.quality": quality,
            "input.attempts": attempts,
        },
    ) as span:
        if quality == "good":
            span.set_attribute("output.route", "end")
            return "end"

        if attempts >= 3:
            span.set_attribute("output.route", "end_max_attempts")
            return "end"

        span.set_attribute("output.route", "human_review")
        return "human_review"


def route_after_human(state: State) -> str:
    """
    人工审核后的路由决策。
    带追踪。
    """
    tracer = _get_tracer()

    decision = state["human_decision"]

    with tracer.start_as_current_span(
        "route_after_human",
        attributes={
            "router.name": "route_after_human",
            "input.decision": decision,
        },
    ) as span:
        if decision == "approve":
            span.set_attribute("output.route", "end")
            return "end"

        span.set_attribute("output.route", "retry")
        return "retry"


# ============ Build ============
def build_graph():
    checkpointer = MemorySaver()

    builder = StateGraph(State)

    builder.add_node("translate", translate)
    builder.add_node("evaluate", evaluate)
    builder.add_node("human_review", human_review)

    builder.add_edge(START, "translate")
    builder.add_edge("translate", "evaluate")

    builder.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {"human_review": "human_review", "end": END},
    )

    builder.add_conditional_edges(
        "human_review",
        route_after_human,
        {"retry": "translate", "end": END},
    )

    return builder.compile(checkpointer=checkpointer)
