"""
Middleware pattern for addsvc.
Provides tracing and metrics for business operations.
"""
from opentelemetry import trace, metrics
from typing import Callable, Any


class TraceMiddleware:
    """Tracing middleware for addsvc operations."""

    def __init__(self, bus: Any, tracer: trace.Tracer):
        self._bus = bus
        self._tracer = tracer

    def __getattr__(self, name: str) -> Callable:
        if hasattr(self._bus, name):
            original_method = getattr(self._bus, name)
            if callable(original_method):
                return self._create_traced_method(name, original_method)
        raise AttributeError(f"'{type(self._bus).__name__}' has no attribute '{name}'")

    def _create_traced_method(self, name: str, original_method: Callable) -> Callable:
        def traced_method(*args, **kwargs):
            with self._tracer.start_as_current_span(f"bus.{name}") as span:
                span.set_attribute("bus.operation", name)
                result = original_method(*args, **kwargs)
                span.set_attribute("result", str(result))
                return result
        traced_method.__name__ = name
        return traced_method


class MetricMiddleware:
    """Metrics middleware for addsvc operations."""

    def __init__(self, bus: Any, meter: metrics.Meter):
        self._bus = bus
        self._meter = meter

        self._operation_counter = meter.create_counter(
            name="addsvc_operations_total",
            description="Total number of addsvc operations",
            unit="1",
        )

        self._operation_histogram = meter.create_histogram(
            name="addsvc_operation_duration_seconds",
            description="Add operation duration in seconds",
            unit="s",
        )

    def __getattr__(self, name: str) -> Callable:
        if hasattr(self._bus, name):
            original_method = getattr(self._bus, name)
            if callable(original_method):
                return self._create_metricked_method(name, original_method)
        raise AttributeError(f"'{type(self._bus).__name__}' has no attribute '{name}'")

    def _create_metricked_method(self, name: str, original_method: Callable) -> Callable:
        def metricked_method(*args, **kwargs):
            import time
            self._operation_counter.add(1, {"operation": name})
            start_time = time.perf_counter()
            try:
                return original_method(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start_time
                self._operation_histogram.record(duration, {"operation": name})
        metricked_method.__name__ = name
        return metricked_method


def wrap_with_all(bus: Any, tracer: trace.Tracer, meter: metrics.Meter) -> MetricMiddleware:
    """Wrap bus with both tracing and metrics."""
    traced_bus = TraceMiddleware(bus, tracer)
    return MetricMiddleware(traced_bus, meter)
