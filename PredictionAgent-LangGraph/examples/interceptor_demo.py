"""
方案三演示：链路拦截器与业务代码完全解耦。

本文件只做“外部接入”，不修改任何原有：
- src/agent.py
- src/graph/builder.py
- src/nodes/*

链路采集通过 GraphTracingInterceptor 在外层包装实现。
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from src.agent import create_agent
from src.tracing.graph_callbacks import GraphTracingInterceptor


def main() -> None:
    # 1. 正常创建业务 Agent，链路逻辑完全没侵入这里
    agent = create_agent()

    # 2. 创建拦截器，只在这里启用链路
    interceptor = GraphTracingInterceptor()

    # 3. 只包装 graph 执行入口，不改动节点代码
    wrapped_invoke = interceptor.wrap_graph_method(agent.app.invoke)

    # 4. 正常构造业务初始状态
    initial_state = {
        "user_query": "帮我分析 iPhone 15 Pro 的销量预测",
        "chart_type": "combined",
        "prediction_state": agent._initial_identification(None),
        "reflection": agent._initial_reflection(),
        "is_completed": False,
        "error_message": "",
        "session_id": "interceptor-demo-session",
        "user_id": "user-demo",
        "created_at": agent._now_iso(),
        "updated_at": agent._now_iso(),
    }
    config = {
        "configurable": {
            "thread_id": "interceptor-demo-thread",
            "user_id": "user-demo",
        }
    }
    
    print("=" * 70)
    print("方案三演示：链路拦截器零侵入")
    print("=" * 70)
    # 5. 业务调用方式几乎不变
    print(f"\n用户问题: {initial_state['user_query']}\n")
    final_state = wrapped_invoke(state=initial_state, config=config)
    response = agent._build_response(final_state)
    print(f"分析结果: {'成功' if response.get('success') else '失败'}")

    # 6. 优雅关闭，确保链路数据刷出
    interceptor.shutdown()
    print("\n链路拦截器已关闭。")


if __name__ == "__main__":
    main()
