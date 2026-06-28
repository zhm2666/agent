"""
Business logic bus for addsvc (addition service).
Handles Sum (addition) and Concat (string concatenation) operations.
"""
from opentelemetry import trace


class AddBus:
    """Business logic for arithmetic and concatenation operations."""

    def __init__(self, tracer: trace.Tracer):
        self.tracer = tracer

    def sum(self, a: int, b: int) -> int:
        """
        Add two numbers together.

        Args:
            a: First operand
            b: Second operand

        Returns:
            Sum of a and b
        """
        with self.tracer.start_as_current_span("addsvc.bus.sum") as span:
            span.set_attribute("operand.a", a)
            span.set_attribute("operand.b", b)

            result = a + b

            span.set_attribute("result.sum", result)
            return result

    def concat(self, a: str, b: str) -> str:
        """
        Concatenate two strings.

        Args:
            a: First string
            b: Second string

        Returns:
            Concatenated string
        """
        with self.tracer.start_as_current_span("addsvc.bus.concat") as span:
            span.set_attribute("operand.a", a)
            span.set_attribute("operand.b", b)
            span.set_attribute("operand.a_length", len(a))
            span.set_attribute("operand.b_length", len(b))

            result = a + b

            span.set_attribute("result.concat", result)
            span.set_attribute("result.length", len(result))
            return result
