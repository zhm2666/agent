"""
OpenTelemetry initialization for agent_demo.
Provides distributed tracing and metrics for LangGraph + FastAPI.
"""
import os
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
# from opentelemetry.propagators.tracecontext import TraceContextTextMapPropagator
# 新版（1.20+）正确路径
# from opentelemetry.sdk.trace.propagation.tracecontext import TraceContextTextMapPropagator

from typing import Optional, Callable

# Singleton shutdown functions
_tracer_shutdown: Optional[Callable] = None
_meter_shutdown: Optional[Callable] = None


def _clean_endpoint(endpoint: str) -> str:
    """剥掉 http:// 或 https:// 前缀，gRPC exporter 不需要"""
    for prefix in ("http://", "https://"):
        if endpoint.startswith(prefix):
            return endpoint[len(prefix):]
    return endpoint


def init_opentelemetry(
    service_name: str = "agent-demo",
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
) -> Callable:
    """
    Initialize OpenTelemetry tracing and metrics.

    Args:
        service_name: Name of the service
        service_version: Version of the service
        otlp_endpoint: OTLP collector endpoint (e.g., "http://localhost:4317" or "localhost:4317")

    Returns:
        Shutdown function to be called on application shutdown
    """
    global _tracer_shutdown, _meter_shutdown

    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })

    # Initialize TracerProvider
    # 不指定 sampler，默认就是 ParentBased(AlwaysOn)，全采样
    tracer_provider = TracerProvider(resource=resource)

    # Add OTLP trace exporter if endpoint is provided
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            clean_endpoint = _clean_endpoint(otlp_endpoint)
            otlp_exporter = OTLPSpanExporter(
                endpoint=clean_endpoint,
                insecure=True,
            )
            tracer_provider.add_span_processor(
                BatchSpanProcessor(otlp_exporter)
            )
        except Exception as e:
            print(f"Warning: Failed to initialize OTLP trace exporter: {e}")

    trace.set_tracer_provider(tracer_provider)

    # Initialize MeterProvider
    meter_provider = MeterProvider(resource=resource)

    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
            clean_endpoint = _clean_endpoint(otlp_endpoint)
            metric_exporter = OTLPMetricExporter(
                endpoint=clean_endpoint,
                insecure=True,
            )
            metric_reader = PeriodicExportingMetricReader(
                metric_exporter,
                export_interval_millis=5000,
            )
            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[metric_reader],
            )
        except Exception as e:
            print(f"Warning: Failed to initialize OTLP metric exporter: {e}")

    metrics.set_meter_provider(meter_provider)

    # # Initialize propagator (W3C TraceContext + Baggage)
    # set_global_textmap(
    #     CompositePropagator([
    #         TraceContextTextMapPropagator(),
    #         W3CBaggagePropagator(),
    #     ])
    # )

    def shutdown():
        """Shutdown both providers."""
        tracer_provider.shutdown()
        meter_provider.shutdown()

    _tracer_shutdown = shutdown
    return shutdown


def get_tracer(name: str = "agent-demo") -> trace.Tracer:
    """Get a tracer instance."""
    return trace.get_tracer(name)


def get_meter(name: str = "agent-demo") -> metrics.Meter:
    """Get a meter instance."""
    return metrics.get_meter(name)