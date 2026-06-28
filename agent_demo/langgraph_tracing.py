"""
LangGraph tracing utilities.
Provides decorators and utilities for tracing LangGraph nodes.
"""
from functools import wraps
from typing import Any, Callable, Dict, Optional
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode


class LangGraphTracer:
    """
    Tracer for LangGraph nodes.
    Automatically creates spans for each node execution.
    """

    def __init__(self, tracer: trace.Tracer, meter: metrics.Meter):
        self.tracer = tracer
        self.meter = meter

        # Metrics
        self.node_counter = meter.create_counter(
            name="langgraph_node_executions_total",
            description="Total number of node executions",
            unit="1",
        )

        self.node_duration = meter.create_histogram(
            name="langgraph_node_duration_seconds",
            description="Node execution duration in seconds",
            unit="s",
        )

    def trace_node(
        self,
        node_name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Callable:
        """
        Decorator to trace a LangGraph node function.

        Args:
            node_name: Name of the node for the span
            attributes: Additional attributes to record

        Returns:
            Decorated function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(state: dict, *args, **kwargs):
                # Extract key info from state for attributes
                span_attrs = {
                    "node.name": node_name,
                    "graph.type": "langgraph",
                    "state.attempts": state.get("attempts", 0),
                }

                if attributes:
                    span_attrs.update(attributes)

                # Add input text preview if available
                if "text" in state:
                    span_attrs["input.text_preview"] = str(state["text"])[:100]

                if "translation" in state and state["translation"]:
                    span_attrs["output.translation_preview"] = str(state["translation"])[:100]

                with self.tracer.start_as_current_span(
                    f"node.{node_name}",
                    attributes=span_attrs,
                ) as span:
                    try:
                        result = func(state, *args, **kwargs)
                        # Record success metrics
                        self.node_counter.add(1, {"node": node_name, "status": "success"})
                        span.set_status(Status(StatusCode.OK))
                        return result

                    except Exception as e:
                        # Record error
                        self.node_counter.add(1, {"node": node_name, "status": "error"})
                        span.set_status(Status(StatusCode.ERROR, str(e)))
                        span.record_exception(e)
                        span.add_event("Node execution failed", {"error": str(e)})
                        raise

            return wrapper
        return decorator

    def record_router(self, router_name: str, decision: str, state: dict) -> None:
        """
        Record a router decision.

        Args:
            router_name: Name of the router function
            decision: The routing decision
            state: Current state
        """
        with self.tracer.start_as_current_span(
            f"router.{router_name}",
            attributes={
                "router.name": router_name,
                "router.decision": decision,
                "state.quality": state.get("quality", ""),
                "state.attempts": state.get("attempts", 0),
            },
        ):
            pass

    def record_graph_invocation(
        self,
        operation: str,
        thread_id: str,
        status: str,
        duration: float,
    ) -> None:
        """
        Record metrics for a graph invocation.

        Args:
            operation: Operation type (chat, review)
            thread_id: Thread identifier
            status: Execution status
            duration: Duration in seconds
        """
        self.node_counter.add(1, {"operation": operation, "status": status})
        self.node_duration.record(duration, {"operation": operation})


def create_tracer() -> LangGraphTracer:
    """Create a LangGraph tracer instance."""
    from otel_setup import get_tracer, get_meter
    tracer = get_tracer("langgraph")
    meter = get_meter("langgraph")
    return LangGraphTracer(tracer, meter)
