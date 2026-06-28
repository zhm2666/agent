"""
Trace Basic - Basic single-process tracing demonstration.
Shows how to create spans, set attributes, record events, and link spans.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from otel_utils import init_tracer_provider, get_tracer


def main():
    # Initialize tracer provider with optional OTLP endpoint
    otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")
    shutdown = init_tracer_provider(
        service_name="trace-basic",
        service_version="1.0.0",
        otlp_endpoint=otlp_endpoint,
    )

    # Get tracer for this module
    tracer = get_tracer("trace-basic")

    # Start a root span
    with tracer.start_as_current_span("trace-basic-operation") as root_span:
        root_span.set_attribute("operation.type", "demo")
        root_span.set_attribute("user.id", "user-123")

        # Add an event (log-like annotation)
        root_span.add_event("Starting operation", {"component": "trace-basic"})

        # Create a child span for calculation
        with tracer.start_as_current_span("calculation-span") as calc_span:
            calc_span.set_attribute("calculation.type", "sum")
            result = 0

            try:
                a = 10
                b = 20
                calc_span.set_attribute("input.a", a)
                calc_span.set_attribute("input.b", b)

                result = a + b

                calc_span.set_attribute("result", result)
                calc_span.add_event("Calculation completed")

            except Exception as e:
                calc_span.set_status(Status(StatusCode.ERROR, str(e)))
                calc_span.record_exception(e)
                raise

        # Create another child span for string processing
        with tracer.start_as_current_span("string-processing-span") as str_span:
            str_span.set_attribute("string.input", "hello world")
            upper = "HELLO WORLD"
            str_span.set_attribute("string.output", upper)
            str_span.set_attribute("string.length", len(upper))

        # Simulate an error scenario
        with tracer.start_as_current_span("error-scenario-span") as error_span:
            error_span.set_attribute("scenario.type", "error-demo")
            try:
                raise ValueError("Simulated error for demonstration")
            except ValueError as e:
                error_span.set_status(Status(StatusCode.ERROR, "ValueError occurred"))
                error_span.record_exception(e)
                error_span.add_event("Caught exception", {"error.type": "ValueError"})

        root_span.add_event("All operations completed")

    print("Trace basic demo completed successfully!")
    print(f"Trace ID: {get_current_trace_id()}")

    # Shutdown the provider
    shutdown()


def get_current_trace_id() -> str:
    """Get the current trace ID as a hex string."""
    span = trace.get_current_span()
    if span:
        ctx = span.get_span_context()
        if ctx.is_valid:
            return format(ctx.trace_id, '032x')
    return "no-active-trace"


if __name__ == "__main__":
    main()
