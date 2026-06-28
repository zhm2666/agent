"""
运行最小可执行示例：带分布式链路采集的 LangGraph 聊天机器人。

链路目标（二选一或同时启用）：
1. LangSmith：设置 LANGSMITH_API_KEY 与 LANGSMITH_TRACING=true
2. Jaeger/OTLP：设置 OTLP_ENDPOINT=http://localhost:4318，并启动 Jaeger

本地启动 Jaeger 示例：
docker run -d --name jaeger \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 16686:16686 -p 4317:4317 -p 4318:4318 \
  jaegertracing/all-in-one:1.60
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from examples.chatbot.chatbot_graph import run_chatbot, stream_chatbot


def print_json(label: str, data: dict[str, object]) -> None:
    print(f"\n=== {label} ===")
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> None:
    queries = [
        "你好，请自我介绍一下",
        "现在几点了？",
        "今天天气怎么样？",
        "帮我推荐一个产品",
    ]

    for idx, query in enumerate(queries, start=1):
        print(f"\n>>>> 第 {idx} 轮: {query}")
        response = run_chatbot(user_query=query, thread_id="chatbot-demo-thread")
        print_json("运行结果", response)

    print("\n>>>> 流式演示")
    for event in stream_chatbot(user_query="查一下今天的天气", thread_id="chatbot-stream"):
        for node_name, node_output in event.items():
            print(f"  - 节点执行完成: {node_name}")


if __name__ == "__main__":
    main()
