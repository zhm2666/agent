"""
OpenTelemetry initialization for agent_demo.
Provides distributed tracing and metrics for LangGraph + FastAPI.
"""
import os
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import AlwaysOnSampler
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.propagate import set_global_textmap_propaginator
from opentelemetry.propagator.tracecontext import TraceContextTextMapPropagator
from opentelemetry.propagators.baggage import BaggagePropagator

from typing import Optional, Callable

# Singleton shutdown functions
_tracer_shutdown: Optional[Callable] = None
_meter_shutdown: Optional[Callable] = None


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
        otlp_endpoint: OTLP collector endpoint (e.g., "http://localhost:4317")

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
    tracer_provider = TracerProvider(
        sampler=AlwaysOnSampler(),
        resource=resource,
    )

    # Add OTLP exporter if endpoint is provided
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
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
            metric_exporter = OTLPMetricExporter(
                endpoint=otlp_endpoint,
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

    # Initialize propagator (W3C TraceContext + Baggage)
    set_global_textmap_propaginator(
        CompositePropagator([
            TraceContextTextMapPropagator(),
            BaggagePropagator(),
        ])
    )

    def shutdown():
        """Shutdown both providers."""
        tracer_provider.shutdown()
        meter_provider.shutdown()

    _tracer_shutdown = shutdown
    return shutdown


class CompositePropagator:
    """Composite propagator combining multiple propagators."""

    def __init__(self, propagators):
        self.propagators = propagators

    def inject(self, carrier, context=None):
        for propagator in self.propagators:
            propagator.inject(carrier, context)

    def extract(self, carrier, context=None):
        for propagator in self.propagators:
            context = propagator.extract(carrier, context)
        return context


def get_tracer(name: str = "agent-demo") -> trace.Tracer:
    """Get a tracer instance."""
    return trace.get_tracer(name)


def get_meter(name: str = "agent-demo") -> metrics.Meter:
    """Get a meter instance."""
    return metrics.get_meter(name)
