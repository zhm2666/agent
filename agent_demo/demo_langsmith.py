"""
使用 LangSmith 追踪的 demo 脚本。
"""
import os
from dotenv import load_dotenv

load_dotenv()

# LangSmith 会自动读取 LANGSMITH_* 环境变量
print("=" * 60)
print("LangGraph Interrupt Demo with LangSmith Tracing")
print("=" * 60)
print(f"LangSmith Project: {os.getenv('LANGSMITH_PROJECT', 'default')}")
print(f"LangSmith API Key: {'*' * 20}{os.getenv('LANGSMITH_API_KEY', '')[-10:]}")
print("=" * 60)

from langgraph.types import Command
import uuid

# 使用 LangSmith 版本的 graph
from graph_langsmith import build_graph


def main():
    graph = build_graph()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    print(f"\nThread ID: {thread_id}")
    print(f"Visit https://smith.langchain.com to view traces\n")

    initial_state = {
        "text": "你好世界",
        "translation": "",
        "attempts": 0,
        "quality": "",
        "human_decision": "",
    }

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

        print("\n" + "-" * 60)
        user_input = input("👤 请输入你的决定 (retry/approve): ").strip()

        print(f"\n📤 恢复执行，人工决定: {user_input}\n")
        result = graph.invoke(
            Command(resume=user_input),
            config=config,
        )

        if "__interrupt__" not in result:
            print("✅ 图已正常结束，跳出循环")
            break

    # ---- 最终状态 ----
    print("\n" + "=" * 60)
    print("✅ 最终结果:")
    print(f"  译文: {result.get('translation')}")
    print(f"  尝试次数: {result.get('attempts')}")
    print(f"  质量: {result.get('quality')}")
    print(f"  人工决定: {result.get('human_decision')}")
    print("=" * 60)
    print("\n📊 查看 LangSmith 追踪: https://smith.langchain.com")


if __name__ == "__main__":
    main()
