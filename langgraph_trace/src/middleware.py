from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from opentelemetry import trace
import time, uuid


class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(f"HTTP {request.method} {request.url.path}") as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            start = time.time()
            response = await call_next(request)
            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("http.duration_ms", (time.time() - start) * 1000)
            return response

