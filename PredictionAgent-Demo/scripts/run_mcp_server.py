#!/usr/bin/env python
"""
MCP Chart Server 独立启动脚本

使用方法:
    python run_mcp_server.py                 # 本地模式
    python run_mcp_server.py --remote        # 远程模式
    python run_mcp_server.py --port 9000    # 指定端口
"""

import argparse
import asyncio
import json
import sys
import os

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


async def run_stdio_server():
    """运行stdio模式的MCP服务器"""
    from src.mcp.chart_mcp_server import ChartMCPService, chart_service
    from mcp.server import Server
    from mcp.types import Tool
    from mcp.server.stdio import stdio_server

    print("启动 MCP Chart Server (stdio模式)...", file=sys.stderr)

    server = Server("chart-mcp-service")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="plot_sales_forecast",
                description="绘制销量预测图表，支持柱状图、折线图和组合图",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "product_name": {"type": "string", "description": "产品名称"},
                        "dates": {"type": "array", "items": {"type": "string"}, "description": "历史日期列表"},
                        "actual_values": {"type": "array", "items": {"type": "number"}, "description": "历史实际销量"},
                        "predicted_values": {"type": "array", "items": {"type": "number"}, "description": "历史预测值"},
                        "future_dates": {"type": "array", "items": {"type": "string"}, "description": "未来日期列表"},
                        "future_predictions": {"type": "array", "items": {"type": "number"}, "description": "未来预测值"},
                        "chart_type": {"type": "string", "enum": ["bar", "line", "combined"], "default": "combined"}
                    },
                    "required": ["product_name", "dates", "actual_values", "predicted_values", "future_dates", "future_predictions"]
                }
            )
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list:
        from mcp.types import TextContent

        if name == "plot_sales_forecast":
            result = chart_service.plot_sales_forecast(
                product_name=arguments.get("product_name", "Unknown"),
                dates=arguments.get("dates", []),
                actual_values=arguments.get("actual_values", []),
                predicted_values=arguments.get("predicted_values", []),
                future_dates=arguments.get("future_dates", []),
                future_predictions=arguments.get("future_predictions", []),
                chart_type=arguments.get("chart_type", "combined")
            )
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
        else:
            return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


async def run_http_server(port: int = 8000):
    """运行HTTP REST模式的MCP服务器"""
    import uvicorn
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import List, Optional

    print(f"启动 MCP Chart Server (HTTP模式, 端口 {port})...", file=sys.stderr)

    app = FastAPI(title="MCP Chart Service")

    class ChartRequest(BaseModel):
        product_name: str
        dates: List[str]
        actual_values: List[float]
        predicted_values: List[float]
        future_dates: List[str]
        future_predictions: List[float]
        chart_type: str = "combined"

    @app.post("/tools/call")
    async def call_tool(request: ChartRequest):
        from src.mcp.chart_mcp_server import ChartMCPService

        service = ChartMCPService(output_dir="output/charts")
        result = service.plot_sales_forecast(
            product_name=request.product_name,
            dates=request.dates,
            actual_values=request.actual_values,
            predicted_values=request.predicted_values,
            future_dates=request.future_dates,
            future_predictions=request.future_predictions,
            chart_type=request.chart_type
        )
        return result

    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "chart-mcp"}

    @app.get("/")
    async def root():
        return {
            "service": "MCP Chart Service",
            "version": "1.0.0",
            "endpoints": {
                "tools_call": "POST /tools/call",
                "health": "GET /health"
            }
        }

    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


def main():
    parser = argparse.ArgumentParser(description="MCP Chart Server")
    parser.add_argument("--mode", choices=["stdio", "http"], default="stdio",
                       help="服务器运行模式")
    parser.add_argument("--port", type=int, default=8000,
                       help="HTTP模式端口号")
    args = parser.parse_args()

    if args.mode == "stdio":
        asyncio.run(run_stdio_server())
    else:
        asyncio.run(run_http_server(args.port))


if __name__ == "__main__":
    main()
