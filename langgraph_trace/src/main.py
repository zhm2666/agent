import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# 关键：尽早加载 .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path, encoding="utf-8")

# 调试：确认配置是否加载
from langgraph_trace.src.tracing.config import TracingConfig
if TracingConfig.is_enabled():
    logging.warning(f"[Tracing DEBUG] OTel enabled, endpoint={TracingConfig.OTLP_ENDPOINT}, service={TracingConfig.SERVICE_NAME}")
else:
    logging.warning(f"[Tracing DEBUG] 追踪未启用! USE_OTEL={TracingConfig.USE_OTEL}, LANGSMITH={TracingConfig.LANGSMITH_TRACING}")

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from langgraph_trace.src.tracing.manager import init_tracing, get_tracing_manager
from langgraph_trace.src.chatbot.pure_graph import PureChatbotGraph
from langgraph_trace.src.chatbot.session_manager import get_session_manager

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# 初始化追踪
init_tracing()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 应用启动")
    yield
    logger.info("👋 应用关闭，清理追踪资源...")
    manager = get_tracing_manager()
    if manager:
        manager.shutdown()

app = FastAPI(
    title="LangGraph Chatbot with Tracing",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建聊天机器人
chatbot = PureChatbotGraph()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    user_id: Optional[str] = "anonymous"
    session_id: Optional[str] = None  # 可选，不传则自动生成


class ChatResponse(BaseModel):
    response: str
    reasoning_steps: List[str]
    tool_results: List[Dict[str, Any]]
    session_id: str
    status: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """同步聊天接口"""
    try:
        import uuid
        session_id = req.session_id or str(uuid.uuid4())
        result = chatbot.invoke(req.message, req.user_id, session_id)
        return ChatResponse(**result)
    except Exception as e:
        logger.exception("Chat error")
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "status": "error"}
        )


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """流式聊天接口"""
    import uuid
    import json

    session_id = req.session_id or str(uuid.uuid4())

    async def event_generator():
        try:
            for chunk in chatbot.stream(req.message, req.user_id, session_id):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            # 发送结束信号
            yield f"data: {json.dumps({'type': 'done', 'session_id': session_id}, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.exception("Stream error")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """获取会话信息"""
    manager = get_session_manager()
    info = manager.get_session_info(session_id)
    if info:
        return info
    return JSONResponse(status_code=404, content={"error": "Session not found"})


@app.get("/sessions")
async def list_sessions():
    """列出所有活跃会话"""
    manager = get_session_manager()
    return {
        "active_sessions": manager.active_sessions,
        "max_history": manager.max_history,
        "ttl_minutes": manager.ttl_minutes
    }


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """删除会话"""
    manager = get_session_manager()
    if manager.clear_session(session_id):
        return {"status": "deleted", "session_id": session_id}
    return JSONResponse(status_code=404, content={"error": "Session not found"})


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "active_sessions": get_session_manager().active_sessions
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "langgraph_trace.src.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info")
    )
