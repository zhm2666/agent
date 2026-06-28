"""
Business logic for trace-basic demonstration.
Contains functions that would be traced.
"""
from opentelemetry import trace
from typing import Dict, Any


class Bus:
    """Business logic class that handles operations."""

    def __init__(self, tracer: trace.Tracer):
        self.tracer = tracer

    def calculate(self, operation: str, a: int, b: int) -> int:
        """
        Perform a calculation operation.

        Args:
            operation: Type of operation (add, subtract, multiply, divide)
            a: First operand
            b: Second operand

        Returns:
            Result of the calculation
        """
        with self.tracer.start_as_current_span(f"bus.calculate.{operation}") as span:
            span.set_attribute("operation", operation)
            span.set_attribute("operand.a", a)
            span.set_attribute("operand.b", b)

            if operation == "add":
                result = a + b
            elif operation == "subtract":
                result = a - b
            elif operation == "multiply":
                result = a * b
            elif operation == "divide":
                result = a // b if b != 0 else 0
                span.set_attribute("division.by_zero", b == 0)
            else:
                result = 0

            span.set_attribute("result", result)
            return result

    def process_string(self, text: str, transformation: str) -> str:
        """
        Process a string with the given transformation.

        Args:
            text: Input text
            transformation: Type of transformation (upper, lower, reverse)

        Returns:
            Transformed text
        """
        with self.tracer.start_as_current_span("bus.process_string") as span:
            span.set_attribute("input.text", text)
            span.set_attribute("transformation", transformation)
            span.set_attribute("input.length", len(text))

            if transformation == "upper":
                result = text.upper()
            elif transformation == "lower":
                result = text.lower()
            elif transformation == "reverse":
                result = text[::-1]
            else:
                result = text

            span.set_attribute("output.length", len(result))
            return result

    def aggregate_data(self, data: list) -> Dict[str, Any]:
        """
        Aggregate data from a list.

        Args:
            data: List of numbers

        Returns:
            Dictionary with aggregation results
        """
        with self.tracer.start_as_current_span("bus.aggregate_data") as span:
            span.set_attribute("data.count", len(data))
            if not data:
                return {"count": 0, "sum": 0, "min": 0, "max": 0}

            result = {
                "count": len(data),
                "sum": sum(data),
                "min": min(data),
                "max": max(data),
                "avg": sum(data) / len(data),
            }

            for key, value in result.items():
                span.set_attribute(f"result.{key}", value)

            return result
