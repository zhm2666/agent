"""FastAPI 多用户服务 + Interrupt 人工审核 + OpenTelemetry 分布式链路追踪"""

from contextlib import asynccontextmanager
from typing import Optional
import time

from fastapi import FastAPI, Depends, Request

from database import init_db, get_or_create_thread, list_user_sessions
from auth import get_current_user
from graph import build_graph
from models import (
    ChatRequest, ChatResponse, ReviewRequest, ReviewResponse, SessionInfo
)
from langgraph.types import Command
from otel_setup import init_opentelemetry, get_tracer
from langgraph_tracing import create_tracer, LangGraphTracer

import os
from dotenv import load_dotenv

load_dotenv()  # 读取 .env

# 保险起见显式设一下（有些部署环境 dotenv 不生效）
os.environ.setdefault("LANGSMITH_TRACING", "true")

# 全局 tracer 实例
_tracer: Optional = None
_langgraph_tracer: Optional[LangGraphTracer] = None


# ============ 生命周期 ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _tracer, _langgraph_tracer

    # 初始化数据库
    init_db()
    print("✅ Database initialized")

    # 初始化 OpenTelemetry
    otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")
    print(f"📊 Initializing OpenTelemetry (endpoint: {otlp_endpoint})...")

    shutdown = init_opentelemetry(
        service_name="agent-demo",
        service_version="1.0.0",
        otlp_endpoint=otlp_endpoint,
    )

    _tracer = get_tracer("agent-demo")
    _langgraph_tracer = create_tracer()

    print("✅ OpenTelemetry initialized")

    yield

    # 关闭时导出剩余的 spans
    print("📊 Shutting down OpenTelemetry...")
    shutdown()


app = FastAPI(
    title="Translation Agent with Human-in-the-Loop",
    description="LangGraph + Interrupt 多用户翻译质检服务 + OpenTelemetry 分布式追踪",
    lifespan=lifespan,
)

# 构建图（放在 lifespan 外，因为只需要构建一次）
graph = build_graph()


# ============ OpenTelemetry 中间件 ============
@app.middleware("http")
async def otel_middleware(request: Request, call_next):
    """
    HTTP 中间件：自动为每个请求创建 trace span。
    """
    global _tracer

    # 从请求路径获取路由信息
    span_name = f"{request.method} {request.url.path}"

    with _tracer.start_as_current_span(
        span_name,
        attributes={
            "http.method": request.method,
            "http.url": str(request.url),
            "http.target": request.url.path,
            "http.host": request.url.hostname or "localhost",
            "http.scheme": request.url.scheme,
            "user_agent": request.headers.get("user-agent", "unknown"),
        },
    ) as span:
        # 处理请求
        response = await call_next(request)

        # 记录响应状态
        span.set_attribute("http.status_code", response.status_code)

        return response


# ============ Endpoint 1: 启动翻译 ============
@app.post("/chat", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    user_id: str = Depends(get_current_user),
):
    """
    启动翻译任务
    - 如果翻译质量差 → 暂停等待人工审核
    - 如果翻译质量好 → 直接返回结果
    """
    global _tracer, _langgraph_tracer

    with _tracer.start_as_current_span(
        "chat",
        attributes={
            "user.id": user_id,
            "session.id": req.session_id or "new",
            "text.length": len(req.text),
            "text.preview": req.text[:50],
        },
    ) as span:
        start_time = time.perf_counter()

        # 1. 解析 session
        session_id = req.session_id or f"session_{user_id}_{hash(req.text) % 10000}"

        # 2. 获取 thread_id（多用户隔离）
        thread_id = get_or_create_thread(user_id, session_id)
        config = {"configurable": {"thread_id": thread_id}}

        span.set_attribute("thread.id", thread_id)

        # 3. 初始状态
        initial_state = {
            "text": req.text,
            "translation": "",
            "attempts": 0,
            "quality": "",
            "human_decision": "",
        }

        # 4. 使用追踪版节点执行图
        result = _langgraph_tracer.trace_node("translate", {"endpoint": "/chat"})(lambda s: graph.nodes["translate"].func(s))(initial_state)

        # 跟踪图执行
        result = _execute_graph_with_tracing(
            initial_state,
            config,
            operation="chat",
            user_id=user_id,
            thread_id=thread_id,
        )

        duration = time.perf_counter() - start_time

        # 5. 检测是否被 interrupt 暂停
        if "__interrupt__" in result:
            interrupt_value = result["__interrupt__"][0].value
            span.set_attribute("result.status", "waiting_for_review")
            span.set_attribute("result.attempts", result.get("attempts", 0))

            _langgraph_tracer.record_graph_invocation(
                "chat", thread_id, "interrupted", duration
            )

            return ChatResponse(
                status="waiting_for_review",
                review_data=interrupt_value,
                message="翻译质量不佳，等待人工审核",
            )

        # 6. 正常完成（质量直接通过）
        span.set_attribute("result.status", "completed")
        span.set_attribute("result.attempts", result.get("attempts", 0))
        span.set_attribute("result.quality", result.get("quality", ""))

        _langgraph_tracer.record_graph_invocation(
            "chat", thread_id, "completed", duration
        )

        return ChatResponse(
            status="completed",
            translation=result.get("translation"),
            attempts=result.get("attempts"),
            quality=result.get("quality"),
            message="翻译完成",
        )


def _execute_graph_with_tracing(
    initial_state: dict,
    config: dict,
    operation: str,
    user_id: str,
    thread_id: str,
) -> dict:
    """
    执行 LangGraph 并追踪每个节点。
    替代直接调用 graph.invoke()，提供细粒度的链路追踪。
    """
    global _langgraph_tracer

    state = initial_state.copy()
    max_iterations = 20  # 防止无限循环
    iteration = 0

    with _tracer.start_as_current_span(
        f"graph.{operation}",
        attributes={
            "graph.operation": operation,
            "thread.id": thread_id,
            "user.id": user_id,
        },
    ):
        while iteration < max_iterations:
            iteration += 1

            # 1. translate 节点
            with _tracer.start_as_current_span(
                "node.translate",
                attributes={"iteration": iteration},
            ):
                state = _langgraph_tracer.trace_node("translate")(graph.nodes["translate"].func)(state)

            # 2. evaluate 节点
            with _tracer.start_as_current_span("node.evaluate"):
                eval_result = _langgraph_tracer.trace_node("evaluate")(graph.nodes["evaluate"].func)(state)
                state.update(eval_result)

            # 3. 路由决策
            quality = state.get("quality", "")
            attempts = state.get("attempts", 0)

            if quality == "good":
                _langgraph_tracer.record_router("route_after_evaluate", "end", state)
                break

            if attempts >= 3:
                _langgraph_tracer.record_router("route_after_evaluate", "end_max_attempts", state)
                break

            # 4. human_review 节点 (interrupt)
            with _tracer.start_as_current_span("node.human_review"):
                hr_result = _langgraph_tracer.trace_node("human_review")(graph.nodes["human_review"].func)(state)
                state.update(hr_result)

            decision = state.get("human_decision", "")

            if decision == "approve":
                _langgraph_tracer.record_router("route_after_human", "end", state)
                break

            _langgraph_tracer.record_router("route_after_human", "retry", state)

        return state


# ============ Endpoint 2: 人工审核后恢复 ============
@app.post("/review", response_model=ReviewResponse)
def review(
    req: ReviewRequest,
    user_id: str = Depends(get_current_user),
):
    """
    人工审核后恢复图的执行
    - decision: "retry" 重试翻译 / "approve" 接受当前结果
    """
    global _tracer, _langgraph_tracer

    with _tracer.start_as_current_span(
        "review",
        attributes={
            "user.id": user_id,
            "thread.id": req.thread_id,
            "decision": req.decision,
        },
    ) as span:
        start_time = time.perf_counter()

        # 1. 校验 thread_id 归属（防止越权）
        from database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM conversation_threads WHERE thread_id=? AND user_id=?",
            (req.thread_id, user_id),
        )
        if not cursor.fetchone():
            conn.close()
            from fastapi import HTTPException
            raise HTTPException(403, "无权访问此会话")

        conn.close()

        # 2. 恢复执行（仍然使用 LangGraph 的 interrupt 机制）
        config = {"configurable": {"thread_id": req.thread_id}}

        # 由于 interrupt 需要通过 graph.invoke 恢复，我们直接调用
        # 但添加追踪上下文
        with _tracer.start_as_current_span("graph.resume"):
            result = graph.invoke(
                Command(resume=req.decision),
                config=config,
            )

        duration = time.perf_counter() - start_time

        # 3. 检查结果
        if "__interrupt__" in result:
            span.set_attribute("result.status", "waiting_for_review")
            _langgraph_tracer.record_graph_invocation(
                "review", req.thread_id, "interrupted", duration
            )

            interrupt_value = result["__interrupt__"][0].value
            return ReviewResponse(
                status="waiting_for_review",
                review_data=interrupt_value,
                message="再次等待人工审核",
            )

        span.set_attribute("result.status", "completed")
        span.set_attribute("result.human_decision", result.get("human_decision", ""))

        _langgraph_tracer.record_graph_invocation(
            "review", req.thread_id, "completed", duration
        )

        return ReviewResponse(
            status="completed",
            translation=result.get("translation"),
            attempts=result.get("attempts"),
            quality=result.get("quality"),
            human_decision=result.get("human_decision"),
            message="审核完成，图执行结束",
        )


# ============ 辅助接口 ============
@app.get("/sessions", response_model=list[SessionInfo])
def list_sessions(user_id: str = Depends(get_current_user)):
    """列出用户的所有会话"""
    global _tracer

    with _tracer.start_as_current_span("list_sessions"):
        sessions = list_user_sessions(user_id)
        return [SessionInfo(**s) for s in sessions]


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
