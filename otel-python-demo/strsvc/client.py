"""
Client for testing strsvc (string service).
Demonstrates how to call gRPC services with trace context propagation.
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

from strsvc import strsvc_pb2
from strsvc import strsvc_pb2_grpc
from otel_utils import init_tracer_provider, init_meter_provider, init_propagator, get_tracer


class StrSvcClient:
    """Client for calling strsvc gRPC methods with trace context propagation."""

    def __init__(self, channel: grpc.Channel, tracer: trace.Tracer):
        self.stub = strsvc_pb2_grpc.StrStub(channel)
        self.tracer = tracer

    def count(self, text: str) -> int:
        """
        Call the Count RPC method.

        Args:
            text: Text to count characters in

        Returns:
            Character count
        """
        ctx, span = self.tracer.start_span("client.strsvc.Count")
        span.set_attribute("request.text", text)
        span.set_attribute("request.length", len(text))

        try:
            # Inject trace context into gRPC metadata
            metadata = []
            carrier = {}

            # Inject W3C TraceContext
            inject(carrier)

            for key, value in carrier.items():
                metadata.append((key, value))

            # Inject baggage if present
            baggage_carrier = {}
            baggage_propagator = BaggagePropagator()
            baggage_propagator.inject(baggage_carrier, ctx)
            for key, value in baggage_carrier.items():
                metadata.append((key, value))

            # Make the gRPC call
            response = self.stub.Count(
                strsvc_pb2.CountRequest(str=text),
                metadata=metadata,
            )

            span.set_attribute("response.count", response.v)
            span.set_status(Status(StatusCode.OK))
            return response.v

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
        finally:
            span.end()

    def uppercase(self, text: str) -> str:
        """
        Call the Uppercase RPC method.

        Args:
            text: Text to convert to uppercase

        Returns:
            Uppercase text
        """
        ctx, span = self.tracer.start_span("client.strsvc.Uppercase")
        span.set_attribute("request.text", text)

        try:
            # Inject trace context
            metadata = []
            carrier = {}
            inject(carrier)
            for key, value in carrier.items():
                metadata.append((key, value))

            response = self.stub.Uppercase(
                strsvc_pb2.UppercaseRequest(str=text),
                metadata=metadata,
            )

            span.set_attribute("response.text", response.v)
            span.set_status(Status(StatusCode.OK))
            return response.v

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
        finally:
            span.end()


def run_demo():
    """Run the client demo."""
    # Initialize OpenTelemetry
    otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")

    print("Initializing OpenTelemetry client...")
    tracer_shutdown = init_tracer_provider(
        service_name="strsvc-client",
        service_version="1.0.0",
        otlp_endpoint=otlp_endpoint,
    )
    init_propagator()

    tracer = get_tracer("strsvc-client")

    # Connect to server
    server_address = os.getenv("STRVCP_ADDRESS", "localhost:50052")
    print(f"Connecting to strsvc at {server_address}...")

    with grpc.insecure_channel(server_address) as channel:
        client = StrSvcClient(channel, tracer)

        print("\n" + "=" * 50)
        print("strsvc Client Demo")
        print("=" * 50)

        # Test Count
        test_text = "Hello, World! OpenTelemetry is awesome!"
        print(f"\nTesting Count('{test_text}')...")
        count_result = client.count(test_text)
        print(f"Result: {count_result} characters")

        # Test Uppercase
        print(f"\nTesting Uppercase('{test_text}')...")
        upper_result = client.uppercase(test_text)
        print(f"Result: {upper_result}")

        print("\n" + "=" * 50)
        print("All tests passed!")
        print("=" * 50)

    tracer_shutdown()


if __name__ == "__main__":
    run_demo()
