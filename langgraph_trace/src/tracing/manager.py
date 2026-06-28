import os
from typing import Optional, Any
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ALWAYS_ON
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GRPCExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as HTTPExporter
from langgraph_trace.src.tracing.config import TracingConfig


class TracingManager:
    _instance: Optional["TracingManager"] = None

    def __init__(
            self,
            service_name: str = "langgraph-chatbot",
            otlp_endpoint: Optional[str] = None,
            use_langsmith: bool = True,
    ):
        self.service_name = service_name
        self.otlp_endpoint = otlp_endpoint or TracingConfig.OTLP_ENDPOINT
        self.use_langsmith = use_langsmith and TracingConfig.LANGSMITH_TRACING

        self._tracer_provider: Optional[TracerProvider] = None
        self._tracer: Optional[Any] = None

        self._init_opentelemetry()
        if self.use_langsmith:
            self._init_langsmith()

        TracingManager._instance = self

    def _init_opentelemetry(self) -> None:
        if not TracingConfig.USE_OTEL:
            print("[Tracing] USE_OTEL=false, OpenTelemetry 跳过初始化")
            return

        endpoint = self.otlp_endpoint
        # :4317 → gRPC, :4318 → HTTP
        is_grpc = ":4317" in endpoint

        print(f"[Tracing] 初始化 OpenTelemetry, endpoint={endpoint}, is_grpc={is_grpc}")

        resource = Resource.create({
            SERVICE_NAME: self.service_name,
            "service.version": "1.0.0",
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        })

        self._tracer_provider = TracerProvider(
            sampler=ALWAYS_ON,
            resource=resource,
        )

        if is_grpc:
            exporter = GRPCExporter(endpoint=endpoint, insecure=True)
            print(f"[Tracing] 使用 gRPC Exporter → {endpoint}")
        else:
            if not endpoint.startswith("http"):
                endpoint = f"http://{endpoint}"
            exporter = HTTPExporter(endpoint=endpoint)
            print(f"[Tracing] 使用 HTTP Exporter → {endpoint}")

        self._tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(self._tracer_provider)

        # 通过 provider 获取 tracer
        self._tracer = self._tracer_provider.get_tracer(self.service_name)

        print(f"[Tracing] OpenTelemetry initialized (endpoint: {endpoint}, is_grpc={is_grpc})")

    def _init_langsmith(self) -> None:
        if not TracingConfig.LANGSMITH_API_KEY:
            print("[Tracing] LANGSMITH_API_KEY missing, LangSmith disabled")
            self.use_langsmith = False
            return
        os.environ["LANGSMITH_TRACING"] = "true"
        print(f"[Tracing] LangSmith enabled (project: {TracingConfig.LANGSMITH_PROJECT})")

    def get_tracer(self):
        if self._tracer:
            return self._tracer
        # ✅ 通过 provider 获取
        if self._tracer_provider:
            return self._tracer_provider.get_tracer(self.service_name)
        return None

    def shutdown(self) -> None:
        if self._tracer_provider:
            self._tracer_provider.shutdown()


# 全局单例
_tracing_manager: Optional[TracingManager] = None


def get_tracing_manager() -> Optional[TracingManager]:
    global _tracing_manager
    if _tracing_manager is None and TracingConfig.is_enabled():
        _tracing_manager = TracingManager()
    return _tracing_manager


def init_tracing(
        service_name: str = "langgraph-chatbot",
        otlp_endpoint: Optional[str] = None,
        use_langsmith: Optional[bool] = None,
) -> TracingManager:
    global _tracing_manager
    if use_langsmith is None:
        use_langsmith = TracingConfig.LANGSMITH_TRACING
    _tracing_manager = TracingManager(
        service_name=service_name,
        otlp_endpoint=otlp_endpoint,
        use_langsmith=use_langsmith,
    )
    return _tracing_manager