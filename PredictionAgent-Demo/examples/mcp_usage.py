"""
MCP使用示例
展示如何通过MCP调用绘图服务
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.mcp import MCPChartClient, quick_plot
from src.mcp.chart_mcp_server import ChartMCPService


def example_direct_call():
    """直接调用绘图服务"""
    print("\n" + "=" * 60)
    print("示例1: 直接调用绘图服务")
    print("=" * 60)

    service = ChartMCPService(output_dir="output/charts")

    result = service.plot_sales_forecast(
        product_name="iPhone 15 Pro",
        dates=["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
        actual_values=[100, 120, 110, 130, 125],
        predicted_values=[95, 118, 115, 128, 122],
        future_dates=["2024-01-06", "2024-01-07", "2024-01-08"],
        future_predictions=[135, 140, 138],
        chart_type="combined"
    )

    print(f"生成结果: {result}")
    print(f"图表保存位置: {result['filepath']}")
    print(f"访问URL: {result['url']}")


def example_mcp_client_local():
    """通过MCP客户端本地调用"""
    print("\n" + "=" * 60)
    print("示例2: MCP客户端本地调用")
    print("=" * 60)

    # 创建MCP客户端（本地模式）
    client = MCPChartClient(mode="local")

    result = client.plot_sales_forecast(
        product_name="MacBook Pro",
        dates=["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
        actual_values=[50, 55, 48, 60, 58],
        predicted_values=[48, 52, 50, 58, 56],
        future_dates=["2024-01-06", "2024-01-07"],
        future_predictions=[62, 65],
        chart_type="line"
    )

    print(f"MCP调用结果:")
    print(f"  成功: {result.success}")
    print(f"  图表URL: {result.url}")
    print(f"  图表类型: {result.chart_type}")
    if result.error:
        print(f"  错误: {result.error}")


def example_mcp_client_remote():
    """通过MCP客户端远程调用"""
    print("\n" + "=" * 60)
    print("示例3: MCP客户端远程调用")
    print("=" * 60)

    # 创建MCP客户端（远程模式）
    client = MCPChartClient(
        mode="remote",
        server_url="http://localhost:8000"
    )

    result = client.plot_sales_forecast(
        product_name="AirPods Pro",
        dates=["2024-01-01", "2024-01-02", "2024-01-03"],
        actual_values=[80, 85, 78],
        predicted_values=[78, 82, 80],
        future_dates=["2024-01-04", "2024-01-05"],
        future_predictions=[88, 90],
        chart_type="bar"
    )

    print(f"MCP远程调用结果:")
    print(f"  成功: {result.success}")
    if result.success:
        print(f"  图表URL: {result.url}")
    else:
        print(f"  错误: {result.error}")
        print("  (需要先启动远程MCP服务器: python scripts/run_mcp_server.py --mode http)")


def example_quick_plot():
    """快速绘图函数"""
    print("\n" + "=" * 60)
    print("示例4: 快速绘图函数")
    print("=" * 60)

    result = quick_plot(
        product_name="iPad Air",
        dates=["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
        actual_values=[70, 75, 72, 80],
        predicted_values=[68, 73, 70, 78],
        future_dates=["2024-01-05", "2024-01-06"],
        future_predictions=[82, 85],
        chart_type="combined"
    )

    print(f"快速绘图结果: {result}")


def example_start_server():
    """启动MCP服务器"""
    print("\n" + "=" * 60)
    print("示例5: 启动MCP服务器")
    print("=" * 60)

    print("""
    启动MCP服务器的方式：

    1. Stdio模式 (推荐用于本地集成):
       python scripts/run_mcp_server.py

    2. HTTP模式 (用于远程服务):
       python scripts/run_mcp_server.py --mode http --port 8000

    3. 在Python中启动:
       from src.mcp import MCPChartClient

       client = MCPChartClient(mode="local")
       process = client.start_mcp_server()

       # ... 使用MCP调用 ...

       client.stop_mcp_server(process)
    """)


def main():
    """主函数"""
    print("=" * 60)
    print("MCP 绘图服务使用示例")
    print("=" * 60)

    # 基础调用
    example_direct_call()
    example_mcp_client_local()
    example_quick_plot()

    # 远程调用（需要服务器）
    example_mcp_client_remote()

    # 服务器启动说明
    example_start_server()

    print("\n" + "=" * 60)
    print("示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
