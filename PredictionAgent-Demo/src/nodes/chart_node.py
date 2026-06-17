"""
图表生成节点 - MCP版本
通过MCP协议调用远程绘图服务
"""

from typing import Dict, Any
from .base_node import BaseNode
from ..mcp import MCPChartClient, quick_plot


class ChartNode(BaseNode):
    """图表生成节点 - MCP调用版本"""

    def __init__(self, llm_client, mcp_client: MCPChartClient = None):
        super().__init__(llm_client, "ChartGeneration")
        # MCP客户端用于调用远程绘图服务
        self.mcp_client = mcp_client or MCPChartClient(mode="local")

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行图表生成（通过MCP调用）

        Args:
            input_data: {
                "product_name": str,
                "chart_type": str,  # bar, line, combined
                "historical_data": List[Dict],
                "future_predictions": List[Dict],
                "model_predictions": List[Dict] (可选)
            }

        Returns:
            {
                "generated": bool,
                "chart_type": str,
                "chart_url": str,
                "chart_filepath": str,
                "chart_id": str
            }
        """
        product_name = input_data.get("product_name", "Unknown Product")
        chart_type = input_data.get("chart_type", "combined")
        historical_data = input_data.get("historical_data", [])
        future_predictions = input_data.get("future_predictions", [])
        model_predictions = input_data.get("model_predictions", [])

        if not historical_data:
            return {
                "generated": False,
                "chart_type": chart_type,
                "chart_url": "",
                "chart_filepath": "",
                "chart_id": "",
                "error": "没有数据可绘制"
            }

        self.log_info(f"正在通过MCP生成图表: {product_name}, 类型: {chart_type}")

        try:
            # 提取日期和值
            dates = [d["date"] for d in historical_data]
            actual_values = [d["actual_value"] for d in historical_data]

            # 使用模型预测值（如果有）或历史预测
            if model_predictions:
                predicted_values = [p["predicted_value"] for p in model_predictions[:len(dates)]]
            else:
                predicted_values = [d.get("predicted_value", 0) for d in historical_data]

            # 补齐长度
            while len(predicted_values) < len(dates):
                predicted_values.append(predicted_values[-1] if predicted_values else 0)

            # 未来预测数据
            future_dates = [p["date"] for p in future_predictions]
            future_pred_values = [p["predicted_value"] for p in future_predictions]

            # 通过MCP调用绘图服务
            result = self.mcp_client.plot_sales_forecast(
                product_name=product_name,
                dates=dates,
                actual_values=actual_values,
                predicted_values=predicted_values,
                future_dates=future_dates,
                future_predictions=future_pred_values,
                chart_type=chart_type
            )

            # 转换结果格式
            chart_result = {
                "generated": result.success,
                "chart_type": result.chart_type or chart_type,
                "chart_url": result.url,
                "chart_filepath": result.filepath,
                "chart_id": result.chart_id,
                "error": result.error if not result.success else ""
            }

            if chart_result["generated"]:
                self.log_info(f"MCP图表生成成功: {result.url}")
            else:
                self.log_error(f"MCP图表生成失败: {result.error}")

            return chart_result

        except Exception as e:
            self.log_error(f"图表生成失败: {str(e)}")
            return {
                "generated": False,
                "chart_type": chart_type,
                "chart_url": "",
                "chart_filepath": "",
                "chart_id": "",
                "error": str(e)
            }

    def run_local(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        本地直接调用绘图（不使用MCP）

        当MCP服务器不可用时，使用本地直接调用作为备选
        """
        product_name = input_data.get("product_name", "Unknown Product")
        chart_type = input_data.get("chart_type", "combined")
        historical_data = input_data.get("historical_data", [])
        future_predictions = input_data.get("future_predictions", [])
        model_predictions = input_data.get("model_predictions", [])

        if not historical_data:
            return {
                "generated": False,
                "error": "没有数据可绘制"
            }

        self.log_info(f"正在本地生成图表: {product_name}")

        try:
            # 提取数据
            dates = [d["date"] for d in historical_data]
            actual_values = [d["actual_value"] for d in historical_data]

            if model_predictions:
                predicted_values = [p["predicted_value"] for p in model_predictions[:len(dates)]]
            else:
                predicted_values = [d.get("predicted_value", 0) for d in historical_data]

            while len(predicted_values) < len(dates):
                predicted_values.append(predicted_values[-1] if predicted_values else 0)

            future_dates = [p["date"] for p in future_predictions]
            future_pred_values = [p["predicted_value"] for p in future_predictions]

            # 直接调用quick_plot
            result = quick_plot(
                product_name=product_name,
                dates=dates,
                actual_values=actual_values,
                predicted_values=predicted_values,
                future_dates=future_dates,
                future_predictions=future_pred_values,
                chart_type=chart_type
            )

            return {
                "generated": result.get("success", False),
                "chart_type": result.get("chart_type", chart_type),
                "chart_url": result.get("url", ""),
                "chart_filepath": result.get("filepath", ""),
                "chart_id": result.get("chart_id", ""),
                "error": "" if result.get("success") else "生成失败"
            }

        except Exception as e:
            self.log_error(f"本地图表生成失败: {str(e)}")
            return {
                "generated": False,
                "error": str(e)
            }

    def select_chart_type(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """根据数据特征推荐图表类型"""
        data_points = len(input_data.get("historical_data", []))
        has_model_predictions = len(input_data.get("model_predictions", [])) > 0
        user_preference = input_data.get("chart_type", "combined")

        if user_preference in ["bar", "line", "combined"]:
            return {
                "chart_type": user_preference,
                "reasoning": f"用户指定: {user_preference}"
            }

        if has_model_predictions or data_points > 30:
            return {
                "chart_type": "combined",
                "reasoning": "数据量大且包含模型预测，适合使用综合图表"
            }
        else:
            return {
                "chart_type": "line",
                "reasoning": "数据量适中，适合使用折线图展示趋势"
            }
