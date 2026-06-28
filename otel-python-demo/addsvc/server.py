"""
gRPC server for addsvc (addition service).
Orchestrates calls to downstream strsvc service with distributed tracing.
"""
import os
import sys
import grpc
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opentelemetry import trace
from opentelemetry.propagate import inject
from opentelemetry.trace import Status, StatusCode
from opentelemetry.propagators.baggage import BaggagePropagator

from addsvc import addsvc_pb2
from addsvc import addsvc_pb2_grpc
from strsvc import strsvc_pb2 as strvc_proto
from strsvc import strsvc_pb2_grpc as strvc_grpc
from addsvc.bus import AddBus
from addsvc.middleware import wrap_with_all
from otel_utils import init_tracer_provider, init_meter_provider, init_propagator, get_tracer, get_meter


class AddSvcServicer(addsvc_pb2_grpc.AddServicer):
    """
    gRPC service implementation for addition operations.
    Orchestrates calls to downstream strsvc.
    """

    def __init__(
        self,
        bus: AddBus,
        tracer: trace.Tracer,
        str_client: strvc_grpc.StrStub,
        baggage_propagator: BaggagePropagator,
    ):
        self.bus = bus
        self.tracer = tracer
        self.str_client = str_client
        self.baggage_propagator = baggage_propagator

    def Sum(self, request, context):
        """
        RPC endpoint for summing two numbers.
        Creates a parent span for the orchestration.
        """
        ctx, span = self.tracer.start_span("addsvc.Sum")
        span.set_attribute("request.a", request.a)
        span.set_attribute("request.b", request.b)

        try:
            # Call local business logic
            result = self.bus.sum(ctx, request.a, request.b)

            # Optionally call downstream strsvc to count the result
            str_addr = os.getenv("STRVCP_ADDRESS", "localhost:50052")
            try:
                with grpc.insecure_channel(str_addr) as channel:
                    str_stub = strvc_grpc.StrStub(channel)

                    # Inject trace context for downstream call
                    metadata = []
                    carrier = {}
                    inject(carrier)
                    for key, value in carrier.items():
                        metadata.append((key, value))

                    str_response = str_stub.Count(
                        strvc_proto.CountRequest(str=str(result)),
                        metadata=metadata,
                    )
                    span.set_attribute("downstream.result_length", str_response.v)
            except Exception as e:
                span.add_event("Downstream strsvc call failed", {"error": str(e)})

            span.set_attribute("result.sum", result)
            span.set_status(Status(StatusCode.OK))

            return addsvc_pb2.SumReply(v=result)

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
        finally:
            span.end()

    def Concat(self, request, context):
        """
        RPC endpoint for concatenating strings.
        Adds custom baggage and calls downstream strsvc.
        """
        ctx, span = self.tracer.start_span("addsvc.Concat")
        span.set_attribute("request.a", request.a)
        span.set_attribute("request.b", request.b)

        try:
            # Add custom baggage for propagation to downstream
            ctx = self.baggage_propagator.inject(
                {},
                ctx,
                {"author": "addsvc-orchestrator"}
            )

            # Call local business logic
            result = self.bus.concat(ctx, request.a, request.b)

            # Call downstream strsvc with baggage
            str_addr = os.getenv("STRVCP_ADDRESS", "localhost:50052")
            try:
                with grpc.insecure_channel(str_addr) as channel:
                    str_stub = strvc_grpc.StrStub(channel)

                    # Inject trace context and baggage
                    metadata = []
                    carrier = {}
                    inject(carrier)
                    for key, value in carrier.items():
                        metadata.append((key, value))

                    # Also inject baggage
                    baggage_carrier = {}
                    self.baggage_propagator.inject(baggage_carrier, ctx)
                    for key, value in baggage_carrier.items():
                        metadata.append((key, value))

                    # Call Uppercase on downstream
                    str_response = str_stub.Uppercase(
                        strvc_proto.UppercaseRequest(str=result),
                        metadata=metadata,
                    )
                    span.set_attribute("downstream.uppercase_result", str_response.v)

            except Exception as e:
                span.add_event("Downstream strsvc call failed", {"error": str(e)})

            span.set_attribute("result.concat", result)
            span.set_status(Status(StatusCode.OK))

            return addsvc_pb2.ConcatReply(v=result)

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
        finally:
            span.end()


def create_bus(tracer: trace.Tracer) -> AddBus:
    """Create a traced bus instance."""
    raw_bus = AddBus(tracer)
    meter = get_meter("addsvc")
    return wrap_with_all(raw_bus, tracer, meter)


def serve(port: int = 50051):
    """
    Start the addsvc gRPC server.

    Args:
        port: Port to listen on
    """
    # Initialize OpenTelemetry
    otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")

    print(f"Initializing OpenTelemetry (endpoint: {otlp_endpoint})...")
    tracer_shutdown = init_tracer_provider(
        service_name="addsvc",
        service_version="1.0.0",
        otlp_endpoint=otlp_endpoint,
    )
    meter_shutdown = init_meter_provider(
        service_name="addsvc",
        service_version="1.0.0",
        otlp_endpoint=otlp_endpoint,
    )
    init_propagator()

    tracer = get_tracer("addsvc-server")
    baggage_propagator = BaggagePropagator()

    # Create bus
    bus = create_bus(tracer)

    # Create gRPC server
    server = grpc.server(ThreadPoolExecutor(max_workers=10))

    # Create servicer with str_client placeholder (will be set per-request)
    # For simplicity, we create str_client dynamically in each request handler
    servicer = AddSvcServicer(bus, tracer, None, baggage_propagator)

    addsvc_pb2_grpc.add_AddServicer_to_server(servicer, server)

    address = f"[::]:{port}"
    server.add_insecure_port(address)

    print(f"Starting addsvc server on {address}")
    print(f"Downstream strsvc at: {os.getenv('STRVCP_ADDRESS', 'localhost:50052')}")
    server.start()

    try:
        print("addsvc server is running. Press Ctrl+C to stop.")
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\nShutting down addsvc server...")
        server.stop(grace=5)
        tracer_shutdown()
        meter_shutdown()


if __name__ == "__main__":
    port = int(os.getenv("ADDSVC_PORT", "50051"))
    serve(port)
