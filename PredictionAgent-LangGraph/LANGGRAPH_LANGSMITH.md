# LangSmith 日志集成指南

本文档讲解如何将 LangGraph 的执行日志导出到 LangSmith，实现追踪、可视化、调试和性能分析。

---

## 目录

1. [LangSmith 是什么](#1-langsmith-是什么)
2. [快速接入（三步完成）](#2-快速接入三步完成)
3. [环境变量配置详解](#3-环境变量配置详解)
4. [在代码中配置 LangSmith](#4-在代码中配置-langsmith)
5. [给 trace 打标签和元数据](#5-给-trace-打标签和元数据)
6. [按 user_id / session_id / thread_id 过滤 trace](#6-按-user_id--session_id--thread_id-过滤-trace)
7. [LangSmith Dashboard 各面板解读](#7-langsmith-dashboard-各面板解读)
8. [生产环境最佳实践](#8-生产环境最佳实践)
9. [常见问题](#9-常见问题)

---

## 1. LangSmith 是什么

LangSmith 是 LangChain 官方推出的 LLM 应用调试平台，核心功能：

| 功能 | 说明 |
|------|------|
| **Trace 追踪** | 记录每个节点的输入、输出、执行时间 |
| **Prompt 调试** | 实时修改 prompt 并重新运行 |
| **评估测试** | 对 LLM 输出做自动化质量评估 |
| **数据集管理** | 管理测试用例，对比不同版本的输出 |
| **用量统计** | 按 user_id、模型、租户统计调用量和费用 |

LangSmith 与 LangGraph 无缝集成：只需设置环境变量，无需改代码，LangGraph 会自动把每个节点的执行记录发送到 LangSmith。

---

## 2. 快速接入（三步完成）

### 第一步：获取 LangSmith API Key

1. 访问 [smith.langchain.com](https://smith.langchain.com)
2. 注册/登录账号
3. 进入 **Settings** → **API Keys** → **Create API Key**
4. 复制生成的 key（格式：`lsv2_pt_xxxxxxxx`）

### 第二步：设置环境变量

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=lsv2_pt_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export LANGCHAIN_PROJECT=PredictionAgent   # 项目名，可选，默认 "default"
export LANGCHAIN_ENDPOINT=https://api.smith.langchain.com  # 可选
```

或者在 `.env` 文件里：

```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_xxxxxxxx
LANGCHAIN_PROJECT=PredictionAgent
```

### 第三步：运行代码（无需改代码）

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=lsv2_pt_xxxxxxxx
export LANGCHAIN_PROJECT=PredictionAgent

python examples/basic_usage.py
```

运行后，打开 [smith.langchain.com](https://smith.langchain.com)，在 **Traces** 面板就能看到每一条执行记录。

---

## 3. 环境变量配置详解

| 环境变量 | 必须 | 说明 | 示例 |
|---------|------|------|------|
| `LANGCHAIN_TRACING_V2` | ✅ | 开启 v2 追踪，写 `true` | `true` |
| `LANGCHAIN_API_KEY` | ✅ | LangSmith API Key | `lsv2_pt_xxxx` |
| `LANGCHAIN_PROJECT` | ❌ | 项目名，用来分组 traces | `PredictionAgent` |
| `LANGCHAIN_ENDPOINT` | ❌ | API 端点，国内可能需要代理 | `https://api.smith.langchain.com` |
| `LANGCHAIN_VERIFY_API_KEY` | ❌ | 启动时验证 key 是否有效 | `true` |
| `LANGCHAIN_HIDE_INPUT_MESSAGES` | ❌ | 隐藏 trace 里的输入（脱敏） | `true` |
| `LANGCHAIN_HIDE_OUTPUT_MESSAGES` | ❌ | 隐藏 trace 里的输出 | `true` |

> **国内用户注意**：如果访问 `smith.langchain.com` 较慢，可以设置代理：
> ```bash
> export HTTPS_PROXY=http://127.0.0.1:7890
> export HTTP_PROXY=http://127.0.0.1:7890
> ```

---

## 4. 在代码中配置 LangSmith

除了环境变量，也可以在 Python 代码里直接配置，优先级更高：

### 4.1 初始化时配置

```python
import os
from langsmith import Client

# 方式A：设置环境变量
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "lsv2_pt_xxxx"
os.environ["LANGCHAIN_PROJECT"] = "PredictionAgent-Prod"

# 方式B：用 Client 配置（优先级更高）
from langchain_core.runnables.config import configure RunnableConfig

# 在调用 app.invoke 时传入 config
config = {
    "configurable": {
        "thread_id": "user-123",
        "user_id": "user-001",
    },
    "metadata": {
        "project": "PredictionAgent-Prod",  # 会覆盖环境变量
        "tenant": "enterprise",
    },
    "tags": ["production", "analysis"],  # 打标签
}

final_state = app.invoke(initial_state, config)
```

### 4.2 自动注入 metadata

在 `app.invoke()` 时通过 `metadata` 可以给每次 trace 自动注入上下文：

```python
from langchain_core.runnables.config import RunnableConfig

config = RunnableConfig(
    configurable={
        "thread_id": "chat-001",
        "user_id": "user-001",
    },
    metadata={
        "tenant_id": "tenant-abc",
        "environment": "production",
        "feature": "sales_forecast",
        "llm_provider": "deepseek",
    },
    tags=["forecast", "v2"],
)

# LangSmith 里可以按这些 metadata 过滤 trace
final_state = app.invoke(initial_state, config)
```

### 4.3 给每个 trace 设置名称

默认 trace 名称是类名或函数名，可以通过 `run_name` 自定义：

```python
config = RunnableConfig(
    configurable={"thread_id": "chat-001"},
    run_name="销量预测-完整流程-v2",  # 在 LangSmith 里显示的名称
)

final_state = app.invoke(initial_state, config)
```

---

## 5. 给 trace 打标签和元数据

### 5.1 metadata vs tags vs configurable

```
config = RunnableConfig(
    configurable={          # LangGraph checkpointer 使用的字段
        "thread_id": "chat-001",
        "user_id": "user-001",
    },
    metadata={             # LangSmith trace 的元数据（可过滤/统计）
        "tenant_id": "tenant-abc",
        "llm_model": "deepseek-chat",
        "chart_type": "combined",
        "use_mock_data": False,
    },
    tags=[                # 标签（用于分组和快速筛选）
        "production",
        "forecast",
        "v2"
    ],
)
```

在 LangSmith Dashboard 中：

- **metadata** → 可以按任意字段过滤（支持精确查询和范围查询）
- **tags** → 左侧边栏标签筛选（快速勾选）
- **configurable** → 不会自动出现在 LangSmith，但会透传到 checkpointer

### 5.2 在节点里动态添加 metadata

有时需要在节点执行过程中动态添加 metadata，比如根据识别结果决定 tags：

```python
def analysis_node(state: AgentState) -> dict:
    product_code = state.get("prediction_state", {}).get("product_identification", {}).get("product_code", "")

    # 动态决定 tags
    tags = ["analysis"]
    if "P00" in product_code:
        tags.append("apple-products")
    if not state.get("prediction_state", {}).get("data_fetch", {}).get("fetched"):
        tags.append("fallback-mode")

    # 手动把 metadata 写入状态，供后续 trace 使用
    return {
        "prediction_state": {
            **state.get("prediction_state", {}),
            "step": "analysis",
            "analysis": {...},
        },
        "_metadata": {
            "product_category": _infer_category(product_code),
            "data_quality": "high" if len(state.get("prediction_state", {}).get("data_fetch", {}).get("historical_data", [])) > 30 else "low",
        }
    }
```

### 5.3 trace 截图示例

一条完整的 trace 在 LangSmith 里看起来是这样的：

```
PredictionAgent-analyze
├── run_type: chain
├── start_time: 2026-06-25 22:00:00
├── duration: 3.2s
├── metadata:
│   ├── thread_id: chat-001
│   ├── user_id: user-001
│   ├── tenant_id: tenant-abc
│   └── llm_model: deepseek-chat
├── tags: [production, forecast]
│
├── ▶ product_identification
│   ├── run_type: tool
│   ├── input: {"user_query": "分析 iPhone 销量"}
│   ├── output: {"product_code": "P001", "confidence": 0.95}
│   └── duration: 0.8s
│
├── ▶ data_fetch
│   ├── run_type: tool
│   ├── input: {"product_code": "P001"}
│   ├── output: {"historical_data": [...], "statistics": {...}}
│   └── duration: 0.5s
│
├── ▶ chart_generation
│   ├── run_type: tool
│   ├── input: {"product_name": "iPhone 15 Pro", "chart_type": "combined"}
│   ├── output: {"chart_url": "/charts/xxx.png"}
│   └── duration: 1.2s
│
└── ▶ analysis
    ├── run_type: chain
    ├── input: {...}
    ├── output: {"analysis_result": "iPhone 销量呈上升趋势..."}
    └── duration: 0.7s
```

---

## 6. 按 user_id / session_id / thread_id 过滤 trace

### 6.1 在代码里过滤

LangSmith 提供 Python SDK，可以按字段过滤 trace：

```python
from langsmith import Client

client = Client(api_key="lsv2_pt_xxxx")

# 方式1：按 metadata 字段过滤
traces = client.list_runs(
    project_name="PredictionAgent",
    filter='and(eq(metadata.user_id, "user-001"), eq(metadata.tenant_id, "tenant-abc"))',
    limit=50,
)

for run in traces:
    print(run.id, run.duration, run.outputs)

# 方式2：按 tags 过滤
traces = client.list_runs(
    project_name="PredictionAgent",
    filter='and(eq(tags, "production"), eq(tags, "forecast"))',
    limit=20,
)

# 方式3：按时间范围过滤
from datetime import datetime, timedelta
start = datetime.now() - timedelta(hours=1)

traces = client.list_runs(
    project_name="PredictionAgent",
    filter='gte(start_time, now() - duration("1h"))',
    limit=100,
)

# 方式4：按执行时间过滤（慢查询分析）
traces = client.list_runs(
    project_name="PredictionAgent",
    filter='gt(duration_ms, 5000)',  # 执行时间超过 5 秒的 trace
    limit=50,
)
```

### 6.2 过滤语法速查

| 需求 | filter 语法 |
|------|-----------|
| user_id = "user-001" | `eq(metadata.user_id, "user-001")` |
| tenant_id = "abc" | `eq(metadata.tenant_id, "abc")` |
| 包含某个 tag | `eq(tags, "production")` |
| 执行时间 > 5 秒 | `gt(duration_ms, 5000)` |
| 最近 1 小时 | `gte(start_time, now() - duration("1h"))` |
| 最近 24 小时 | `gte(start_time, now() - duration("1d"))` |
| AND 组合 | `and(eq(...), gt(...))` |
| OR 组合 | `or(eq(...), eq(...))` |

### 6.3 在 LangSmith Dashboard 里过滤

在 LangSmith 网页端，左侧边栏支持快速筛选：

1. **Project** → 选择项目
2. **Start time** → 选择时间范围
3. **Status** → 成功 / 失败 / 运行中
4. **Tags** → 勾选标签
5. **Metadata** → 输入 key:value 过滤

### 6.4 分析 user_id 维度的用量统计

```python
from collections import defaultdict
from langsmith import Client

client = Client(api_key="lsv2_pt_xxxx")

# 获取最近 7 天的所有 trace
runs = client.list_runs(
    project_name="PredictionAgent",
    filter='gte(start_time, now() - duration("7d"))',
    limit=1000,
)

# 按 user_id 统计
user_stats = defaultdict(lambda: {"count": 0, "total_duration_ms": 0})

for run in runs:
    user_id = run.metadata.get("user_id", "unknown")
    user_stats[user_id]["count"] += 1
    user_stats[user_id]["total_duration_ms"] += run.duration_ms or 0

print("\n=== 用户用量统计（最近7天）===")
for user_id, stats in sorted(user_stats.items(), key=lambda x: x[1]["count"], reverse=True):
    avg_duration = stats["total_duration_ms"] / stats["count"] / 1000
    print(f"{user_id}: {stats['count']} 次调用, 平均耗时 {avg_duration:.1f}s")
```

---

## 7. LangSmith Dashboard 各面板解读

### 7.1 Traces（追踪面板）

![trace_list]

展示所有 trace 列表，可按时间、状态、tags、metadata 过滤。

每条 trace 显示：
- 名称和状态（成功✅ / 失败❌）
- 持续时间
- 开始时间
- 节点数

### 7.2 Trace Detail（详情面板）

点击某条 trace 进入详情页，可以看到：

- **时间线视图**：每个节点的执行顺序和耗时
- **输入/输出**：每个节点的完整输入输出 JSON
- **Token 用量**：消耗了多少输入/输出 tokens
- **错误信息**：如果失败，显示错误堆栈

### 7.3 Datasets（数据集面板）

可以上传测试用例，自动评估 Agent 输出质量：

```python
# 创建数据集
dataset = client.create_dataset(
    project_name="PredictionAgent",
    description="销量预测测试集",
)

# 添加测试用例
client.create_examples(
    dataset_id=dataset.id,
    inputs=[
        {"user_query": "分析 iPhone 15 Pro 的销量"},
        {"user_query": "预测 MacBook 的趋势"},
    ],
    outputs=[
        {"expected_product": "P001"},
        {"expected_product": "P002"},
    ],
)

# 运行评估
from langchain.smith import RunEvalConfig, evaluation

eval_config = RunEvalConfig(
    evaluators=[
        evaluation.ExampleQualityEvaluator(),  # 输出质量评分
    ]
)

client.run_on_dataset(
    dataset_name="销量预测测试集",
    llm_or_chain_factory=lambda: app,
    evaluation_config=eval_config,
)
```

### 7.4 Statistics（统计面板）

按时间维度统计：
- 总调用量趋势
- 成功率 / 失败率
- P50 / P95 / P99 延迟
- Token 消耗量
- 按 user_id / tenant_id 分组

---

## 8. 生产环境最佳实践

### 8.1 敏感数据脱敏

如果 trace 里包含敏感数据（如用户个人信息），可以：

```python
# 方式1：全局隐藏
os.environ["LANGCHAIN_HIDE_INPUT_MESSAGES"] = "true"
os.environ["LANGCHAIN_HIDE_OUTPUT_MESSAGES"] = "true"

# 方式2：按 trace 隐藏
config = RunnableConfig(
    configurable={"thread_id": "..."},
    metadata={"_hide": True},  # LangSmith 不会记录输入输出
)
```

### 8.2 采样率（避免费用爆炸）

高频调用场景下，可以只采样部分 trace 上传：

```python
import random

SAMPLE_RATE = 0.1  # 只上传 10% 的 trace

def maybe_trace(state, config):
    if random.random() < SAMPLE_RATE:
        # 正常追踪
        return app.invoke(state, config)
    else:
        # 跳过追踪，直接执行（但 checkpointer 仍然生效）
        # 需要用 None tracer
        from langsmith import tracing_context
        with tracing_context(enabled=False):
            return app.invoke(state, config)
```

### 8.3 多环境隔离

用不同的 `LANGCHAIN_PROJECT` 隔离环境：

```python
import os

ENV = os.getenv("APP_ENV", "development")

PROJECT_MAP = {
    "development": "PredictionAgent-Dev",
    "staging": "PredictionAgent-Staging",
    "production": "PredictionAgent-Prod",
}

os.environ["LANGCHAIN_PROJECT"] = PROJECT_MAP.get(ENV, "PredictionAgent-Dev")

# 也可以在代码里动态设置
config = RunnableConfig(
    metadata={"environment": ENV},
    # project_name 会覆盖环境变量
)
```

### 8.4 异步上报（不影响主流程）

LangSmith 默认是同步上报，如果网络延迟影响响应时间：

```python
# LangSmith 支持异步队列，会在后台线程上传
# 无需额外配置，默认就是异步的

# 如果想确保不阻塞，可以在独立线程池里执行
import concurrent.futures

executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

def analyze_async(query, thread_id):
    future = executor.submit(agent.analyze, query, thread_id)
    return future.result()

# 主流程不等待 LangSmith 上报
```

### 8.5 与 Prometheus / Grafana 集成

```python
from langsmith import Client
from prometheus_client import Counter, Histogram, Gauge

# Prometheus 指标
trace_counter = Counter("langgraph_traces_total", "Total traces", ["status", "project"])
trace_duration = Histogram("langgraph_trace_duration_seconds", "Trace duration", ["project"])
token_gauge = Counter("langgraph_tokens_total", "Tokens consumed", ["type", "model"])

def track_metrics():
    client = Client(api_key=os.getenv("LANGCHAIN_API_KEY"))
    runs = client.list_runs(
        project_name="PredictionAgent-Prod",
        filter='gte(start_time, now() - duration("1m"))',
    )
    for run in runs:
        trace_counter.labels(status="success" if run.error is None else "error", project="PredictionAgent").inc()
        if run.duration_ms:
            trace_duration.labels(project="PredictionAgent").observe(run.duration_ms / 1000)

# 定时拉取统计到 Prometheus
import threading
def start_metrics_loop(interval=60):
    def loop():
        while True:
            track_metrics()
            threading.Event().wait(interval)
    threading.Thread(target=loop, daemon=True).start()
```

---

## 9. 常见问题

### Q1: LangSmith 免费额度是多少？

| 套餐 | 价格 | 额度 |
|------|------|------|
| Free | 免费 | 每月 5,000 条 trace |
| Team | $39/月 | 每月 50,000 条 trace |
| Enterprise | 定制 | 无限制 |

### Q2: 网络不通，无法上传 trace？

```bash
# 设置代理
export HTTPS_PROXY=http://127.0.0.1:7890

# 或者使用国内镜像（如果有的话）
export LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
```

### Q3: trace 里显示的是 node 函数名，如何改成中文？

```python
config = RunnableConfig(
    run_name="【销量预测】完整流程",
)

# 或者在每个节点里返回时带上
return {
    "prediction_state": {...},
    "_run_name": "产品识别",
}
```

### Q4: 如何删除已上传的 trace？

```python
client = Client(api_key="lsv2_pt_xxxx")

# 删除指定 trace
client.delete_run(run_id="xxxxxxxx-xxxx-xxxx")

# 删除整个项目的所有 trace
# （谨慎操作，不可恢复）
client.delete_project(project_name="PredictionAgent-Dev")
```

### Q5: trace 里有大文件（如图表）会占用大量存储？

默认 trace 会记录输入输出 JSON。如果数据量大：

```python
# 方式1：配置最大存储大小
os.environ["LANGCHAIN_MAX_CHAT_HISTORY_SIZE"] = "1000"  # 最大保留条数

# 方式2：大字段不记录
def analysis_node(state):
    # 只记录摘要，不记录完整数据
    return {
        "analysis_result": "...",
        "_trace_note": f"完整数据 {len(state.get('historical_data', []))} 条已省略",
    }
```

---

*文档基于 LangSmith API，生成时间：2026-06-25*
