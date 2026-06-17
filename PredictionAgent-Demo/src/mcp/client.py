"""
MCP客户端
用于Agent调用MCP服务的客户端
"""

import json
import subprocess
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class MCPChartResult:
    """MCP图表结果"""
    success: bool
    filepath: str = ""
    url: str = ""
    chart_id: str = ""
    chart_type: str = ""
    error: str = ""


class MCPChartClient:
    """
    MCP图表客户端

    通过MCP协议调用远程绘图服务
    支持本地子进程模式和远程HTTP模式
    """

    def __init__(
        self,
        mode: str = "local",  # local 或 remote
        server_url: str = "http://localhost:8000",
        mcp_server_path: Optional[str] = None
    ):
        """
        初始化MCP客户端

        Args:
            mode: 调用模式
                - "local": 启动本地子进程调用
                - "remote": HTTP远程调用
            server_url: 远程服务器URL（remote模式）
            mcp_server_path: MCP服务器脚本路径（local模式）
        """
        self.mode = mode
        self.server_url = server_url
        self.mcp_server_path = mcp_server_path or self._find_mcp_server()

    def _find_mcp_server(self) -> str:
        """查找MCP服务器脚本"""
        # 尝试多种路径
        possible_paths = [
            os.path.join(os.path.dirname(__file__), "chart_mcp_server.py"),
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp", "chart_mcp_server.py"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return "src/mcp/chart_mcp_server.py"

    def plot_sales_forecast(
        self,
        product_name: str,
        dates: List[str],
        actual_values: List[float],
        predicted_values: List[float],
        future_dates: List[str],
        future_predictions: List[float],
        chart_type: str = "combined"
    ) -> MCPChartResult:
        """
        绘制销量预测图表

        Args:
            product_name: 产品名称
            dates: 历史日期列表
            actual_values: 历史实际销量
            predicted_values: 历史模型预测值
            future_dates: 未来日期列表
            future_predictions: 未来预测值
            chart_type: 图表类型 (bar/line/combined)

        Returns:
            MCPChartResult: 包含图表路径和URL
        """
        if self.mode == "remote":
            return self._call_remote(
                product_name, dates, actual_values, predicted_values,
                future_dates, future_predictions, chart_type
            )
        else:
            return self._call_local(
                product_name, dates, actual_values, predicted_values,
                future_dates, future_predictions, chart_type
            )

    def _build_mcp_request(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """构建MCP请求"""
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

    def _call_local(
        self,
        product_name: str,
        dates: List[str],
        actual_values: List[float],
        predicted_values: List[float],
        future_dates: List[str],
        future_predictions: List[float],
        chart_type: str
    ) -> MCPChartResult:
        """
        本地子进程模式调用

        直接导入并调用ChartMCPService，保持原有逻辑
        """
        try:
            # 直接调用服务（避免子进程开销）
            from .chart_mcp_server import ChartMCPService

            service = ChartMCPService(output_dir="output/charts")
            result = service.plot_sales_forecast(
                product_name=product_name,
                dates=dates,
                actual_values=actual_values,
                predicted_values=predicted_values,
                future_dates=future_dates,
                future_predictions=future_predictions,
                chart_type=chart_type
            )

            return MCPChartResult(
                success=result.get("success", False),
                filepath=result.get("filepath", ""),
                url=result.get("url", ""),
                chart_id=result.get("chart_id", ""),
                chart_type=result.get("chart_type", chart_type)
            )

        except Exception as e:
            return MCPChartResult(
                success=False,
                error=f"本地调用失败: {str(e)}"
            )

    def _call_remote(
        self,
        product_name: str,
        dates: List[str],
        actual_values: List[float],
        predicted_values: List[float],
        future_dates: List[str],
        future_predictions: List[float],
        chart_type: str
    ) -> MCPChartResult:
        """
        远程HTTP模式调用

        通过HTTP API调用远程MCP服务器
        """
        try:
            import requests

            response = requests.post(
                f"{self.server_url}/tools/call",
                json={
                    "name": "plot_sales_forecast",
                    "arguments": {
                        "product_name": product_name,
                        "dates": dates,
                        "actual_values": actual_values,
                        "predicted_values": predicted_values,
                        "future_dates": future_dates,
                        "future_predictions": future_predictions,
                        "chart_type": chart_type
                    }
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return MCPChartResult(
                    success=result.get("success", False),
                    filepath=result.get("filepath", ""),
                    url=result.get("url", ""),
                    chart_id=result.get("chart_id", ""),
                    chart_type=result.get("chart_type", chart_type)
                )
            else:
                return MCPChartResult(
                    success=False,
                    error=f"HTTP错误: {response.status_code}"
                )

        except ImportError:
            return MCPChartResult(
                success=False,
                error="requests库未安装，请使用本地模式或安装requests: pip install requests"
            )
        except Exception as e:
            return MCPChartResult(
                success=False,
                error=f"远程调用失败: {str(e)}"
            )

    def start_mcp_server(self) -> subprocess.Popen:
        """
        启动MCP服务器（作为后台进程）

        Returns:
            subprocess.Popen: 服务器进程
        """
        if self.mode != "local":
            raise ValueError("仅本地模式支持启动服务器")

        process = subprocess.Popen(
            ["python", self.mcp_server_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return process

    def stop_mcp_server(self, process: subprocess.Popen):
        """停止MCP服务器"""
        if process:
            process.terminate()
            process.wait(timeout=5)


# 便捷函数：直接调用绘图（保持原有API风格）
def quick_plot(
    product_name: str,
    dates: List[str],
    actual_values: List[float],
    predicted_values: List[float],
    future_dates: List[str],
    future_predictions: List[float],
    chart_type: str = "combined",
    output_dir: str = "output/charts"
) -> Dict[str, Any]:
    """
    快速绘图函数（保持原有调用方式）

    这个函数直接调用ChartMCPService，模拟MCP调用但不启动额外进程
    实际MCP调用通过MCPChartClient类
    """
    from .chart_mcp_server import ChartMCPService

    service = ChartMCPService(output_dir=output_dir)
    return service.plot_sales_forecast(
        product_name=product_name,
        dates=dates,
        actual_values=actual_values,
        predicted_values=predicted_values,
        future_dates=future_dates,
        future_predictions=future_predictions,
        chart_type=chart_type
    )
