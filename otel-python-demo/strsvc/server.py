"""
gRPC server for strsvc (string service).
Provides Count and Uppercode RPC endpoints with distributed tracing.
"""
import os
import sys
import grpc
from concurrent import futures
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.propagators.baggage import BaggagePropagator
from opentelemetry.trace import Status, StatusCode

from strsvc import strsvc_pb2
from strsvc import strsvc_pb2_grpc
from strsvc.bus import StrBus
from strsvc.middleware import wrap_with_all
from otel_utils import init_tracer_provider, init_meter_provider, init_propagator, get_tracer, get_meter


class StrSvcServicer(strsvc_pb2_grpc.StrServicer):
    """
    gRPC service implementation for string operations.
    Extracts trace context from incoming requests and creates child spans.
    """

    def __init__(self, bus: StrBus, tracer: trace.Tracer, propagator: BaggagePropagator):
        self.bus = bus
        self.tracer = tracer
        self.propagator = propagator

    def Count(self, request, context):
        """
        RPC endpoint for counting characters.
        Extracts trace context from gRPC metadata.
        """
        # Extract trace context from incoming metadata
        metadata = dict(context.invocation_metadata())
        carrier = {k: v for k, v in metadata.items()}

        ctx = extract(carrier)
        ctx, span = self.tracer.start_span("strsvc.Count", context=ctx)

        try:
            span.set_attribute("request.str", request.str)
            span.set_attribute("request.str_length", len(request.str))

            # Extract baggage if present
            baggage = self.propagator.extract(ctx, carrier)
            author = self._get_baggage_value(baggage, "author")
            if author:
                span.set_attribute("baggage.author", author)

            # Call business logic with the extracted context
            result = self.bus.count(ctx, request.str)

            span.set_attribute("result.count", result)
            span.set_status(Status(StatusCode.OK))

            return strsvc_pb2.CountReply(v=result)

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
        finally:
            span.end()

    def Uppercase(self, request, context):
        """
        RPC endpoint for converting to uppercase.
        """
        metadata = dict(context.invocation_metadata())
        carrier = {k: v for k, v in metadata.items()}

        ctx = extract(carrier)
        ctx, span = self.tracer.start_span("strsvc.Uppercase", context=ctx)

        try:
            span.set_attribute("request.str", request.str)

            result = self.bus.uppercase(ctx, request.str)

            span.set_attribute("result.str", result)
            span.set_status(Status(StatusCode.OK))

            return strsvc_pb2.UppercaseReply(v=result)

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
        finally:
            span.end()

    def _get_baggage_value(self, baggage, key: str) -> str:
        """Extract a value from baggage."""
        try:
            return baggage.get(key, "")
        except Exception:
            return ""


def create_bus(tracer: trace.Tracer) -> StrBus:
    """Create a traced bus instance."""
    raw_bus = StrBus(tracer)
    meter = get_meter("strsvc")
    return wrap_with_all(raw_bus, tracer, meter)


def serve(port: int = 50052):
    """
    Start the gRPC server.

    Args:
        port: Port to listen on
    """
    # Initialize OpenTelemetry
    otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")

    print(f"Initializing OpenTelemetry (endpoint: {otlp_endpoint})...")
    tracer_shutdown = init_tracer_provider(
        service_name="strsvc",
        service_version="1.0.0",
        otlp_endpoint=otlp_endpoint,
    )
    meter_shutdown = init_meter_provider(
        service_name="strsvc",
        service_version="1.0.0",
        otlp_endpoint=otlp_endpoint,
    )
    init_propagator()

    tracer = get_tracer("strsvc-server")
    propagator = BaggagePropagator()

    # Create bus and server
    bus = create_bus(tracer)
    server = grpc.server(ThreadPoolExecutor(max_workers=10))
    strsvc_pb2_grpc.add_StrServicer_to_server(
        StrSvcServicer(bus, tracer, propagator),
        server
    )

    address = f"[::]:{port}"
    server.add_insecure_port(address)

    print(f"Starting strsvc server on {address}")
    server.start()

    try:
        print("strsvc server is running. Press Ctrl+C to stop.")
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\nShutting down strsvc server...")
        server.stop(grace=5)
        tracer_shutdown()
        meter_shutdown()


if __name__ == "__main__":
    port = int(os.getenv("STRVCP_PORT", "50052"))
    serve(port)
