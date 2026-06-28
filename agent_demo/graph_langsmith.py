"""LangSmith 集成 - 使用 LangSmith 原生追踪"""
import os
from dotenv import load_dotenv

load_dotenv()

# 设置 LangSmith 环境变量
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
os.environ["LANGSMITH_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "agent-demo")

from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt

# 导入 langsmith
from langsmith.run_helpers import traceable


class State(TypedDict):
    text: str
    translation: str
    attempts: int
    quality: str
    human_decision: str


# ============ Nodes (带 LangSmith 追踪) ============
@traceable(name="translate", tags=["langgraph-node"])
def translate(state: State) -> dict:
    """翻译节点 - 自动追踪输入输出"""
    text = state["text"]
    attempts = state["attempts"]

    if attempts < 2:
        result = f"[BAD_TRANSLATION] {text}"
    else:
        result = f"Hello World! (from: {text})"

    print(f"  [translate] attempt #{attempts + 1} → {result[:40]}...")

    return {
        "translation": result,
        "attempts": attempts + 1,
        "quality": "",
        "human_decision": "",
    }


@traceable(name="evaluate", tags=["langgraph-node"])
def evaluate(state: State) -> dict:
    """评估节点"""
    translation = state["translation"]
    quality = "good" if "[BAD" not in translation else "bad"

    print(f"  [evaluate] quality={quality}")

    return {"quality": quality}


@traceable(name="human_review", tags=["langgraph-node"])
def human_review(state: State) -> dict:
    """人工审核节点"""
    translation = state["translation"]
    attempts = state["attempts"]

    decision = interrupt({
        "message": "请审核以下翻译结果",
        "translation": translation,
        "attempts": attempts,
        "instruction": "输入 'retry' 重试，或 'approve' 接受当前翻译",
    })

    print(f"  [human_review] 收到人工决定: {decision}")

    return {"human_decision": decision}


def route_after_evaluate(state: State) -> str:
    if state["quality"] == "good":
        return "end"
    if state["attempts"] >= 3:
        return "end"
    return "human_review"


def route_after_human(state: State) -> str:
    if state["human_decision"] == "approve":
        return "end"
    return "retry"


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
