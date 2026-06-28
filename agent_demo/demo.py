"""LangGraph Interrupt Demo - 带 OpenTelemetry 分布式追踪版"""

import os
from dotenv import load_dotenv

load_dotenv()

# 设置 OpenTelemetry
os.environ.setdefault("LANGSMITH_TRACING", "true")

from opentelemetry import trace
from langgraph.types import Command

# 初始化 OpenTelemetry
from otel_setup import init_opentelemetry

otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")
shutdown = init_opentelemetry(
    service_name="agent-demo-demo",
    service_version="1.0.0",
    otlp_endpoint=otlp_endpoint,
)

# 导入带追踪的 graph
from graph import build_graph
import uuid


def main():
    graph = build_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    tracer = trace.get_tracer("agent-demo")

    print("=" * 55)
    print("LangGraph Interrupt Demo: 翻译质检 + 人工审核")
    print("📊 OpenTelemetry 分布式追踪已启用")
    print("=" * 55)

    initial_state = {
        "text": "你好世界",
        "translation": "",
        "attempts": 0,
        "quality": "",
        "human_decision": "",
    }

    with tracer.start_as_current_span("demo.chat", attributes={"thread.id": thread_id}):
        # ---- 第一次启动 ----
        print("\n📤 启动翻译...\n")
        result = graph.invoke(initial_state, config=config)

        # ---- while 循环处理 interrupt ----
        while "__interrupt__" in result:
            interrupt_info = result["__interrupt__"][0].value
            print(f"\n⏸️  图已暂停，等待人工审核:")
            print(f"   翻译结果: {interrupt_info['translation']}")
            print(f"   尝试次数: {interrupt_info['attempts']}")
            print(f"   提示: {interrupt_info['instruction']}")

            print("\n" + "-" * 55)
            user_input = input("👤 请输入你的决定 (retry/approve): ").strip()

            print(f"\n📤 恢复执行，人工决定: {user_input}\n")

            with tracer.start_as_current_span("demo.review", attributes={"decision": user_input}):
                result = graph.invoke(
                    Command(resume=user_input),
                    config=config,
                )

            if "__interrupt__" not in result:
                print("✅ 图已正常结束，跳出循环")
                break

    # ---- 最终状态 ----
    print("\n" + "=" * 55)
    print("✅ 最终结果:")
    print(f"  译文: {result.get('translation')}")
    print(f"  尝试次数: {result.get('attempts')}")
    print(f"  质量: {result.get('quality')}")
    print(f"  人工决定: {result.get('human_decision')}")

    # 获取 trace ID
    span = trace.get_current_span()
    if span:
        ctx = span.get_span_context()
        if ctx.is_valid:
            print(f"\n📊 Trace ID: {format(ctx.trace_id, '032x')}")

    shutdown()


if __name__ == "__main__":
    main()
