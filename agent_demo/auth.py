"""模拟用户认证 + OpenTelemetry 追踪"""

from fastapi import Header, HTTPException
from opentelemetry import trace

_tracer = trace.get_tracer("auth")


def get_current_user(authorization: str = Header(None)) -> str:
    with _tracer.start_as_current_span(
        "auth.validate_token",
        attributes={
            "auth.has_token": authorization is not None,
        },
    ) as span:
        if not authorization:
            span.set_attribute("auth.result", "missing_header")
            raise HTTPException(status_code=401, detail="Missing Authorization header")

        token = authorization.replace("Bearer ", "").strip()

        if not token.startswith("user_"):
            span.set_attribute("auth.result", "invalid_token")
            raise HTTPException(status_code=401, detail="Invalid token")

        span.set_attribute("auth.result", "valid")
        span.set_attribute("user.id", token)
        return token
