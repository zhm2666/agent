"""
MCP绘图服务
基于Model Context Protocol的远程绘图服务
"""

import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.dates import DateFormatter

# MCP相关导入
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from pydantic import AnyUrl


class ChartMCPService:
    """MCP绘图服务"""

    def __init__(self, output_dir: str = "output/charts"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.server = Server("chart-service")

    def generate_chart_id(self) -> str:
        """生成唯一图表ID"""
        from uuid import uuid4
        return uuid4().hex[:8]

    def plot_sales_forecast(
        self,
        product_name: str,
        dates: List[str],
        actual_values: List[float],
        predicted_values: List[float],
        future_dates: List[str],
        future_predictions: List[float],
        chart_type: str = "combined"
    ) -> Dict[str, Any]:
        """
        绘制销量预测图表（保留原有逻辑）

        Args:
            product_name: 产品名称
            dates: 历史日期列表
            actual_values: 历史真实值
            predicted_values: 模型预测值
            future_dates: 未来日期列表
            future_predictions: 未来预测值
            chart_type: 图表类型 (bar/line/combined)

        Returns:
            包含图表路径和URL的字典
        """
        chart_id = self.generate_chart_id()

        if chart_type == "bar":
            return self._plot_bar_chart(
                product_name, dates, actual_values, predicted_values,
                future_dates, future_predictions, chart_id
            )
        elif chart_type == "line":
            return self._plot_line_chart(
                product_name, dates, actual_values, predicted_values,
                future_dates, future_predictions, chart_id
            )
        else:  # combined
            return self._plot_combined_chart(
                product_name, dates, actual_values, predicted_values,
                future_dates, future_predictions, chart_id
            )

    def _plot_bar_chart(
        self, product_name: str, dates: List[str], actual_values: List[float],
        predicted_values: List[float], future_dates: List[str],
        future_predictions: List[float], chart_id: str
    ) -> Dict[str, Any]:
        """绘制柱状图"""
        fig, ax = plt.subplots(figsize=(14, 6))

        all_dates = dates + future_dates
        all_actual = actual_values + [0] * len(future_dates)
        all_predicted = predicted_values + future_predictions

        x = range(len(all_dates))
        width = 0.35

        bars1 = ax.bar([i - width/2 for i in x], all_actual, width,
                       label='实际销量', color='#2ecc71', alpha=0.8)
        bars2 = ax.bar([i + width/2 for i in x], all_predicted, width,
                       label='预测销量', color='#3498db', alpha=0.8)

        ax.axvline(x=len(dates) - 0.5, color='red', linestyle='--',
                   linewidth=2, label='预测分界线')

        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('销量', fontsize=12)
        ax.set_title(f'{product_name} - 销量预测分析 (柱状图)', fontsize=14, fontweight='bold')
        ax.set_xticks(x[::max(1, len(x)//10)])
        ax.set_xticklabels([all_dates[i] for i in range(0, len(all_dates), max(1, len(all_dates)//10))],
                          rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()

        filename = f"sales_forecast_{chart_id}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return {
            "filepath": filepath,
            "url": f"/charts/{filename}",
            "chart_id": chart_id,
            "chart_type": "bar",
            "success": True
        }

    def _plot_line_chart(
        self, product_name: str, dates: List[str], actual_values: List[float],
        predicted_values: List[float], future_dates: List[str],
        future_predictions: List[float], chart_id: str
    ) -> Dict[str, Any]:
        """绘制折线图"""
        fig, ax = plt.subplots(figsize=(14, 6))

        from datetime import datetime
        all_dates = [datetime.strptime(d, '%Y-%m-%d') for d in dates + future_dates]

        hist_dates = all_dates[:len(dates)]
        future_all_dates = all_dates[len(dates):]

        ax.plot(hist_dates, actual_values, 'g-o', linewidth=2,
                markersize=6, label='实际销量', color='#2ecc71')
        ax.plot(hist_dates, predicted_values[:len(hist_dates)], 'b--s', linewidth=2,
                markersize=5, label='模型预测', color='#3498db')
        ax.plot(future_all_dates, future_predictions, 'r-^', linewidth=2,
                markersize=6, label='未来预测', color='#e74c3c')

        ax.axvline(x=hist_dates[-1], color='red', linestyle='--',
                   linewidth=2, label='预测分界线')

        ax.fill_between(future_all_dates,
                       [p * 0.9 for p in future_predictions],
                       [p * 1.1 for p in future_predictions],
                       alpha=0.2, color='#e74c3c', label='预测置信区间(±10%)')

        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('销量', fontsize=12)
        ax.set_title(f'{product_name} - 销量预测分析 (折线图)', fontsize=14, fontweight='bold')
        ax.xaxis.set_major_formatter(DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45, ha='right')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        filename = f"sales_forecast_{chart_id}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return {
            "filepath": filepath,
            "url": f"/charts/{filename}",
            "chart_id": chart_id,
            "chart_type": "line",
            "success": True
        }

    def _plot_combined_chart(
        self, product_name: str, dates: List[str], actual_values: List[float],
        predicted_values: List[float], future_dates: List[str],
        future_predictions: List[float], chart_id: str
    ) -> Dict[str, Any]:
        """绘制组合图表"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10),
                                        gridspec_kw={'height_ratios': [2, 1]})

        all_dates = dates + future_dates
        from datetime import datetime
        x = range(len(all_dates))

        # 上图：柱状图
        width = 0.4
        ax1.bar([i - width/2 for i in x[:len(dates)]], actual_values, width,
                label='实际销量', color='#2ecc71', alpha=0.8)
        ax1.bar([i + width/2 for i in x[:len(dates)]], predicted_values[:len(dates)], width,
                label='模型预测', color='#3498db', alpha=0.8)
        ax1.bar([i for i in x[len(dates):]], future_predictions, width,
                label='未来预测', color='#e74c3c', alpha=0.8)

        ax1.axvline(x=len(dates) - 0.5, color='red', linestyle='--',
                    linewidth=2, label='预测分界线')
        ax1.set_ylabel('销量', fontsize=12)
        ax1.set_title(f'{product_name} - 销量预测综合分析', fontsize=14, fontweight='bold')
        ax1.set_xticks(x[::max(1, len(x)//8)])
        ax1.set_xticklabels([all_dates[i] for i in range(0, len(all_dates), max(1, len(all_dates)//8))],
                            rotation=45, ha='right')
        ax1.legend(loc='upper left')
        ax1.grid(axis='y', alpha=0.3)

        # 下图：误差分析
        errors = [actual_values[i] - predicted_values[i]
                  for i in range(min(len(actual_values), len(predicted_values)))]
        colors = ['#2ecc71' if e >= 0 else '#e74c3c' for e in errors]
        ax2.bar(range(len(errors)), errors, color=colors, alpha=0.8)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax2.set_xlabel('时间序列', fontsize=12)
        ax2.set_ylabel('预测误差', fontsize=12)
        ax2.set_title('预测误差分析 (实际值 - 预测值)', fontsize=12)
        ax2.grid(axis='y', alpha=0.3)

        mape = sum(abs(actual_values[i] - predicted_values[i]) / actual_values[i]
                   for i in range(len(actual_values))) / len(actual_values) * 100
        ax2.text(0.02, 0.95, f'MAPE: {mape:.2f}%', transform=ax2.transAxes,
                fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()

        filename = f"sales_forecast_{chart_id}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return {
            "filepath": filepath,
            "url": f"/charts/{filename}",
            "chart_id": chart_id,
            "chart_type": "combined",
            "success": True
        }

    def get_chart_info(self, chart_id: str) -> Dict[str, Any]:
        """获取图表信息"""
        for ext in ['png', 'jpg', 'jpeg']:
            filepath = os.path.join(self.output_dir, f"sales_forecast_{chart_id}.{ext}")
            if os.path.exists(filepath):
                return {
                    "exists": True,
                    "filepath": filepath,
                    "url": f"/charts/sales_forecast_{chart_id}.{ext}",
                    "chart_id": chart_id
                }
        return {"exists": False, "chart_id": chart_id}


# 创建服务实例
chart_service = ChartMCPService()


# MCP工具定义
async def create_chart_tool() -> Tool:
    """创建MCP图表工具"""
    return Tool(
        name="plot_sales_forecast",
        description="绘制销量预测图表，支持柱状图、折线图和组合图",
        inputSchema={
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "产品名称"
                },
                "dates": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "历史日期列表 (YYYY-MM-DD格式)"
                },
                "actual_values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "历史实际销量"
                },
                "predicted_values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "历史模型预测值"
                },
                "future_dates": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "未来日期列表"
                },
                "future_predictions": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "未来预测值"
                },
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "combined"],
                    "description": "图表类型",
                    "default": "combined"
                }
            },
            "required": ["product_name", "dates", "actual_values", "predicted_values", "future_dates", "future_predictions"]
        }
    )


async def handle_chart_request(arguments: Dict[str, Any]) -> TextContent:
    """处理图表请求"""
    try:
        result = chart_service.plot_sales_forecast(
            product_name=arguments.get("product_name", "Unknown"),
            dates=arguments.get("dates", []),
            actual_values=arguments.get("actual_values", []),
            predicted_values=arguments.get("predicted_values", []),
            future_dates=arguments.get("future_dates", []),
            future_predictions=arguments.get("future_predictions", []),
            chart_type=arguments.get("chart_type", "combined")
        )

        return TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2)
        )
    except Exception as e:
        return TextContent(
            type="text",
            text=json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
        )


# MCP服务器主函数
async def main():
    """MCP服务器主函数"""
    from mcp.server import Server
    from mcp.server.stdio import stdio_server

    server = Server("chart-mcp-service")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """列出所有可用工具"""
        return [await create_chart_tool()]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
        """调用工具"""
        if name == "plot_sales_forecast":
            result = await handle_chart_request(arguments)
            return [result]
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    # 启动服务器
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
