"""
基础使用示例

展示 LangGraph 版 PredictionAgent 的基本调用方式。
"""

import sys
import os
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.agent import PredictionAgent, create_agent


def main():
    print("=" * 70)
    print("PredictionAgent-LangGraph 基础使用示例")
    print("=" * 70)

    agent = create_agent()

    test_queries = [
        "帮我分析一下 iPhone 15 Pro 的销量预测",
        "预测一下 MacBook Pro 的销量趋势",
        "分析华为手机的市场表现",
    ]

    for query in test_queries:
        print(f"\n{'=' * 70}")
        print(f"用户问题: {query}")
        print(f"{'=' * 70}\n")

        # 执行分析（使用模拟数据，无需数据库）
        result = agent.analyze(
            query=query,
            chart_type="combined",
            use_mock_data=True,
        )

        if result.get("success"):
            print("\n" + "=" * 50)
            print("分析结果")
            print("=" * 50)

            product = result.get("product", {})
            print(f"\n【产品信息】")
            print(f"  名称: {product.get('name', 'N/A')}")
            print(f"  代码: {product.get('code', 'N/A')}")
            print(f"  置信度: {product.get('confidence', 0):.2%}")

            stats = result.get("data", {}).get("statistics", {})
            print(f"\n【统计信息】")
            print(f"  日均销量: {stats.get('avg_daily_sales', 0):.2f}")
            print(f"  趋势方向: {stats.get('trend_direction', 'unknown')}")
            print(f"  趋势变化: {stats.get('trend_change_percent', 0):+.2f}%")

            chart = result.get("chart", {})
            if chart.get("url"):
                print(f"\n【可视化图表】")
                print(f"  图表URL: {chart.get('url')}")
                print(f"  图表类型: {chart.get('type', 'N/A')}")
                if chart.get("filepath"):
                    print(f"  文件路径: {chart.get('filepath')}")

            analysis = result.get("analysis", {})
            print(f"\n【分析报告】")
            analysis_text = analysis.get("result", "无分析结果")
            print(analysis_text[:500] + ("..." if len(analysis_text) > 500 else ""))

            insights = analysis.get("key_insights", [])
            if insights:
                print(f"\n【关键洞察】")
                for i, insight in enumerate(insights[:3], 1):
                    print(f"  {i}. {insight}")

            recommendations = analysis.get("recommendations", [])
            if recommendations:
                print(f"\n【业务建议】")
                for i, rec in enumerate(recommendations[:3], 1):
                    print(f"  {i}. {rec}")

        else:
            print(f"\n分析失败: {result.get('error', '未知错误')}")

    print("\n\n" + "=" * 70)
    print("示例执行完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
