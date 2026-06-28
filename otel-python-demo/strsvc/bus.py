"""
Business logic bus for strsvc (string service).
Handles string operations: Count (count occurrences) and Uppercase.
"""
from opentelemetry import trace


class StrBus:
    """Business logic for string operations."""

    def __init__(self, tracer: trace.Tracer):
        self.tracer = tracer

    def count(self, text: str) -> int:
        """
        Count the total number of characters in the text.

        Args:
            text: Input text

        Returns:
            Character count
        """
        with self.tracer.start_as_current_span("strsvc.bus.count") as span:
            span.set_attribute("input.text_length", len(text))
            span.set_attribute("input.text_preview", text[:50] if len(text) > 50 else text)

            result = len(text)

            span.set_attribute("result.count", result)
            return result

    def uppercase(self, text: str) -> str:
        """
        Convert text to uppercase.

        Args:
            text: Input text

        Returns:
            Uppercase text
        """
        with self.tracer.start_as_current_span("strsvc.bus.uppercase") as span:
            span.set_attribute("input.text", text)
            span.set_attribute("input.length", len(text))

            result = text.upper()

            span.set_attribute("result.text", result)
            span.set_attribute("result.length", len(result))
            return result
