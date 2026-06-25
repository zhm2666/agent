# PredictionAgent-LangGraph

基于 LangGraph 重构的销量预测分析 Agent。

## 与原版对比

| 维度 | PredictionAgent-Demo | PredictionAgent-LangGraph |
|------|----------------------|---------------------------|
| 流程控制 | 手写顺序调用 | LangGraph StateGraph |
| 状态管理 | 自定义 State 类 | TypedDict + checkpointer |
| 节点复用 | 手搓节点类 | 直接复用原节点逻辑 |
| 会话/线程 | 无 | 支持 thread_id 多轮续跑 |
| 持久化 | 文件/内存 | MemorySaver / PostgresSaver |
| 可观测性 | print/日志 | LangSmith / LangGraph Studio |
| 反思重试 | 手写循环 | 条件边 + 状态路由 |

## 目录结构

```text
PredictionAgent-LangGraph/
├── src/
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── builder.py
│   │   └── conditional_routing.py
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── product_identification_node.py
│   │   ├── data_fetch_node.py
│   │   ├── chart_node.py
│   │   ├── analysis_node.py
│   │   └── reflection_node.py
│   ├── state/
│   │   ├── __init__.py
│   │   └── prediction_state.py
│   ├── tools/
│   │   └── chart_tool.py
│   ├── llms/
│   │   └── factory.py
│   └── agent.py
├── examples/
│   └── basic_usage.py
└── requirements.txt
```

## 快速开始

```bash
pip install -r requirements.txt
python examples/basic_usage.py
```