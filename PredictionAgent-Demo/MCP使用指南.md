# MCP (Model Context Protocol) 在PredictionAgent中的使用指南

## 目录

1. [MCP概述](#1-mcp概述)
2. [MCP工作原理](#2-mcp工作原理)
3. [项目中的MCP架构](#3-项目中的mcp架构)
4. [快速开始](#4-快速开始)
5. [MCP服务使用方式](#5-mcp服务使用方式)
6. [MCP客户端使用](#6-mcp客户端使用)
7. [在Agent中集成MCP](#7-在agent中集成mcp)
8. [常见问题](#8-常见问题)

---

## 1. MCP概述

### 什么是MCP？

**MCP (Model Context Protocol)** 是一种开放协议，用于将AI模型与外部工具和服务连接。它允许：

- AI模型调用外部工具（如数据库、API、绘图服务等）
- 标准化工具发现和调用流程
- 支持本地和远程服务调用

### MCP的核心概念

```
┌─────────────┐      MCP Protocol      ┌─────────────┐
│   AI Agent  │ ←──────────────────→  │ MCP Server  │
│             │                       │             │
│  - 发送请求  │                       │  - 实现工具  │
│  - 接收响应  │                       │  - 执行逻辑  │
└─────────────┘                       └─────────────┘
```

**关键组件：**

| 组件 | 作用 |
|------|------|
| **MCP Host** | AI应用程序（如Agent） |
| **MCP Client** | 与Server保持1:1连接的客户端 |
| **MCP Server** | 暴露特定工具的服务程序 |
| **Tools** | Server提供的可调用功能 |

---

## 2. MCP工作原理

### 通信模式

MCP支持两种主要通信模式：

#### 模式一：Stdio模式（本地进程）

```
Agent ←→ stdio ←→ MCP Server (子进程)
```

- MCP Server作为Agent的子进程启动
- 通过标准输入/输出通信
- 适合本地工具调用

#### 模式二：HTTP模式（远程服务）

```
Agent ←→ HTTP ←→ MCP Server (远程/容器)
```

- MCP Server独立运行在本地或远程
- 通过HTTP REST API通信
- 适合微服务架构、容器化部署

### 协议流程

```
1. 初始化
   Client ──→ Server: initialize
   Client ←── Server: protocol_version, capabilities

2. 工具列表
   Client ──→ Server: tools/list
   Client ←── Server: [tool1, tool2, ...]

3. 工具调用
   Client ──→ Server: tools/call { name: "plot_sales_forecast", arguments: {...} }
   Client ←── Server: { result: {...} }

4. 关闭
   Client ──→ Server: shutdown
```

---

## 3. 项目中的MCP架构

### 架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          PredictionAgent                                │
│                                                                         │
│   ┌─────────────┐    ┌──────────────┐    ┌─────────────┐             │
│   │ Product ID  │ → │ Data Fetch   │ → │ Analysis    │             │
│   │   Node      │    │   Node       │    │   Node      │             │
│   └─────────────┘    └──────────────┘    └─────────────┘             │
│                            │                                           │
│                            ▼                                           │
│                      ┌──────────────┐                                  │
│                      │ Chart Node   │                                  │
│                      │ (MCP Client) │                                  │
│                      └──────┬───────┘                                  │
└──────────────────────────────│──────────────────────────────────────────┘
                               │ MCP Protocol
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    MCP Chart Service (绘图服务)                           │
│                                                                         │
│   ┌───────────────────────────────────────────────────────────────┐     │
│   │  Tools:                                                      │     │
│   │  - plot_sales_forecast (绘制销量预测图表)                       │     │
│   │  - 支持: bar / line / combined                             │     │
│   └───────────────────────────────────────────────────────────────┘     │
│                                                                         │
│   ┌───────────────────────────────────────────────────────────────┐     │
│   │  实现: matplotlib                                            │     │
│   └───────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
```

### 文件结构

```
src/
├── mcp/
│   ├── __init__.py
│   ├── chart_mcp_server.py   # MCP服务器（绘图服务实现）
│   │   ├── ChartMCPService   # 绘图服务类
│   │   ├── plot_sales_forecast()  # 绘图工具
│   │   └── MCP Server启动逻辑
│   │
│   └── client.py              # MCP客户端
│       ├── MCPChartClient    # 客户端类
│       ├── plot_sales_forecast()  # 调用方法
│       └── 支持 local/remote 模式

scripts/
└── run_mcp_server.py         # 服务器启动脚本
```

### 为什么使用MCP？

| 优势 | 说明 |
|------|------|
| **解耦** | 绘图服务独立，可单独部署和升级 |
| **复用** | 多个Agent可以共享同一个MCP服务 |
| **扩展** | 易于添加新的工具（数据库查询、API调用等） |
| **测试** | MCP服务可以独立测试 |
| **远程** | 支持远程调用，适合分布式系统 |

---

## 4. 快速开始

### 4.1 安装依赖

```bash
cd PredictionAgent-Demo
pip install -r requirements.txt
```

确保安装以下MCP相关依赖：
```txt
mcp>=1.0.0
fastapi>=0.100.0
uvicorn>=0.23.0
```

### 4.2 快速调用示例

```python
from src.mcp import quick_plot

# 一行代码生成图表
result = quick_plot(
    product_name="iPhone 15 Pro",
    dates=["2024-01-01", "2024-01-02", "2024-01-03"],
    actual_values=[100, 120, 110],
    predicted_values=[95, 118, 115],
    future_dates=["2024-01-04", "2024-01-05"],
    future_predictions=[125, 130],
    chart_type="combined"
)

print(f"图表保存: {result['filepath']}")
print(f"访问URL: {result['url']}")
```

---

## 5. MCP服务使用方式

### 方式一：直接调用服务类

适用于：在同一个Python进程中直接使用绘图功能

```python
from src.mcp.chart_mcp_server import ChartMCPService

# 创建服务实例
service = ChartMCPService(output_dir="output/charts")

# 调用绘图
result = service.plot_sales_forecast(
    product_name="MacBook Pro",
    dates=["2024-01-01", "2024-01-02", "2024-01-03"],
    actual_values=[50, 55, 48],
    predicted_values=[48, 52, 50],
    future_dates=["2024-01-04", "2024-01-05"],
    future_predictions=[60, 62],
    chart_type="line"
)

print(result)
# {
#     "filepath": "output/charts/sales_forecast_abc123.png",
#     "url": "/charts/sales_forecast_abc123.png",
#     "chart_id": "abc123",
#     "chart_type": "line",
#     "success": True
# }
```

### 方式二：启动独立的MCP服务器

#### Stdio模式（本地进程）

```bash
python scripts/run_mcp_server.py
```

服务器会作为子进程运行，通过stdio与调用方通信。

#### HTTP REST模式（独立服务）

```bash
# 启动HTTP服务器
python scripts/run_mcp_server.py --mode http --port 8000

# 测试健康检查
curl http://localhost:8000/health
# {"status": "healthy", "service": "chart-mcp"}

# 调用绘图API
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "product_name": "iPad Air",
    "dates": ["2024-01-01"],
    "actual_values": [70],
    "predicted_values": [68],
    "future_dates": ["2024-01-02"],
    "future_predictions": [75],
    "chart_type": "bar"
  }'
```

---

## 6. MCP客户端使用

### 6.1 本地模式（推荐）

```python
from src.mcp import MCPChartClient

# 创建客户端（本地模式）
client = MCPChartClient(mode="local")

# 调用绘图
result = client.plot_sales_forecast(
    product_name="AirPods Pro",
    dates=["2024-01-01", "2024-01-02"],
    actual_values=[80, 85],
    predicted_values=[78, 82],
    future_dates=["2024-01-03"],
    future_predictions=[90],
    chart_type="combined"
)

print(f"成功: {result.success}")
print(f"URL: {result.url}")
```

### 6.2 远程模式

```python
from src.mcp import MCPChartClient

# 创建客户端（远程模式）
client = MCPChartClient(
    mode="remote",
    server_url="http://localhost:8000"  # MCP服务器地址
)

# 调用绘图
result = client.plot_sales_forecast(
    product_name="Apple Watch",
    dates=["2024-01-01", "2024-01-02"],
    actual_values=[60, 65],
    predicted_values=[58, 62],
    future_dates=["2024-01-03"],
    future_predictions=[70],
    chart_type="line"
)

if result.success:
    print(f"图表: {result.url}")
else:
    print(f"错误: {result.error}")
```

### 6.3 启动和管理MCP服务器

```python
from src.mcp import MCPChartClient

# 创建客户端
client = MCPChartClient(mode="local")

# 启动服务器作为后台进程
process = client.start_mcp_server()
print("MCP服务器已启动")

# ... 执行其他操作 ...

# 停止服务器
client.stop_mcp_server(process)
print("MCP服务器已停止")
```

---

## 7. 在Agent中集成MCP

### 7.1 使用MCP版本的Agent

```python
from src import PredictionAgentMCP

# 创建Agent（自动集成MCP客户端）
agent = PredictionAgentMCP()

# 执行分析
result = agent.analyze(
    query="分析iPhone 15 Pro的销量预测",
    chart_type="combined",
    use_mock_data=True  # 使用模拟数据
)

# 查看结果
if result["success"]:
    print(f"产品: {result['product']['name']}")
    print(f"图表: {result['chart']['url']}")
    print(f"通过MCP生成: {result['chart'].get('via_mcp', False)}")
    print(result["analysis"]["result"])
```

### 7.2 ChartNode中的MCP调用

核心代码在 `src/nodes/chart_node.py`：

```python
from src.mcp import MCPChartClient

class ChartNode(BaseNode):
    def __init__(self, llm_client, mcp_client: MCPChartClient = None):
        super().__init__(llm_client, "ChartGeneration")
        # 注入MCP客户端
        self.mcp_client = mcp_client or MCPChartClient(mode="local")

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # ... 数据准备 ...

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

        # 处理结果
        return {
            "generated": result.success,
            "chart_url": result.url,
            "chart_filepath": result.filepath,
            "chart_id": result.chart_id,
            "chart_type": result.chart_type
        }
```

### 7.3 Agent主控制器中的初始化

```python
from src.mcp import MCPChartClient

class PredictionAgent:
    def __init__(self, config):
        # ... 其他初始化 ...

        # 初始化MCP客户端
        self.mcp_chart_client = MCPChartClient(
            mode="local",  # 或 "remote"
            server_url="http://localhost:8000"
        )

        # 初始化节点（传入MCP客户端）
        self.chart_node = ChartNode(
            self.llm_client,
            self.mcp_chart_client
        )
```

---

## 8. 常见问题

### Q1: Stdio模式和HTTP模式如何选择？

| 场景 | 推荐模式 |
|------|----------|
| 本地开发、快速原型 | Stdio |
| 单进程应用 | Stdio |
| 微服务架构 | HTTP |
| 容器化部署 | HTTP |
| 需要远程调用 | HTTP |

### Q2: 如何调试MCP调用？

```python
from src.mcp import MCPChartClient

client = MCPChartClient(mode="local")

# 启用调试日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 调用
result = client.plot_sales_forecast(...)
```

### Q3: MCP服务器无响应怎么办？

```python
# 检查服务器状态
import requests

try:
    response = requests.get("http://localhost:8000/health", timeout=5)
    print(f"服务器状态: {response.json()}")
except requests.exceptions.Timeout:
    print("服务器响应超时")
except requests.exceptions.ConnectionError:
    print("无法连接到服务器，请确保MCP服务器已启动")
```

### Q4: 如何扩展新的MCP工具？

1. 在 `chart_mcp_server.py` 中添加新方法：

```python
class ChartMCPService:
    def new_tool(self, params):
        """新的工具实现"""
        # 工具逻辑
        return result
```

2. 在 `create_chart_tool()` 的返回列表中添加新工具：

```python
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        await create_chart_tool(),
        Tool(
            name="new_tool",
            description="新工具描述",
            inputSchema={...}
        )
    ]
```

### Q5: 如何处理MCP调用失败？

```python
from src.mcp import MCPChartClient

client = MCPChartClient(mode="local")

try:
    result = client.plot_sales_forecast(...)
    if not result.success:
        # MCP调用失败，使用本地备选
        from src.nodes.chart_node import ChartNode
        node = ChartNode(None)
        result = node.run_local(input_data)
except Exception as e:
    print(f"MCP调用异常: {e}")
    # 降级到本地实现
    result = fallback_local_draw(...)
```

---

## 附录：完整示例

### 完整MCP使用示例

```python
"""
MCP完整使用示例
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.mcp import MCPChartClient, quick_plot
from src.mcp.chart_mcp_server import ChartMCPService
from src import PredictionAgentMCP


def main():
    print("=" * 60)
    print("MCP 使用完整示例")
    print("=" * 60)

    # 示例1: 快速绘图
    print("\n【示例1】快速绘图")
    result = quick_plot(
        product_name="iPhone 15 Pro",
        dates=["2024-01-01", "2024-01-02", "2024-01-03"],
        actual_values=[100, 120, 110],
        predicted_values=[95, 118, 115],
        future_dates=["2024-01-04", "2024-01-05"],
        future_predictions=[125, 130],
        chart_type="combined"
    )
    print(f"图表: {result['url']}")

    # 示例2: MCP客户端本地调用
    print("\n【示例2】MCP客户端本地调用")
    client = MCPChartClient(mode="local")
    result = client.plot_sales_forecast(
        product_name="MacBook Pro",
        dates=["2024-01-01", "2024-01-02"],
        actual_values=[50, 55],
        predicted_values=[48, 52],
        future_dates=["2024-01-03"],
        future_predictions=[60],
        chart_type="line"
    )
    print(f"成功: {result.success}")
    if result.success:
        print(f"图表: {result.url}")

    # 示例3: 使用MCP版Agent
    print("\n【示例3】MCP版Agent")
    try:
        agent = PredictionAgentMCP()
        result = agent.analyze(
            query="分析iPhone的销量预测",
            chart_type="combined",
            use_mock_data=True
        )
        if result["success"]:
            print(f"产品: {result['product']['name']}")
            print(f"图表: {result['chart']['url']}")
            print(f"通过MCP: {result['chart'].get('via_mcp')}")
    except Exception as e:
        print(f"Agent执行: {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
```

---

## 参考资料

- [MCP官方文档](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- 本项目源码: `src/mcp/`

---

*文档版本: 1.0*
*最后更新: 2026-06-17*
