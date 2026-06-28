"""
OpenTelemetry initialization utilities for distributed tracing.
Provides standardized initialization for TracerProvider and MeterProvider.
"""
import os
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import AlwaysOnSampler
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.propagate import set_global_textmap_propaginator
from opentelemetry.propagator.composite import CompositePropagator
from opentelemetry.propagator.tracecontext import TraceContextTextMapPropagator
from opentelemetry.propagators.baggage import BaggagePropagator
from typing import Optional, Callable


def init_tracer_provider(
    service_name: str,
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    export_batch_size: int = 8192,
) -> Callable[[], None]:
    """
    Initialize the global TracerProvider with OTLP exporter.

    Args:
        service_name: Name of the service for identification
        service_version: Version of the service
        otlp_endpoint: OTLP collector endpoint (e.g., "http://localhost:4317")
        export_batch_size: Number of spans to batch before export

    Returns:
        Shutdown function to call when shutting down the provider
    """
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })

    tracer_provider = TracerProvider(
        sampler=AlwaysOnSampler(),
        resource=resource,
    )

    if otlp_endpoint:
        try:
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                insecure=True,
            )
            span_processor = BatchSpanProcessor(
                otlp_exporter,
                max_export_batch_size=export_batch_size,
            )
            tracer_provider.add_span_processor(span_processor)
        except Exception as e:
            print(f"Warning: Failed to initialize OTLP exporter: {e}")

    trace.set_tracer_provider(tracer_provider)

    def shutdown():
        return tracer_provider.shutdown()

    return shutdown


def init_meter_provider(
    service_name: str,
    service_version: str = "1.0.0",
    otlp_endpoint: Optional[str] = None,
    export_interval_ms: int = 5000,
) -> Callable[[], None]:
    """
    Initialize the global MeterProvider with OTLP exporter.

    Args:
        service_name: Name of the service
        service_version: Version of the service
        otlp_endpoint: OTLP collector endpoint
        export_interval_ms: Interval between metric exports in milliseconds

    Returns:
        Shutdown function
    """
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
    })

    if otlp_endpoint:
        try:
            metric_exporter = OTLPMetricExporter(
                endpoint=otlp_endpoint,
                insecure=True,
            )
            metric_reader = PeriodicExportingMetricReader(
                metric_exporter,
                export_interval_millis=export_interval_ms,
            )
        except Exception as e:
            print(f"Warning: Failed to initialize OTLP metric exporter: {e}")
            metric_reader = None
    else:
        metric_reader = None

    meter_provider = MeterProvider(
        resource=resource,
        metric_reader=metric_reader,
    )

    metrics.set_meter_provider(meter_provider)

    def shutdown():
        return meter_provider.shutdown()

    return shutdown


def init_propagator() -> None:
    """
    Initialize the global propagator for trace context propagation.
    Supports W3C TraceContext and Baggage propagation.
    """
    set_global_textmap_propaginator(CompositePropagator([
        TraceContextTextMapPropagator(),
        BaggagePropagator(),
    ]))


def get_tracer(name: str) -> trace.Tracer:
    """
    Get a tracer instance for creating spans.

    Args:
        name: Name of the tracer (usually module name)

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """
    Get a meter instance for creating metrics.

    Args:
        name: Name of the meter (usually module name)

    Returns:
        Meter instance
    """
    return metrics.get_meter(name)
