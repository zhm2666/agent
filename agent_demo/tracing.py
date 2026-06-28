"""
OpenTelemetry + LangSmith 双重追踪配置。
可以同时将追踪数据发送到 OTEL Collector 和 LangSmith。

使用方法:
1. 设置环境变量 .env:
   - OTLP_ENDPOINT=http://localhost:4317
   - LANGSMITH_API_KEY=your-key
   - LANGSMITH_PROJECT=agent-demo
   - USE_LANGSMITH=true
   - USE_OTEL=true
"""
import os
from typing import Optional, Callable
from functools import wraps

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import AlwaysOnSampler
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION

# LangSmith imports
_langsmith_available = False
try:
    from langsmith.run_helpers import traceable as langsmith_traceable
    from langsmith import Client as LangSmithClient
    _langsmith_available = True
except ImportError:
    langsmith_traceable = None
    LangSmithClient = None


class TracingManager:
    """
    统一追踪管理器，支持 OpenTelemetry 和 LangSmith 双轨输出。
    """

    def __init__(
        self,
        service_name: str = "agent-demo",
        otlp_endpoint: Optional[str] = None,
        use_langsmith: bool = True,
    ):
        self.service_name = service_name
        self.otlp_endpoint = otlp_endpoint
        self.use_langsmith = use_langsmith and _langsmith_available

        self._tracer_provider: Optional[TracerProvider] = None
        self._tracer: Optional[trace.Tracer] = None
        self._langsmith_client: Optional = None

        self._init_opentelemetry()
        self._init_langsmith()

    def _init_opentelemetry(self):
        """初始化 OpenTelemetry"""
        if not self.otlp_endpoint:
            return

        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            resource = Resource.create({
                SERVICE_NAME: self.service_name,
                SERVICE_VERSION: "1.0.0",
            })

            self._tracer_provider = TracerProvider(
                sampler=AlwaysOnSampler(),
                resource=resource,
            )

            otlp_exporter = OTLPSpanExporter(
                endpoint=self.otlp_endpoint,
                insecure=True,
            )

            self._tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter)
            )

            trace.set_tracer_provider(self._tracer_provider)
            self._tracer = trace.get_tracer(self.service_name)

            print(f"✅ OpenTelemetry initialized (endpoint: {self.otlp_endpoint})")

        except Exception as e:
            print(f"⚠️ OpenTelemetry initialization failed: {e}")

    def _init_langsmith(self):
        """初始化 LangSmith"""
        if not self.use_langsmith:
            return

        if not os.getenv("LANGSMITH_API_KEY"):
            print("⚠️ LANGSMITH_API_KEY not set, LangSmith tracing disabled")
            self.use_langsmith = False
            return

        try:
            # 设置环境变量
            os.environ["LANGSMITH_TRACING"] = "true"

            self._langsmith_client = LangSmithClient()
            print("✅ LangSmith initialized")

        except Exception as e:
            print(f"⚠️ LangSmith initialization failed: {e}")
            self.use_langsmith = False

    def get_tracer(self) -> trace.Tracer:
        """获取 OpenTelemetry tracer"""
        return self._tracer or trace.get_tracer(self.service_name)

    def trace(self, name: str, tags: list = None):
        """
        追踪装饰器，同时在 OTEL 和 LangSmith 中创建 trace。

        Args:
            name: trace 名称
            tags: LangSmith 标签
        """
        def decorator(func):
            # OpenTelemetry 追踪
            otel_decorated = self._otel_trace(name)(func)

            # LangSmith 追踪（如果可用）
            if self.use_langsmith and langsmith_traceable:
                return langsmith_traceable(
                    name=name,
                    tags=tags or [],
                )(otel_decorated)

            return otel_decorated

        return decorator

    def _otel_trace(self, name: str):
        """OpenTelemetry 追踪装饰器"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                tracer = self.get_tracer()
                with tracer.start_as_current_span(name) as span:
                    try:
                        result = func(*args, **kwargs)
                        span.set_attribute("status", "success")
                        return result
                    except Exception as e:
                        span.set_attribute("status", "error")
                        span.record_exception(e)
                        raise
            return wrapper
        return decorator

    def shutdown(self):
        """关闭追踪器"""
        if self._tracer_provider:
            self._tracer_provider.shutdown()


# 全局实例
_tracing_manager: Optional[TracingManager] = None


def init_tracing(
    service_name: str = "agent-demo",
    otlp_endpoint: Optional[str] = None,
    use_langsmith: bool = True,
) -> TracingManager:
    """
    初始化追踪系统。

    Args:
        service_name: 服务名称
        otlp_endpoint: OTLP 收集器地址
        use_langsmith: 是否启用 LangSmith

    Returns:
        TracingManager 实例
    """
    global _tracing_manager

    _tracing_manager = TracingManager(
        service_name=service_name,
        otlp_endpoint=otlp_endpoint,
        use_langsmith=use_langsmith,
    )

    return _tracing_manager


def get_tracing_manager() -> Optional[TracingManager]:
    """获取全局追踪管理器"""
    return _tracing_manager


# ============ 便捷装饰器 ============
def trace_node(name: str = None, tags: list = None):
    """
    追踪 LangGraph 节点的装饰器。
    同时输出到 OpenTelemetry 和 LangSmith（如果已初始化）。

    用法:
        @trace_node("translate")
        def translate(state):
            ...
    """
    def decorator(func):
        node_name = name or func.__name__

        # 获取全局 tracing manager
        manager = get_tracing_manager()

        if manager and manager.use_langsmith and langsmith_traceable:
            # 使用 LangSmith 追踪
            return langsmith_traceable(
                name=f"node.{node_name}",
                tags=tags or ["langgraph-node"],
            )(func)

        # 降级到 OpenTelemetry
        if manager:
            tracer = manager.get_tracer()
            @wraps(func)
            def traced(*args, **kwargs):
                with tracer.start_as_current_span(f"node.{node_name}") as span:
                    result = func(*args, **kwargs)
                    return result
            return traced

        # 无追踪
        return func

    return decorator
