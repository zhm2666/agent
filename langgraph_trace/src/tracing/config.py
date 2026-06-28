import os


class TracingConfig:
    LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
    LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "chatbot")

    USE_OTEL = os.getenv("USE_OTEL", "false").lower() == "true"
    OTLP_ENDPOINT = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")
    SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "langgraph-chatbot")

    @classmethod
    def is_enabled(cls) -> bool:
        return bool(cls.LANGSMITH_TRACING or cls.USE_OTEL)

