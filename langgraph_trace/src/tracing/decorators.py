import functools
import inspect
from typing import Any, Callable, Dict, List, Optional, Union, get_type_hints
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from langgraph_trace.src.tracing.manager import get_tracing_manager
from langgraph_trace.src.tracing.config import TracingConfig

# LangSmith 可用性检查
try:
    from langsmith import traceable as _langsmith_traceable
    _langsmith_available = True
except ImportError:
    _langsmith_available = False
    _langsmith_traceable = None


def _extract_state_from_args(func: Callable, args: tuple, kwargs: dict) -> Dict[str, Any]:
    """智能从函数参数中提取 state"""
    sig = inspect.signature(func)

    # 1. 尝试从命名参数获取
    if "state" in kwargs:
        state = kwargs["state"]
        if isinstance(state, dict):
            return state

    # 2. 尝试从位置参数获取 (通常是第一个参数 self/class, 第二个是 state)
    try:
        bound = sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()

        # 查找 state 参数 (排除 self)
        params = list(sig.parameters.keys())
        for i, param_name in enumerate(params):
            if param_name == "state" and i < len(args):
                state = args[i] if i < len(args) else None
                if isinstance(state, dict):
                    return state
                # 尝试从 ChatbotState 实例获取
                if hasattr(state, "__dict__"):
                    return state.__dict__
    except (TypeError, IndexError):
        pass

    return {}


def _extract_user_info(state: Dict[str, Any]) -> Dict[str, str]:
    """从 state 中提取用户信息"""
    info = {}
    if isinstance(state, dict):
        if "user_query" in state:
            query = str(state["user_query"])[:100]
            if query:
                info["user_query_preview"] = query
        if "user_id" in state:
            info["user_id"] = str(state["user_id"])
        if "session_id" in state:
            info["session_id"] = str(state["session_id"])
        # 尝试从 messages 中提取最后一条用户消息
        messages = state.get("messages", [])
        if messages and hasattr(messages[-1], "content"):
            last_content = str(messages[-1].content)[:50]
            if last_content:
                info["last_message_preview"] = last_content
    return info


def traceable(
        name: str,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
):
    """通用追踪装饰器"""
    tags = tags or []
    metadata = metadata or {}

    # 优先 LangSmith
    if _langsmith_available and _langsmith_traceable:
        return _langsmith_traceable(name=name, tags=tags, metadata=metadata)

    def decorator(func: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(func)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            manager = get_tracing_manager()
            tracer = manager.get_tracer() if manager else None

            if tracer:
                span_name = f"{name}"
                with tracer.start_as_current_span(span_name) as span:
                    for tag in tags:
                        span.set_attribute(f"tag.{tag}", True)
                    for k, v in metadata.items():
                        if isinstance(v, (str, int, float, bool)):
                            span.set_attribute(f"metadata.{k}", v)

                    # 提取并记录 state 信息
                    state = _extract_state_from_args(func, args, kwargs)
                    user_info = _extract_user_info(state)
                    for k, v in user_info.items():
                        span.set_attribute(f"user.{k}", v)

                    print(f"[Decorator DEBUG] 使用 OTel tracer 创建 span: {name}")

                    try:
                        result = await func(*args, **kwargs)
                        span.set_attribute("status", "success")
                        return result
                    except Exception as e:
                        span.set_attribute("status", "error")
                        span.record_exception(e)
                        raise
            else:
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            manager = get_tracing_manager()
            tracer = manager.get_tracer() if manager else None

            if tracer:
                span_name = f"{name}"
                with tracer.start_as_current_span(span_name) as span:
                    for tag in tags:
                        span.set_attribute(f"tag.{tag}", True)
                    for k, v in metadata.items():
                        if isinstance(v, (str, int, float, bool)):
                            span.set_attribute(f"metadata.{k}", v)

                    # 提取并记录 state 信息
                    state = _extract_state_from_args(func, args, kwargs)
                    user_info = _extract_user_info(state)
                    for k, v in user_info.items():
                        span.set_attribute(f"user.{k}", v)

                    try:
                        result = func(*args, **kwargs)
                        span.set_attribute("status", "success")
                        return result
                    except Exception as e:
                        span.set_attribute("status", "error")
                        span.record_exception(e)
                        raise
            else:
                return func(*args, **kwargs)

        sync_wrapper.__wrapped__ = func
        return async_wrapper if is_async else sync_wrapper

    return decorator


def trace_node(node_name: str):
    """用于 LangGraph 节点 - 支持同步和异步"""

    def decorator(func: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(func)

        # OTel 优先，只有 OTel 未启用才降级到 LangSmith
        if TracingConfig.USE_OTEL:
            pass  # 走下面的 OTel 逻辑
        elif _langsmith_available and _langsmith_traceable:
            print(f"[Decorator DEBUG] 使用 LangSmith traceable: node.{node_name}")
            return _langsmith_traceable(name=f"node.{node_name}", tags=["langgraph", "node"])(func)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            manager = get_tracing_manager()
            tracer = manager.get_tracer() if manager else None

            if tracer:
                span_name = f"node.{node_name}"
                with tracer.start_as_current_span(span_name) as span:
                    span.set_attribute("langgraph.node_name", node_name)
                    span.set_attribute("langgraph.node_type", "async")

                    # 智能提取 state
                    state = _extract_state_from_args(func, args, kwargs)
                    user_info = _extract_user_info(state)
                    for k, v in user_info.items():
                        span.set_attribute(f"user.{k}", v)

                    # 记录输入消息数量
                    messages = state.get("messages", [])
                    span.set_attribute("input.message_count", len(messages))

                    try:
                        result = await func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))

                        # 记录输出状态
                        if isinstance(result, dict):
                            output_messages = result.get("messages", [])
                            span.set_attribute("output.message_count", len(output_messages))

                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR))
                        span.record_exception(e)
                        raise
            else:
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            manager = get_tracing_manager()
            tracer = manager.get_tracer() if manager else None

            if tracer:
                span_name = f"node.{node_name}"
                with tracer.start_as_current_span(span_name) as span:
                    span.set_attribute("langgraph.node_name", node_name)
                    span.set_attribute("langgraph.node_type", "sync")

                    # 智能提取 state
                    state = _extract_state_from_args(func, args, kwargs)
                    user_info = _extract_user_info(state)
                    for k, v in user_info.items():
                        span.set_attribute(f"user.{k}", v)

                    # 记录输入消息数量
                    messages = state.get("messages", [])
                    span.set_attribute("input.message_count", len(messages))

                    try:
                        result = func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))

                        # 记录输出状态
                        if isinstance(result, dict):
                            output_messages = result.get("messages", [])
                            span.set_attribute("output.message_count", len(output_messages))

                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR))
                        span.record_exception(e)
                        raise
            else:
                return func(*args, **kwargs)

        sync_wrapper.__wrapped__ = func
        sync_wrapper._is_trace_node = True
        sync_wrapper._node_name = node_name
        return async_wrapper if is_async else sync_wrapper

    return decorator


def trace_graph(name: str = "graph.invoke", kind: str = "client"):
    """包装整个图执行，生成 root span，降低业务代码侵入性"""

    def decorator(func: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(func)

        if TracingConfig.USE_OTEL:
            pass  # 走下面的 OTel 逻辑
        elif _langsmith_available and _langsmith_traceable:
            print(f"[Decorator DEBUG] 使用 LangSmith traceable: {name}")
            return _langsmith_traceable(name=name, tags=["langgraph", "graph"])(func)

        def _apply_attributes(span, func, args, kwargs):
            span.set_attribute("langgraph.graph_name", name)
            span.set_attribute("langgraph.graph_kind", kind)
            sig = inspect.signature(func)
            try:
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
                user_id = bound.arguments.get("user_id") or kwargs.get("user_id") or "anonymous"
                session_id = bound.arguments.get("session_id") or kwargs.get("session_id") or "default"
                message = bound.arguments.get("user_message") or kwargs.get("user_message") or ""
                span.set_attribute("user.user_id", str(user_id))
                span.set_attribute("user.session_id", str(session_id))
                if message:
                    span.set_attribute("user.user_message", str(message)[:100])
            except Exception:
                pass

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            manager = get_tracing_manager()
            tracer = manager.get_tracer() if manager else None

            if tracer:
                with tracer.start_as_current_span(name) as span:
                    _apply_attributes(span, func, args, kwargs)
                    try:
                        result = await func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR))
                        span.record_exception(e)
                        raise
            else:
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            manager = get_tracing_manager()
            tracer = manager.get_tracer() if manager else None

            if tracer:
                with tracer.start_as_current_span(name) as span:
                    _apply_attributes(span, func, args, kwargs)
                    try:
                        result = func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR))
                        span.record_exception(e)
                        raise
            else:
                return func(*args, **kwargs)

        sync_wrapper.__wrapped__ = func
        return async_wrapper if is_async else sync_wrapper

    return decorator


def trace_tool(tool_name: str):
    """用于工具函数 - 支持同步和异步"""

    def decorator(func: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(func)

        # OTel 优先，只有 OTel 未启用才降级到 LangSmith
        if TracingConfig.USE_OTEL:
            pass  # 走下面的 OTel 逻辑
        elif _langsmith_available and _langsmith_traceable:
            print(f"[Decorator DEBUG] 使用 LangSmith traceable: tool.{tool_name}")
            return _langsmith_traceable(name=f"tool.{tool_name}", tags=["langgraph", "tool"])(func)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            manager = get_tracing_manager()
            tracer = manager.get_tracer() if manager else None

            if tracer:
                span_name = f"tool.{tool_name}"
                with tracer.start_as_current_span(span_name) as span:
                    span.set_attribute("tool.name", tool_name)
                    span.set_attribute("tool.category", "chatbot")

                    # 安全提取参数
                    try:
                        sig = inspect.signature(func)
                        bound = sig.bind(*args, **kwargs)
                        bound.apply_defaults()
                        safe_args = {
                            k: str(v)[:100]  # 限制长度
                            for k, v in bound.arguments.items()
                            if k != 'self' and not k.startswith('_')
                        }
                        if safe_args:
                            span.add_event("tool.arguments", {"args": safe_args})
                    except Exception:
                        pass  # 参数提取失败不影响执行

                    try:
                        result = await func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))

                        # 记录结果摘要
                        result_str = str(result)[:200]
                        span.set_attribute("result.preview", result_str)
                        span.set_attribute("result.length", len(str(result)))

                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR))
                        span.record_exception(e)
                        raise
            else:
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            manager = get_tracing_manager()
            tracer = manager.get_tracer() if manager else None

            if tracer:
                span_name = f"tool.{tool_name}"
                with tracer.start_as_current_span(span_name) as span:
                    span.set_attribute("tool.name", tool_name)
                    span.set_attribute("tool.category", "chatbot")

                    # 安全提取参数
                    try:
                        sig = inspect.signature(func)
                        bound = sig.bind(*args, **kwargs)
                        bound.apply_defaults()
                        safe_args = {
                            k: str(v)[:100]
                            for k, v in bound.arguments.items()
                            if k != 'self' and not k.startswith('_')
                        }
                        if safe_args:
                            span.add_event("tool.arguments", {"args": safe_args})
                    except Exception:
                        pass

                    try:
                        result = func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))

                        result_str = str(result)[:200]
                        span.set_attribute("result.preview", result_str)
                        span.set_attribute("result.length", len(str(result)))

                        return result
                    except Exception as e:
                        span.set_status(Status(StatusCode.ERROR))
                        span.record_exception(e)
                        raise
            else:
                return func(*args, **kwargs)

        sync_wrapper.__wrapped__ = func
        sync_wrapper._is_trace_tool = True
        sync_wrapper._tool_name = tool_name
        return async_wrapper if is_async else sync_wrapper

    return decorator
