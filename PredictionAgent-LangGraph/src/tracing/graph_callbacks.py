"""
LangGraph 链路拦截器（方案三，零侵入业务节点）

核心思路：
- 不修改任何现有节点、builder、agent 代码；
- 只新增这套拦截文件；
- 在 Agent 入口或调用方注册后，即可自动采集链路。

支持两路输出：
1. LangSmith（自动从环境变量读取配置）
2. OpenTelemetry（OTLP / Jaeger）

可扩展点：
- 增加自定义 span attribute；
- 接入日志平台；
- 埋点采样率控制。
"""

from __future__ import annotations

import os
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Generator, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

try:
    from langsmith import Client as _LangSmithClient
    from langsmith.run_helpers import traceable as _langsmith_traceable
    _LANGSMITH_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    _LangSmithClient = None
    _langsmith_traceable = None
    _LANGSMITH_AVAILABLE = False


@dataclass
class InterceptorConfig:
    """拦截器配置，默认从环境变量读取。"""

    service_name: str = "prediction-agent"
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    use_langsmith: bool = field(default_factory=lambda: os.getenv("LANGSMITH_TRACING", "false").lower() == "true")
    use_otel: bool = field(default_factory=lambda: os.getenv("USE_OTEL", "false").lower() == "true")
    otlp_endpoint: str = field(default_factory=lambda: os.getenv("OTLP_ENDPOINT", "http://localhost:4318"))
    langsmith_project: str = field(default_factory=lambda: os.getenv("LANGSMITH_PROJECT", "prediction-agent"))
    sample_rate: float = 1.0


class GraphTracingInterceptor:
    """
    图执行链路拦截器。

    在 graph.invoke / graph.stream 前后自动生成 root span，
    并可选记录每个节点的开始/结束。
    """

    def __init__(self, config: Optional[InterceptorConfig] = None) -> None:
        self.config = config or InterceptorConfig()
        self._tracer_provider: Optional[TracerProvider] = None
        self._langsmith_client: Optional[Any] = None

        if self.config.use_otel:
            self._init_otel()
        if self.config.use_langsmith and _LANGSMITH_AVAILABLE:
            self._init_langsmith()

    # ============ OpenTelemetry 初始化 ============

    def _init_otel(self) -> None:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HttpExporter
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise ImportError("缺少 OpenTelemetry HTTP exporter，请安装 opentelemetry-exporter-otlp-proto-http") from exc

        resource = Resource.create({
            SERVICE_NAME: self.config.service_name,
            "service.version": "1.0.0",
            "deployment.environment": self.config.environment,
        })
        self._tracer_provider = TracerProvider(resource=resource)
        endpoint = self.config.otlp_endpoint
        if not endpoint.startswith("http"):
            endpoint = f"http://{endpoint}"
        exporter = HttpExporter(endpoint=endpoint)
        self._tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(self._tracer_provider)

    # ============ LangSmith 初始化 ============

    def _init_langsmith(self) -> None:
        api_key = os.getenv("LANGSMITH_API_KEY")
        if not api_key:
            return
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGSMITH_PROJECT"] = self.config.langsmith_project
        try:
            self._langsmith_client = _LangSmithClient()
        except Exception:  # pragma: no cover - network/optional
            self._langsmith_client = None

    # ============ 公共 API ============

    @contextmanager
    def trace_graph(self, graph_name: str = "prediction-graph") -> Generator[None, None, None]:
        """
        包裹整个图执行过程，生成 root span。

        用法：
            with interceptor.trace_graph():
                result = app.invoke(state, config)
        """
        tracer = trace.get_tracer(self.config.service_name)
        with tracer.start_as_current_span(f"graph.{graph_name}") as span:
            span.set_attribute("graph.name", graph_name)
            span.set_attribute("graph.type", "langgraph")
            span.set_attribute("environment", self.config.environment)
            try:
                yield
                span.set_attribute("status", "success")
            except Exception as exc:
                span.set_attribute("status", "error")
                span.record_exception(exc)
                raise

    @contextmanager
    def trace_node(self, node_name: str) -> Generator[None, None, None]:
        """包裹单个节点执行过程。"""
        tracer = trace.get_tracer(self.config.service_name)
        with tracer.start_as_current_span(f"node.{node_name}") as span:
            span.set_attribute("langgraph.node_name", node_name)
            span.set_attribute("langgraph.node_type", "node")
            yield
            span.set_attribute("status", "success")

    def wrap_graph_method(self, graph_method: Callable) -> Callable:
        """
        将 graph.invoke / graph.stream 方法包装为带链路采集的版本。

        返回的新方法与原始方法签名一致，可直接替换使用。
        """

        def wrapper(state: Dict[str, Any], config: Optional[Dict[str, Any]] = None, **kwargs: Any):
            with self.trace_graph():
                return graph_method(state, config, **kwargs)

        wrapper.__wrapped__ = graph_method  # type: ignore[attr-defined]
        return wrapper

    def wrap_node(self, node_name: str, node_callable: Callable) -> Callable:
        """
        将单个节点函数包装为带链路采集的版本。

        不会修改原始函数，返回新函数。
        """

        def wrapper(state: Dict[str, Any], **kwargs: Any):
            with self.trace_node(node_name):
                return node_callable(state, **kwargs)

        wrapper.__wrapped__ = node_callable  # type: ignore[attr-defined]
        return wrapper

    def shutdown(self) -> None:
        """关闭追踪器，确保数据刷出。"""
        if self._tracer_provider:
            self._tracer_provider.shutdown()


# ============ 便捷函数 ============


def create_interceptor(config: Optional[InterceptorConfig] = None) -> GraphTracingInterceptor:
    """创建链路拦截器实例。"""
    return GraphTracingInterceptor(config=config)


@contextmanager
def trace_graph_execution(
    service_name: str = "prediction-agent",
    graph_name: str = "prediction-graph",
) -> Generator[GraphTracingInterceptor, None, None]:
    """
    便捷上下文管理器：自动创建拦截器并收集图执行链路。

    用法：
        with trace_graph_execution() as interceptor:
            wrapped_app = interceptor.wrap_graph_method(app.invoke)
            wrapped_app(state, config)
    """
    interceptor = create_interceptor(
        InterceptorConfig(service_name=service_name)
    )
    try:
        yield interceptor
    finally:
        interceptor.shutdown()
