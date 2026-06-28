"""
统一分布式追踪模块

支持 OpenTelemetry 和 LangSmith 双轨输出。
在 LangGraph 节点、LLM 调用、数据库操作中自动创建 trace span。

使用方式:
    from .tracing import traceable, trace_node

    @traceable(name="agent.analyze", tags=["agent"])
    def analyze(self, ...):
        ...

    @trace_node("product_identification")
    def product_identification_node(state, ...):
        ...
"""

import os
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

import dotenv

# 加载 .env 文件
dotenv.load_dotenv()

# LangSmith 可用性检测
_langsmith_available = False
try:
    from langsmith.run_helpers import traceable as _langsmith_traceable
    from langsmith import Client as _LangSmithClient
    _langsmith_available = True
except ImportError:
    _langsmith_traceable = None
    _LangSmithClient = None

# OpenTelemetry 可用性检测
_otel_available = False
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.trace.sampling import AlwaysOnSampler
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME
    _otel_available = True
except ImportError:
    trace = None
    metrics = None
    TracerProvider = None
    BatchSpanProcessor = None
    AlwaysOnSampler = None
    Resource = None
    SERVICE_NAME = None


# ============ 配置 ============

class TracingConfig:
    """追踪配置"""
    # LangSmith 配置
    LANGSMITH_TRACING: bool = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "prediction-agent")
    
    # OpenTelemetry 配置
    USE_OTEL: bool = os.getenv("USE_OTEL", "false").lower() == "true"
    OTLP_ENDPOINT: str = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")
    SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "prediction-agent")
    
    @classmethod
    def is_enabled(cls) -> bool:
        return cls.LANGSMITH_TRACING or cls.USE_OTEL


# ============ 追踪管理器 ============

class TracingManager:
    """
    统一追踪管理器
    
    同时支持 OpenTelemetry 和 LangSmith：
    - OpenTelemetry: spans → OTLP → Collector → Jaeger
    - LangSmith: 自动追踪 → LangSmith Cloud
    """
    
    _instance: Optional["TracingManager"] = None
    
    def __init__(
        self,
        service_name: str = "prediction-agent",
        otlp_endpoint: Optional[str] = None,
        use_langsmith: bool = True,
    ):
        self.service_name = service_name
        self.otlp_endpoint = otlp_endpoint or TracingConfig.OTLP_ENDPOINT
        self.use_langsmith = use_langsmith and TracingConfig.LANGSMITH_TRACING
        
        self._tracer_provider: Optional[Any] = None
        self._tracer: Optional[Any] = None
        self._meter: Optional[Any] = None
        
        self._init_opentelemetry()
        self._init_langsmith()
        
        TracingManager._instance = self
    
    def _init_opentelemetry(self) -> None:
        """初始化 OpenTelemetry"""
        if not TracingConfig.USE_OTEL or not _otel_available:
            return
        
        try:
            from opentelemetry.sdk.resources import Resource, SERVICE_NAME
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.sdk.trace.sampling import AlwaysOnSampler
            
            # 根据 endpoint 协议选择 exporter 类型
            endpoint = self.otlp_endpoint
            is_grpc = endpoint.startswith("grpc://") or ":4317" in endpoint
            is_http = endpoint.startswith("http://") or endpoint.startswith("https://") or ":4318" in endpoint
            
            if is_grpc or (not is_http and ":4317" in endpoint):
                # gRPC exporter (默认 4317)
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
                exporter_class = OTLPSpanExporter
                insecure = True
            else:
                # HTTP exporter (4318)
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
                exporter_class = OTLPSpanExporter
                insecure = True
            
            resource = Resource.create({
                SERVICE_NAME: self.service_name,
                "service.version": "1.0.0",
                "deployment.environment": os.getenv("ENVIRONMENT", "development"),
            })
            
            self._tracer_provider = TracerProvider(
                sampler=AlwaysOnSampler(),
                resource=resource,
            )
            
            # 添加 OTLP 导出器
            if is_grpc or ":4317" in endpoint:
                # gRPC
                otlp_exporter = exporter_class(
                    endpoint=endpoint,
                    insecure=insecure,
                )
            else:
                # HTTP - 确保 endpoint 格式正确
                if not endpoint.startswith("http"):
                    endpoint = f"http://{endpoint}"
                otlp_exporter = exporter_class(endpoint=endpoint)
            
            self._tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter)
            )
            
            trace.set_tracer_provider(self._tracer_provider)
            self._tracer = trace.get_tracer(self.service_name)
            
            # 初始化 Meter
            self._meter = None
            
            print(f"[Tracing] OpenTelemetry initialized (endpoint: {endpoint}, protocol: {'gRPC' if is_grpc else 'HTTP'})")
            
        except ImportError as e:
            print(f"[Tracing] OpenTelemetry optional dependencies not installed: {e}")
        except Exception as e:
            print(f"[Tracing] OpenTelemetry initialization failed: {e}")
    
    def _init_langsmith(self) -> None:
        """初始化 LangSmith"""
        if not self.use_langsmith:
            print("[Tracing] LangSmith tracing disabled")
            return
        
        if not TracingConfig.LANGSMITH_API_KEY:
            print("[Tracing] LANGSMITH_API_KEY not set, LangSmith disabled")
            self.use_langsmith = False
            return
        
        try:
            # 设置 LangSmith 环境变量
            os.environ["LANGSMITH_TRACING"] = "true"
            
            print(f"[Tracing] LangSmith initialized (project: {TracingConfig.LANGSMITH_PROJECT})")
            
        except Exception as e:
            print(f"[Tracing] LangSmith initialization failed: {e}")
            self.use_langsmith = False
    
    def get_tracer(self):
        """获取 OpenTelemetry tracer"""
        if self._tracer:
            return self._tracer
        if _otel_available:
            return trace.get_tracer(self.service_name)
        return None
    
    def shutdown(self) -> None:
        """关闭追踪器"""
        if self._tracer_provider:
            self._tracer_provider.shutdown()


# 全局追踪管理器实例
_tracing_manager: Optional[TracingManager] = None


def get_tracing_manager() -> Optional[TracingManager]:
    """获取全局追踪管理器"""
    global _tracing_manager
    if _tracing_manager is None and TracingConfig.is_enabled():
        _tracing_manager = TracingManager()
    return _tracing_manager


def init_tracing(
    service_name: str = "prediction-agent",
    otlp_endpoint: Optional[str] = None,
    use_langsmith: Optional[bool] = None,
) -> TracingManager:
    """
    初始化追踪系统（全局单例）
    
    Args:
        service_name: 服务名称
        otlp_endpoint: OTLP 收集器地址
        use_langsmith: 是否启用 LangSmith（默认从环境变量读取）
    
    Returns:
        TracingManager 实例
    """
    global _tracing_manager
    
    if use_langsmith is None:
        use_langsmith = TracingConfig.LANGSMITH_TRACING
    
    _tracing_manager = TracingManager(
        service_name=service_name,
        otlp_endpoint=otlp_endpoint,
        use_langsmith=use_langsmith,
    )
    
    return _tracing_manager


# ============ 装饰器工厂 ============

def traceable(
    name: str,
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    统一追踪装饰器
    
    优先使用 LangSmith @traceable，如果不可用则降级到 OpenTelemetry。
    
    Args:
        name: trace 名称
        tags: 标签列表
        metadata: 元数据
    
    Returns:
        装饰后的函数
    
    用法:
        @traceable(name="agent.analyze", tags=["agent"])
        def analyze(self, query, ...):
            ...
    """
    tags = tags or []
    metadata = metadata or {}
    
    # 优先使用 LangSmith
    if _langsmith_available and TracingConfig.LANGSMITH_TRACING and TracingConfig.LANGSMITH_API_KEY:
        return _langsmith_traceable(
            name=name,
            tags=tags,
            metadata=metadata,
        )
    
    # 降级到 OpenTelemetry
    def otel_decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracing_manager().get_tracer() if get_tracing_manager() else None
            
            if tracer:
                with tracer.start_as_current_span(name) as span:
                    # 设置标签
                    for tag in tags:
                        span.set_attribute(f"tag.{tag}", True)
                    
                    # 设置元数据
                    for key, value in metadata.items():
                        if isinstance(value, (str, int, float, bool)):
                            span.set_attribute(f"metadata.{key}", value)
                    
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
        
        return wrapper
    
    return otel_decorator


def trace_node(node_name: str):
    """
    LangGraph 节点追踪装饰器
    
    为节点函数添加追踪，自动记录节点执行情况。
    
    Args:
        node_name: 节点名称（会显示在 trace 中）
    
    用法:
        @trace_node("product_identification")
        def product_identification_node(state, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取 state 参数
            state = kwargs.get("state") or (args[0] if args else {})
            
            # 构建 span 名称
            span_name = f"node.{node_name}"
            
            # 获取 tracer
            manager = get_tracing_manager()
            tracer = manager.get_tracer() if manager else None
            
            if tracer:
                with tracer.start_as_current_span(span_name) as span:
                    # 设置节点相关属性
                    span.set_attribute("langgraph.node_name", node_name)
                    span.set_attribute("langgraph.node_type", "node")
                    
                    # 从 state 中提取有用信息
                    user_query = state.get("user_query", "")[:100] if state else ""
                    step = state.get("prediction_state", {}).get("step", "") if state else ""
                    
                    if user_query:
                        span.set_attribute("user.query_preview", user_query)
                    if step:
                        span.set_attribute("graph.step", step)
                    
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
        
        # 保留原始函数信息（用于 LangGraph）
        wrapper.__wrapped__ = func
        return wrapper
    
    return decorator


def trace_llm_call(operation_name: str = "llm.call"):
    """
    LLM 调用追踪装饰器
    
    自动追踪 LLM API 调用，记录模型、token 数量等信息。
    
    用法:
        @trace_llm_call("product_identification.llm")
        def _call_llm(system_prompt, user_prompt):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = get_tracing_manager()
            tracer = manager.get_tracer() if manager else None
            
            if tracer:
                with tracer.start_as_current_span(operation_name) as span:
                    span.set_attribute("llm.operation", operation_name)
                    
                    try:
                        result = func(*args, **kwargs)
                        
                        # 如果返回对象有 usage 信息，记录 token 使用
                        if hasattr(result, "usage") and result.usage:
                            span.set_attribute("llm.prompt_tokens", result.usage.prompt_tokens or 0)
                            span.set_attribute("llm.completion_tokens", result.usage.completion_tokens or 0)
                            span.set_attribute("llm.total_tokens", result.usage.total_tokens or 0)
                        
                        # 记录模型
                        if hasattr(result, "model"):
                            span.set_attribute("llm.model", result.model)
                        
                        span.set_attribute("status", "success")
                        return result
                        
                    except Exception as e:
                        span.set_attribute("status", "error")
                        span.record_exception(e)
                        raise
            else:
                return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def trace_db_operation(operation: str):
    """
    数据库操作追踪装饰器
    
    用法:
        @trace_db_operation("get_product_by_code")
        def get_product_by_code(self, code):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = get_tracing_manager()
            tracer = manager.get_tracer() if manager else None
            
            if tracer:
                with tracer.start_as_current_span(f"db.{operation}") as span:
                    span.set_attribute("db.operation", operation)
                    span.set_attribute("db.system", "mysql")
                    
                    # 尝试提取表名和关键参数
                    if args and len(args) > 1:
                        # 第一个参数通常是 self，第二个是主键或关键参数
                        key_param = args[1] if len(args) > 1 else kwargs.get("code", "")
                        if isinstance(key_param, str):
                            span.set_attribute("db.key_param", key_param[:50])
                    
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
        
        return wrapper
    
    return decorator


# ============ 上下文管理器（用于手动追踪）============

class TracingContext:
    """
    手动追踪上下文管理器
    
    用法:
        with TracingContext("custom_operation") as ctx:
            ctx.set_attribute("key", "value")
            # 执行操作
            ctx.set_result("success", True)
    """
    
    def __init__(self, name: str, tracer=None):
        self.name = name
        self.tracer = tracer or (get_tracing_manager().get_tracer() if get_tracing_manager() else None)
        self.span = None
    
    def __enter__(self):
        if self.tracer:
            self.span = self.tracer.start_as_current_span(self.name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            if exc_type:
                self.span.record_exception(exc_val)
                self.span.set_attribute("status", "error")
            else:
                self.span.set_attribute("status", "success")
            self.span.end()
        return False
    
    def set_attribute(self, key: str, value: Any) -> None:
        """设置 span 属性"""
        if self.span:
            self.span.set_attribute(key, value)
    
    def set_result(self, key: str, value: Any) -> None:
        """设置结果属性"""
        self.set_attribute(f"result.{key}", value)


# ============ 便捷函数 ============

def create_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    创建 span 的便捷函数
    
    用法:
        with create_span("my_operation", {"key": "value"}) as span:
            span.set_attribute("another_key", "value")
    """
    return TracingContext(name)
