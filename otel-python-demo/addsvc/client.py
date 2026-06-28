"""
Client for testing addsvc (addition service).
Demonstrates distributed tracing across multiple services.
"""
import os
import sys
import grpc

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opentelemetry import trace
from opentelemetry.propagate import inject
from opentelemetry.trace import Status, StatusCode

from addsvc import addsvc_pb2
from addsvc import addsvc_pb2_grpc
from otel_utils import init_tracer_provider, init_propagator, get_tracer


class AddSvcClient:
    """Client for calling addsvc gRPC methods with distributed tracing."""

    def __init__(self, channel: grpc.Channel, tracer: trace.Tracer):
        self.stub = addsvc_pb2_grpc.AddStub(channel)
        self.tracer = tracer

    def sum(self, a: int, b: int) -> int:
        """
        Call the Sum RPC method.

        Args:
            a: First number
            b: Second number

        Returns:
            Sum of a and b
        """
        ctx, span = self.tracer.start_span("client.addsvc.Sum")
        span.set_attribute("request.a", a)
        span.set_attribute("request.b", b)

        try:
            # Inject trace context
            metadata = []
            carrier = {}
            inject(carrier)
            for key, value in carrier.items():
                metadata.append((key, value))

            response = self.stub.Sum(
                addsvc_pb2.SumRequest(a=a, b=b),
                metadata=metadata,
            )

            span.set_attribute("response.result", response.v)
            span.set_status(Status(StatusCode.OK))
            return response.v

        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
        finally:
            span.end()

    def concat(self, a: str, b: str) -> str:
        """
        Call the Concat RPC method.

        Args:
            a: First string
            b: Second string

        Returns:
            Concatenated string
        """
        ctx, span = self.tracer.start_span("client.addsvc.Concat")
        span.set_attribute("request.a", a)
        span.set_attribute("request.b", b)

        try:
            # Inject trace context
            metadata = []
            carrier = {}
            inject(carrier)
            for key, value in carrier.items():
                metadata.append((key, value))

            response = self.stub.Concat(
                addsvc_pb2.ConcatRequest(a=a, b=b),
                metadata=metadata,
            )

            span.set_attribute("response.result", response.v)
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
        service_name="addsvc-client",
        service_version="1.0.0",
        otlp_endpoint=otlp_endpoint,
    )
    init_propagator()

    tracer = get_tracer("addsvc-client")

    # Connect to server
    server_address = os.getenv("ADDSVC_ADDRESS", "localhost:50051")
    print(f"Connecting to addsvc at {server_address}...")

    with grpc.insecure_channel(server_address) as channel:
        client = AddSvcClient(channel, tracer)

        print("\n" + "=" * 50)
        print("addsvc Client Demo - Distributed Tracing")
        print("=" * 50)

        # Test Sum
        print("\nTesting Sum(10, 20)...")
        sum_result = client.sum(10, 20)
        print(f"Result: {sum_result}")

        # Test Concat
        print("\nTesting Concat('Hello, ', 'World!')...")
        concat_result = client.concat("Hello, ", "World!")
        print(f"Result: {concat_result}")

        # Test with larger numbers
        print("\nTesting Sum(12345, 67890)...")
        sum_result2 = client.sum(12345, 67890)
        print(f"Result: {sum_result2}")

        print("\n" + "=" * 50)
        print("All tests passed!")
        print("Check your OTLP collector/Jaeger for distributed traces.")
        print("=" * 50)

    tracer_shutdown()


if __name__ == "__main__":
    run_demo()
