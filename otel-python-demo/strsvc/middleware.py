"""
Middleware pattern for adding tracing and metrics to business logic.
Decorator pattern that wraps bus operations with observability.
"""
from opentelemetry import trace, metrics
from typing import Callable, Any


class TraceMiddleware:
    """
    Tracing middleware that wraps bus operations with spans.
    Automatically creates spans for each operation.
    """

    def __init__(self, bus: Any, tracer: trace.Tracer):
        self._bus = bus
        self._tracer = tracer

    def __getattr__(self, name: str) -> Callable:
        """Proxy all method calls through tracing."""
        if hasattr(self._bus, name):
            original_method = getattr(self._bus, name)
            if callable(original_method):
                return self._create_traced_method(name, original_method)
        raise AttributeError(f"'{type(self._bus).__name__}' has no attribute '{name}'")

    def _create_traced_method(self, name: str, original_method: Callable) -> Callable:
        """Create a traced version of a method."""
        def traced_method(*args, **kwargs):
            with self._tracer.start_as_current_span(f"bus.{name}") as span:
                span.set_attribute("bus.operation", name)
                span.set_attribute("bus.target", f"{type(self._bus).__name__}.{name}")

                # Add input arguments as attributes
                if args:
                    span.set_attribute("input.args", str(args))
                if kwargs:
                    span.set_attribute("input.kwargs", str(kwargs))

                result = original_method(*args, **kwargs)

                # Record result
                span.set_attribute("output.result", str(result))
                return result

        traced_method.__name__ = name
        traced_method.__doc__ = original_method.__doc__
        return traced_method


class MetricMiddleware:
    """
    Metrics middleware that records operation counts and durations.
    Tracks success/failure rates and latency distributions.
    """

    def __init__(self, bus: Any, meter: metrics.Meter):
        self._bus = bus
        self._meter = meter

        self._operation_counter = meter.create_counter(
            name="bus_operations_total",
            description="Total number of bus operations",
            unit="1",
        )

        self._operation_histogram = meter.create_histogram(
            name="bus_operation_duration_seconds",
            description="Bus operation duration in seconds",
            unit="s",
        )

        self._error_counter = meter.create_counter(
            name="bus_errors_total",
            description="Total number of bus operation errors",
            unit="1",
        )

    def __getattr__(self, name: str) -> Callable:
        """Proxy all method calls through metrics collection."""
        if hasattr(self._bus, name):
            original_method = getattr(self._bus, name)
            if callable(original_method):
                return self._create_metricked_method(name, original_method)
        raise AttributeError(f"'{type(self._bus).__name__}' has no attribute '{name}'")

    def _create_metricked_method(self, name: str, original_method: Callable) -> Callable:
        """Create a metrics-enabled version of a method."""
        def metricked_method(*args, **kwargs):
            import time

            self._operation_counter.add(1, {"operation": name})

            start_time = time.perf_counter()
            error = None
            result = None

            try:
                result = original_method(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                self._error_counter.add(1, {"operation": name, "error_type": type(e).__name__})
                raise
            finally:
                duration = time.perf_counter() - start_time
                attributes = {
                    "operation": name,
                    "status": "error" if error else "success",
                }
                self._operation_histogram.record(duration, attributes)

        metricked_method.__name__ = name
        metricked_method.__doc__ = original_method.__doc__
        return metricked_method


def wrap_with_tracing(bus: Any, tracer: trace.Tracer) -> TraceMiddleware:
    """Wrap a bus with tracing middleware."""
    return TraceMiddleware(bus, tracer)


def wrap_with_metrics(bus: Any, meter: metrics.Meter) -> MetricMiddleware:
    """Wrap a bus with metrics middleware."""
    return MetricMiddleware(bus, meter)


def wrap_with_all(bus: Any, tracer: trace.Tracer, meter: metrics.Meter) -> MetricMiddleware:
    """
    Wrap a bus with both tracing and metrics.
    Returns MetricMiddleware which also includes tracing.
    """
    traced_bus = TraceMiddleware(bus, tracer)
    return MetricMiddleware(traced_bus, meter)
