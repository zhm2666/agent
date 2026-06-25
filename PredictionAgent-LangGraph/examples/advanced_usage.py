"""
高级使用示例

展示 LangGraph 版 PredictionAgent 的高级功能：
1. thread_id 多轮对话续跑
2. user_id 审计/多租户
3. session_id 应用层会话追踪
4. stream_analysis 流式执行
5. get_state 状态查看与恢复
"""

import sys
import os
import uuid
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agent import PredictionAgent, create_agent


def example_thread_id_continuation():
    """
    示例1: thread_id 多轮对话续跑

    同一个 thread_id 可以让 LangGraph 在上一次执行的状态上继续，
    适合"用户多轮追问"的场景。
    """
    print("\n" + "=" * 60)
    print("示例1: thread_id 多轮对话续跑")
    print("=" * 60)

    agent = create_agent()
    thread_id = "multi-turn-user-123"

    # 第一轮：用户问 iPhone
    print("\n--- 第一轮：用户问 iPhone ---")
    result1 = agent.analyze(
        query="帮我分析 iPhone 15 Pro 的销量预测",
        chart_type="combined",
        use_mock_data=True,
        thread_id=thread_id,
        user_id="user-001",
    )

    if result1.get("success"):
        print(f"第一轮完成，产品: {result1['product']['name']}")
        print(f"图表: {result1['chart']['url']}")

    # 第二轮：用户追问（同一个 thread_id）
    print("\n--- 第二轮：用户追问趋势分析 ---")
    result2 = agent.analyze(
        query="那相比上个月呢？趋势如何？",
        chart_type="line",
        use_mock_data=True,
        thread_id=thread_id,
        user_id="user-001",
    )

    if result2.get("success"):
        print(f"第二轮完成，产品: {result2['product']['name']}")

    # 查看当前状态
    print("\n--- 查看 thread_id 对应的状态 ---")
    saved_state = agent.get_state(thread_id)
    if saved_state:
        step = saved_state.get("prediction_state", {}).get("step", "unknown")
        print(f"当前 step: {step}")
        print(f"session_id: {saved_state.get('session_id')}")
        print(f"user_id: {saved_state.get('user_id')}")

    return thread_id


def example_user_id_audit():
    """
    示例2: user_id 用于审计/多租户

    user_id 不影响图的执行逻辑，但会被 LangGraph checkpointer 持久化，
    适合接入 LangGraph Platform / LangSmith 后做用户维度的用量统计。
    """
    print("\n" + "=" * 60)
    print("示例2: user_id 审计与多租户")
    print("=" * 60)

    agent = create_agent()

    # 不同用户可以有不同的 thread_id，但 user_id 用于区分是谁在用
    users = [
        {"user_id": "user-alice", "query": "分析 MacBook Pro"},
        {"user_id": "user-bob", "query": "分析 AirPods"},
        {"user_id": "user-alice", "query": "分析 iPad Air"},  # Alice 又来了
    ]

    for u in users:
        result = agent.analyze(
            query=u["query"],
            chart_type="combined",
            use_mock_data=True,
            thread_id=f"thread-{uuid.uuid4().hex[:8]}",
            user_id=u["user_id"],
        )
        print(f"  [{u['user_id']}] {u['query']} -> {'成功' if result.get('success') else '失败'}")

    print("\n在 LangSmith Dashboard 中按 user_id 筛选，可以看到 Alice 跑了2次，Bob 跑了1次。")


def example_session_id_tracking():
    """
    示例3: session_id 应用层会话追踪

    session_id 是直接写入 AgentState 的业务字段，
    适合你的前端有自己的 session/cookie 时做关联追踪。
    """
    print("\n" + "=" * 60)
    print("示例3: session_id 应用层会话追踪")
    print("=" * 60)

    agent = create_agent()
    session_id = f"session-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    print(f"\n创建会话: {session_id}")
    result = agent.analyze(
        query="预测小米手机的销量",
        chart_type="combined",
        use_mock_data=True,
        thread_id=f"thread-{uuid.uuid4().hex[:8]}",
        user_id="user-001",
        session_id=session_id,
    )

    if result.get("success"):
        # session_id 会透传到结果里，便于你在数据库里按会话查询
        print(f"会话 {session_id} 分析完成")
        print(f"session_id 透传到结果: {result.get('state', {}).get('session_id')}")

    # 模拟：你可以在数据库里按 session_id 查询这个会话的所有分析记录
    print(f"\n提示：在数据库里按 session_id='{session_id}' 查询，可以拿到这个会话的所有分析记录。")


def example_stream_analysis():
    """
    示例4: stream_analysis 流式执行

    流式执行让你在每个节点完成后立即拿到中间结果，
    适合做实时进度展示。
    """
    print("\n" + "=" * 60)
    print("示例4: stream_analysis 流式执行")
    print("=" * 60)

    agent = create_agent()

    print("\n开始流式分析...")
    step_count = 0

    for event in agent.stream_analysis(
        query="分析 iPhone 的销量预测",
        chart_type="combined",
        use_mock_data=True,
        thread_id="stream-demo",
    ):
        step_count += 1
        # event 的 key 是节点名，value 是该节点的输出状态
        node_name = list(event.keys())[0] if event else "unknown"
        print(f"  步骤 {step_count}: 节点 {node_name} 执行完成")

        # 可以在这里实时更新 UI 进度条
        if node_name == "product_identification":
            step_data = event[node_name].get("prediction_state", {}).get("product_identification", {})
            if step_data.get("identified"):
                print(f"    -> 产品已识别: {step_data.get('product_name')} (置信度 {step_data.get('confidence', 0):.0%})")

        if node_name == "data_fetch":
            fetch_data = event[node_name].get("prediction_state", {}).get("data_fetch", {})
            if fetch_data.get("fetched"):
                print(f"    -> 数据获取成功: {len(fetch_data.get('historical_data', []))} 条历史数据")

        if node_name == "analysis":
            analysis_data = event[node_name].get("prediction_state", {}).get("analysis", {})
            if analysis_data.get("analyzed"):
                print(f"    -> 分析完成，结果长度: {len(analysis_data.get('analysis_result', ''))} 字符")

    print(f"\n共执行 {step_count} 个节点")


def example_state_recovery():
    """
    示例5: get_state 状态查看与恢复

    通过 thread_id 可以随时查看或恢复之前执行的状态。
    """
    print("\n" + "=" * 60)
    print("示例5: get_state 状态查看与恢复")
    print("=" * 60)

    agent = create_agent()
    thread_id = f"recovery-demo-{uuid.uuid4().hex[:8]}"

    # 先跑一次
    print("\n--- 步骤1: 执行一次分析 ---")
    result = agent.analyze(
        query="分析索尼PS5的销量",
        chart_type="combined",
        use_mock_data=True,
        thread_id=thread_id,
    )

    if result.get("success"):
        print(f"分析成功: {result['product']['name']}")

    # 查看保存的状态
    print("\n--- 步骤2: 查看保存的状态 ---")
    saved_state = agent.get_state(thread_id)
    if saved_state:
        pred_state = saved_state.get("prediction_state", {})
        print(f"当前步骤: {pred_state.get('step')}")
        print(f"产品识别: {pred_state.get('product_identification', {}).get('product_name')}")
        print(f"数据获取: {'已获取' if pred_state.get('data_fetch', {}).get('fetched') else '未获取'}")
        print(f"图表生成: {'已生成' if pred_state.get('chart_generation', {}).get('generated') else '未生成'}")
        print(f"分析完成: {'是' if pred_state.get('analysis', {}).get('analyzed') else '否'}")

        # 你可以把 saved_state 传给前端做展示
        print(f"\n完整状态可序列化后传给前端做实时进度展示。")


def example_custom_checkpointer():
    """
    示例6: 自定义 Checkpointer（可选）

    默认使用 MemorySaver（内存），重启后丢失。
    生产环境建议换成 PostgresSaver 或 RedisSaver。
    """
    print("\n" + "=" * 60)
    print("示例6: 自定义 Checkpointer")
    print("=" * 60)

    # MemorySaver（默认，内存存储，重启丢失）
    from langgraph.checkpoint.memory import MemorySaver

    memory_checkpointer = MemorySaver()

    # PostgresSaver（生产推荐，持久化存储，重启可恢复）
    # from langgraph.checkpoint.postgres import PostgresSaver
    #
    # pg_checkpointer = PostgresSaver.from_conn_string("postgresql://user:pass@localhost/db")
    # pg_checkpointer.setup()  # 首次需要初始化表结构

    from src.graph.builder import create_prediction_graph

    # 使用自定义 checkpointer 创建图
    app = create_prediction_graph(
        repository=None,
        mcp_client=None,
        checkpointer=memory_checkpointer,
    )
    print(f"已使用 MemorySaver checkpointer")
    print("提示：生产环境建议使用 PostgresSaver，换掉 MemorySaver 即可。")


def main():
    print("=" * 70)
    print("PredictionAgent-LangGraph 高级使用示例")
    print("=" * 70)

    example_thread_id_continuation()
    example_user_id_audit()
    example_session_id_tracking()
    example_stream_analysis()
    example_state_recovery()
    example_custom_checkpointer()

    print("\n\n" + "=" * 70)
    print("所有示例执行完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
