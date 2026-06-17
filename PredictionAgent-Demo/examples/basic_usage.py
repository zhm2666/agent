"""
基础使用示例
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.agent import PredictionAgent, create_agent
from src.utils import load_config


def main():
    """主函数"""
    print("=" * 70)
    print("Prediction Agent 基础使用示例")
    print("=" * 70)

    # 创建Agent
    agent = create_agent()

    # 测试查询
    test_queries = [
        "帮我分析一下iPhone 15 Pro的销量预测",
        "预测一下MacBook Pro的销量趋势",
        "分析华为手机的市场表现"
    ]

    for query in test_queries:
        print(f"\n\n{'='*70}")
        print(f"用户问题: {query}")
        print(f"{'='*70}\n")

        # 执行分析（使用模拟数据）
        result = agent.analyze(
            query=query,
            chart_type="combined",
            use_mock_data=True  # 使用模拟数据，避免需要真实数据库
        )

        # 打印结果
        if result.get("success"):
            print("\n" + "=" * 50)
            print("分析结果")
            print("=" * 50)

            # 产品信息
            product = result.get("product", {})
            print(f"\n【产品信息】")
            print(f"  名称: {product.get('name', 'N/A')}")
            print(f"  代码: {product.get('code', 'N/A')}")
            print(f"  置信度: {product.get('confidence', 0):.2%}")

            # 统计信息
            stats = result.get("data", {}).get("statistics", {})
            print(f"\n【统计信息】")
            print(f"  日均销量: {stats.get('avg_daily_sales', 0):.2f}")
            print(f"  趋势方向: {stats.get('trend_direction', 'unknown')}")
            print(f"  趋势变化: {stats.get('trend_change_percent', 0):.2f}%")

            # 图表信息
            chart = result.get("chart", {})
            if chart.get("url"):
                print(f"\n【可视化图表】")
                print(f"  图表URL: {chart.get('url')}")
                print(f"  图表类型: {chart.get('type', 'N/A')}")

            # 分析结果
            analysis = result.get("analysis", {})
            print(f"\n【分析报告】")
            print(analysis.get("result", "无分析结果"))

        else:
            print(f"\n分析失败: {result.get('error', '未知错误')}")

    print("\n\n" + "=" * 70)
    print("示例执行完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
