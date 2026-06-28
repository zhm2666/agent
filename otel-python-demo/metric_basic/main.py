"""
Metric Basic - Metrics demonstration showing Counter, ObservableGauge, and Histogram.
"""
import os
import sys
import time
import random
import threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opentelemetry import metrics
from otel_utils import init_tracer_provider, init_meter_provider, get_meter


class MetricsDemo:
    """Demonstrates all three metric types."""

    def __init__(self, meter: metrics.Meter):
        self.meter = meter
        self._request_count = 0
        self._active_requests = 0
        self._error_count = 0

        self._setup_metrics()

    def _setup_metrics(self):
        """Initialize all metric instruments."""

        # Counter: for values that only increase (request count, error count)
        self.request_counter = self.meter.create_counter(
            name="http_requests_total",
            description="Total number of HTTP requests",
            unit="1",
        )

        self.error_counter = self.meter.create_counter(
            name="http_requests_errors_total",
            description="Total number of HTTP request errors",
            unit="1",
        )

        # ObservableGauge: for values that can go up or down (CPU, memory, queue depth)
        self.cpu_gauge = self.meter.create_observable_gauge(
            name="system_cpu_usage",
            description="Current CPU usage percentage",
            unit="1",
            callbacks=[self._get_cpu_callback],
        )

        self.memory_gauge = self.meter.create_observable_gauge(
            name="system_memory_usage",
            description="Current memory usage in bytes",
            unit="By",
            callbacks=[self._get_memory_callback],
        )

        self.queue_gauge = self.meter.create_observable_gauge(
            name="queue_depth",
            description="Current number of items in queue",
            unit="1",
            callbacks=[self._get_queue_callback],
        )

        # Histogram: for recording distributions (request duration, response size)
        self.request_histogram = self.meter.create_histogram(
            name="http_request_duration_seconds",
            description="HTTP request duration in seconds",
            unit="s",
        )

        self.response_size_histogram = self.meter.create_histogram(
            name="http_response_size_bytes",
            description="HTTP response size in bytes",
            unit="By",
        )

    def _get_cpu_callback(self, options):
        """Callback for CPU gauge - returns current CPU usage."""
        cpu_usage = random.uniform(10.0, 80.0)
        yield metrics.Observation(cpu_usage, {"cpu.core": "total"})

    def _get_memory_callback(self, options):
        """Callback for memory gauge - returns current memory usage."""
        memory_usage = random.randint(100_000_000, 500_000_000)
        yield metrics.Observation(memory_usage, {"memory.type": "used"})

    def _get_queue_callback(self, options):
        """Callback for queue gauge - returns current queue depth."""
        queue_depth = random.randint(0, 100)
        yield metrics.Observation(queue_depth, {"queue.name": "default"})

    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """
        Record metrics for an HTTP request.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: Request endpoint path
            status_code: HTTP status code
            duration: Request duration in seconds
        """
        attributes = {
            "method": method,
            "endpoint": endpoint,
            "status_code": str(status_code),
        }

        self._request_count += 1
        self.request_counter.add(1, attributes)

        self.request_histogram.record(duration, attributes)

        if status_code >= 400:
            self._error_count += 1
            error_attributes = {**attributes, "error.type": "http_error"}
            self.error_counter.add(1, error_attributes)

    def record_response(self, endpoint: str, size_bytes: int):
        """
        Record response size metrics.

        Args:
            endpoint: Request endpoint path
            size_bytes: Response size in bytes
        """
        self.response_size_histogram.record(
            size_bytes,
            {"endpoint": endpoint}
        )

    def simulate_requests(self, num_requests: int = 10):
        """
        Simulate a series of HTTP requests for demonstration.

        Args:
            num_requests: Number of requests to simulate
        """
        endpoints = ["/api/users", "/api/products", "/api/orders", "/api/health"]
        methods = ["GET", "POST", "PUT", "DELETE"]
        status_codes = [200, 200, 200, 201, 204, 400, 404, 500]

        for i in range(num_requests):
            method = random.choice(methods)
            endpoint = random.choice(endpoints)
            status_code = random.choice(status_codes)
            duration = random.uniform(0.01, 2.0)
            response_size = random.randint(100, 10000)

            self.record_request(method, endpoint, status_code, duration)
            self.record_response(endpoint, response_size)

            print(f"Request {i+1}: {method} {endpoint} -> {status_code} ({duration:.3f}s)")

            time.sleep(random.uniform(0.1, 0.5))


def main():
    print("=" * 60)
    print("OpenTelemetry Metrics Demo - Counter, Gauge, Histogram")
    print("=" * 60)

    # Initialize both tracer and meter providers
    otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")

    print("\nInitializing TracerProvider...")
    tracer_shutdown = init_tracer_provider(
        service_name="metric-basic",
        service_version="1.0.0",
        otlp_endpoint=otlp_endpoint,
    )

    print("Initializing MeterProvider...")
    meter_shutdown = init_meter_provider(
        service_name="metric-basic",
        service_version="1.0.0",
        otlp_endpoint=otlp_endpoint,
    )

    # Get meter for this module
    meter = get_meter("metric-basic")

    # Create metrics demo
    demo = MetricsDemo(meter)

    print("\nSimulating HTTP requests...")
    print("-" * 40)

    demo.simulate_requests(10)

    print("-" * 40)
    print("\nMetric summary:")
    print(f"  Total requests recorded: {demo._request_count}")
    print(f"  Total errors recorded: {demo._error_count}")
    print(f"  Metric instruments created:")
    print(f"    - Counters: request_counter, error_counter")
    print(f"    - ObservableGauges: cpu_gauge, memory_gauge, queue_gauge")
    print(f"    - Histograms: request_histogram, response_size_histogram")

    print("\nMetrics are exported every 5 seconds to the OTLP endpoint.")
    print("Shut down gracefully to ensure final metrics are exported.")

    # Simulate some time for metrics to be collected
    print("\nWaiting for metrics collection...")
    time.sleep(2)

    # Shutdown
    print("\nShutting down providers...")
    meter_shutdown()
    tracer_shutdown()

    print("\nMetric basic demo completed!")


if __name__ == "__main__":
    main()
