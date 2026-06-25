# LangGraph 是如何实现 OpenTelemetry 可观测的

---

## 目录

1. [核心原理：LangGraph 与 LangChain 的关系](#1-核心原理langgraph-与-langchain-的关系)
2. [三层 Span 结构](#2-三层-span-结构)
3. [方式一：LangSmith 原生 OTEL Fanout](#3-方式一langsmith-原生-otel-fanout)
4. [方式二：OpenInference 自动插桩](#4-方式二openinference-自动插桩)
5. [方式三：原生 OTel SDK 手动插桩](#5-方式三原生-otel-sdk-手动插桩)
6. [关键问题：跨异步边界的 Context 传播](#6-关键问题跨异步边界的-context-传播)
7. [给 PredictionAgent-LangGraph 接入 OTEL](#7-给-predictionagent-langgraph-接入-otel)
8. [常见后端接入（OTLP Exporter）](#8-常见后端接入otlp-exporter)
9. [OpenInference GenAI 语义约定](#9-openinference-genai-语义约定)

---

## 1. 核心原理：LangGraph 与 LangChain 的关系

理解 LangGraph 的 OTEL 实现，先要搞清楚它们的层次关系：

```
┌─────────────────────────────────────────┐
│  LangGraph (StateGraph, nodes, edges)    │  ← 你的业务代码
├─────────────────────────────────────────┤
│  langgraph-core (Pregel 调度器)           │  ← 执行引擎
├─────────────────────────────────────────┤
│  langchain-core (Runnable 协议)           │  ← 统一接口层
├─────────────────────────────────────────┤
│  LangChain 回调机制 (Callback)            │  ← 事件通知层
└─────────────────────────────────────────┘
        ↑
        │  LangChainInstrumentor 监听回调
        ▼
┌─────────────────────────────────────────┐
│  OpenTelemetry SDK                       │  ← span/trace 管理
├─────────────────────────────────────────┤
│  OTLP Exporter                          │  ← 数据导出
└─────────────────────────────────────────┘
```

LangGraph 底层复用了 LangChain 的 **Runnable 协议**和**回调机制**。这意味着：

- LangGraph 执行节点时，会触发 LangChain 的回调事件
- `LangChainInstrumentor`（OpenInference 提供）监听了这些回调，自动创建 span
- LLM 调用（如 OpenAI / DeepSeek SDK）也有自己的 instrumentor，创建 LLM 子 span

---

## 2. 三层 Span 结构

一条完整的 LangGraph trace，在 OTEL 里呈现为三层嵌套的 span：

```
Trace: prediction-agent-run (root span)
│
├── Span: LangGraph Node product_identification
│   ├── Span: chat/completion (LLM 调用)
│   └── Span: <DB query> (如果有数据库操作)
│
├── Span: LangGraph Node data_fetch
│   ├── Span: chat/completion (如果有 LLM)
│   └── Span: <DB query>
│
├── Span: LangGraph Node chart_generation
│   └── (matplotlib 绘图)
│
└── Span: LangGraph Node analysis
    └── Span: chat/completion (LLM 分析)
```

每一层 span 都带有标准 OTEL 属性：

| 层级 | Span 名称 | 关键属性 |
|------|----------|---------|
| Root | `agent.run` | `service.name`, `thread_id` |
| Node | `LangGraph Node <node_name>` | `gen_ai.langgraph.node`, `gen_ai.langgraph.step` |
| LLM | `chat/completion` | `gen_ai.*` (OpenInference 语义约定) |

---

## 3. 方式一：LangSmith 原生 OTEL Fanout

LangSmith 本身就是一个 OTLP 接收端，同时支持把数据二次转发到其他 OTEL 后端。

### 3.1 基础配置

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=lsv2_pt_xxxxxxxx
export LANGCHAIN_PROJECT=PredictionAgent

# 开启 OTEL 转发（LanSmith 会把 trace 同时发到配置的 OTEL_ENDPOINT）
export LANGSMITH_OTEL_ENABLED=true
export LANGSMITH_OTEL_ONLY=false  # true = 只发 OTEL，不存 LangSmith
```

### 3.2 混合追踪架构

```
你的应用
  │
  ├── LANGCHAIN_TRACING_V2=true
  │     │
  │     ▼
  │   LangSmith (存 trace + 可视化)
  │
  └── LANGSMITH_OTEL_ENABLED=true
        │
        ▼
  OpenTelemetry Collector (OTLP Receiver)
        │
        ├──► Grafana Tempo (trace 存储)
        ├──► Datadog / Honeycomb (APM)
        └──► Prometheus (metrics)
```

LangSmith 会把同一个 trace 的 `parentSpanId` 保持住，所以：
- 在 LangSmith Dashboard 里看到完整的时间线和状态变化
- 在 Grafana Tempo / Datadog 里看到同样的 trace 层级结构

### 3.3 代码中开启 Fanout

```python
import os

os.environ["LANGSMITH_OTEL_ENABLED"] = "true"
os.environ["LANGSMITH_OTEL_ONLY"] = "false"

# 直接运行，无需改代码
from src.agent import PredictionAgent
agent = PredictionAgent()
agent.analyze(query="分析 iPhone 销量")
```

---

## 4. 方式二：OpenInference 自动插桩

OpenInference 是 Arize 推出的 **GenAI 语义约定层**，通过监听 LangChain 回调自动创建 span，无需手动改节点代码。

### 4.1 安装依赖

```bash
pip install \
    opentelemetry-sdk \
    opentelemetry-api \
    opentelemetry-exporter-otlp \
    opentelemetry-instrumentation-langchain \
    openinference-instrumentation-langchain \
    opentelemetry-instrumentation-openai \
    opentelemetry-instrumentation-dbapi  # 数据库调用
```

### 4.2 初始化插桩（在应用入口）

```python
# otel_setup.py
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.semconv.resource import ResourceAttributes

from openinference.instrumentation.langchain import LangChainInstrumentor
from opentelemetry.instrumentation.openai import OpenAIInstrumentor
from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor

def setup_otel(service_name: str = "prediction-agent", otlp_endpoint: str = "http://localhost:4317"):
    """初始化 OpenTelemetry，设置 OTLP exporter 并注册 instrumentors。"""

    # 1. 创建 TracerProvider
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: service_name,
        ResourceAttributes.SERVICE_VERSION: "1.0.0",
    })
    tracer_provider = TracerProvider(resource=resource)

    # 2. 添加 OTLP Exporter（发送到 collector）
    otlp_exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        insecure=True,  # gRPC 默认用 TLS，生产环境设为 True
    )
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # 3. 注册 TracerProvider
    from opentelemetry import trace
    trace.set_tracer_provider(tracer_provider)

    # 4. 注册 instrumentors（自动给 LangChain/LangGraph/OpenAI 插桩）
    LangChainInstrumentor().instrument()          # LangGraph 节点 span
    OpenAIInstrumentor().instrument()            # OpenAI/DeepSeek LLM span
    AsyncioInstrumentor().instrument()           # async 函数 span

    return tracer_provider


# ── 应用入口 (main.py 或 app.py) ──
if __name__ == "__main__":
    from otel_setup import setup_otel

    # 必须在创建 LangGraph app 之前初始化！
    setup_otel(
        service_name="prediction-agent",
        otlp_endpoint="http://localhost:4317",  # OTEL Collector 地址
    )

    # 从这里开始，所有 LangGraph 节点执行都会自动创建 span
    from src.agent import PredictionAgent
    agent = PredictionAgent()
    result = agent.analyze(query="分析 iPhone 销量")
```

### 4.3 关键点：初始化顺序

```
1. setup_otel()           ← 必须在最前面
2. LangChainInstrumentor() ← 注册回调监听
3. OpenAIInstrumentor()   ← 注册 LLM span
4. PredictionAgent()       ← 创建 app
5. app.invoke()           ← 开始执行，自动创建 span
```

如果顺序反了（先创建 app，再初始化 instrumentor），LangGraph 已经调度完了，回调事件已经错过，span 就不会被创建。

---

## 5. 方式三：原生 OTel SDK 手动插桩

OpenInference 只能处理 LangChain 回调里有的事件。如果你想追踪 LangGraph **内部调度细节**（如条件边路由决策），或者不想用 OpenInference，就需要手动用原生 OTel SDK 创建 span。

### 5.1 手动 wrap 节点函数

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer("prediction-agent")

def traced_node(node_fn):
    """给节点函数包一层，自动创建 node span。"""
    node_name = getattr(node_fn, "__name__", "unknown")

    def wrapper(state: dict) -> dict:
        with tracer.start_as_current_span(
            f"LangGraph Node {node_name}",
            kind=trace.SpanKind.INTERNAL,
        ) as span:
            span.set_attribute("gen_ai.langgraph.node", node_name)
            span.set_attribute("gen_ai.langgraph.thread_id",
                               state.get("_thread_id", ""))
            try:
                result = node_fn(state)
                span.set_attribute("gen_ai.langgraph.step",
                                   result.get("prediction_state", {}).get("step", ""))
                return result
            except Exception as exc:
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.record_exception(exc)
                raise
    return wrapper


# 在 builder 里 wrap 每个节点
builder.add_node("product_identification",
                 traced_node(product_identification_node))
builder.add_node("data_fetch",
                 traced_node(data_fetch_node))
builder.add_node("chart_generation",
                 traced_node(chart_node))
builder.add_node("analysis",
                 traced_node(analysis_node))
```

### 5.2 追踪条件边路由

条件边的路由决策也是可观测的重要部分：

```python
from opentelemetry import trace

tracer = trace.get_tracer("prediction-agent")

def traced_routing_decision(routing_fn):
    """给路由函数包一层，记录路由决策。"""
    def wrapper(state: dict) -> str:
        with tracer.start_as_current_span(
            "LangGraph Conditional Edge",
            kind=trace.SpanKind.INTERNAL,
        ) as span:
            current_step = state.get("prediction_state", {}).get("step", "unknown")
            reflection = state.get("reflection", {})
            is_valid = reflection.get("current_validation", {}).get("is_valid", True)

            span.set_attribute("gen_ai.langgraph.current_step", current_step)
            span.set_attribute("gen_ai.langgraph.validation_passed", is_valid)
            span.set_attribute("gen_ai.langgraph.reflection_count",
                               reflection.get("reflection_count", 0))

            result = wrapper(state)
            span.set_attribute("gen_ai.langgraph.next_node", result)
            return result
    return wrapper
```

---

## 6. 关键问题：跨异步边界的 Context 传播

这是 LangGraph OTEL 追踪中最容易出错的地方。

### 6.1 问题描述

LangGraph 内部用 `asyncio` 调度节点。**OTEL 的上下文传播依赖 `contextvars.ContextVar`**，但在异步调度时，每个节点可能在不同的协程/线程里执行：

```
主协程
  │
  └── app.invoke() ──► 创建 root span
       │
       │  (LangGraph 内部 asyncio 调度)
       │
       ├──► 节点A 在协程1执行 ──► 继承了 root span 的 context？  ← 有时丢失
       │
       ├──► 节点B 在协程2执行 ──► 可能是新的 root span？        ← 孤儿 span
       │
       └──► 条件边在协程3执行 ──► context 再次丢失               ← 链路断裂
```

### 6.2 解决方案：用状态传递 OTel Context

把活跃的 OTel context 存入 AgentState，每个节点执行时重新激活：

```python
from opentelemetry import trace
from opentelemetry.context import attach, get_current

# 在 app.invoke 之前创建 root span
tracer = trace.get_tracer("prediction-agent")

def invoke_with_root_span(app, initial_state, config):
    with tracer.start_as_current_span("prediction-agent.run") as root_span:
        # 把 root span 的 context 注入到状态里
        initial_state["__otel_ctx__"] = get_current()
        root_span.set_attribute("gen_ai.langgraph.thread_id",
                                config["configurable"]["thread_id"])

        # 每次调用 app.get_state 时重新激活 context
        final_state = app.invoke(initial_state, config)
        return final_state

# 在节点里激活 context
def product_identification(state):
    # 从状态里取出上次保存的 context
    ctx = state.get("__otel_ctx__")
    if ctx:
        token = attach(ctx)  # 激活 context，后续 span 自动成为 root 的子 span
    try:
        result = _do_identification(state)
        # 把当前 context 写回状态，供下一个节点使用
        result["__otel_ctx__"] = get_current()
        return result
    finally:
        if ctx:
            detach(token)
```

这样做之后，即使节点在不同的协程里执行，span 链路也不会断裂：

```
root span (agent.run)
  │
  ├── node span (product_identification)    ← 正确父子
  │     └── LLM span                        ← 正确祖孙
  │
  ├── node span (data_fetch)                ← 正确父子
  │     └── DB span                         ← 正确祖孙
  │
  └── node span (analysis)                  ← 正确父子
        └── LLM span                        ← 正确祖孙
```

### 6.3 用 `@opentelemetry/instrument` 自动处理（最简单）

Python 的 `opentelemetry-instrument` 命令行工具可以在运行时自动 patch 异步函数，解决 context 传播问题：

```bash
# 安装
pip install opentelemetry-instrumentation-asyncio

# 用 instrument 命令启动，自动处理所有 async 函数的 context
opentelemetry-instrument \
    --service-name prediction-agent \
    python examples/basic_usage.py
```

加上 `--traces-exporter otlp` 参数，instrument 会自动设置 OTLP exporter，无需在代码里写 exporter 配置：

```bash
opentelemetry-instrument \
    --service-name prediction-agent \
    --traces-exporter otlp \
    --otlp-endpoint http://localhost:4317 \
    python examples/basic_usage.py
```

---

## 7. 给 PredictionAgent-LangGraph 接入 OTEL

把上面的方案整合，给你的项目加上 OTEL 支持。

### 7.1 完整接入代码

创建 `src/telemetry/otel_setup.py`：

```python
"""
OpenTelemetry 初始化模块

使用方法：
    from src.telemetry.otel_setup import setup_otel
    setup_otel(service_name="prediction-agent")
"""
import os
from typing import Optional

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes


def setup_otel(
    service_name: str = "prediction-agent",
    otlp_endpoint: Optional[str] = None,
    langsmith_enabled: bool = False,
) -> None:
    """
    初始化 OpenTelemetry 并注册 instrumentors。

    Args:
        service_name: 服务名称，会显示在 trace 里
        otlp_endpoint: OTLP Collector 地址，如 "http://localhost:4317"
        langsmith_enabled: 是否同时开启 LangSmith（需要 LANGCHAIN_API_KEY）
    """
    # 1. LangSmith（可选）
    if langsmith_enabled:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGSMITH_OTEL_ENABLED"] = "true"
        os.environ.setdefault("LANGCHAIN_PROJECT", "PredictionAgent")

    # 2. OTLP Exporter（如果提供了 endpoint）
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                insecure=True,
            )
            add_exporter(otlp_exporter, service_name)
        except ImportError:
            print("⚠️ opentelemetry-exporter-otlp 未安装，跳过 OTLP 导出")

    # 3. 注册 instrumentors
    _register_instrumentors()


def add_exporter(exporter, service_name: str) -> None:
    """把 exporter 注册到全局 TracerProvider。"""
    from opentelemetry import trace

    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: service_name,
    })
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(tracer_provider)


def _register_instrumentors() -> None:
    """注册所有 instrumentors。"""
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor
        LangChainInstrumentor().instrument()
        print("✓ LangChainInstrumentor 已注册（LangGraph 节点 span）")
    except ImportError:
        print("⚠️ openinference-instrumentation-langchain 未安装，跳过")

    try:
        from opentelemetry.instrumentation.openai import OpenAIInstrumentor
        OpenAIInstrumentor().instrument()
        print("✓ OpenAIInstrumentor 已注册（LLM 调用 span）")
    except ImportError:
        print("⚠️ opentelemetry-instrumentation-openai 未安装，跳过")

    try:
        from opentelemetry.instrumentation.asyncio import AsyncioInstrumentor
        AsyncioInstrumentor().instrument()
        print("✓ AsyncioInstrumentor 已注册（异步 context 传播）")
    except ImportError:
        print("⚠️ opentelemetry-instrumentation-asyncio 未安装，跳过")


def get_tracer(name: str = "prediction-agent"):
    """获取一个 Tracer 实例，用于手动创建 span。"""
    from opentelemetry import trace
    return trace.get_tracer(name)
```

### 7.2 在应用中启用

```python
# examples/basic_usage.py
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# === OTEL 初始化必须在创建 app 之前 ===
from src.telemetry.otel_setup import setup_otel

setup_otel(
    service_name="prediction-agent",
    otlp_endpoint=os.getenv("OTLP_ENDPOINT"),  # "http://localhost:4317"
    langsmith_enabled=bool(os.getenv("LANGCHAIN_API_KEY")),
)
# ==========================================

from src.agent import PredictionAgent

agent = PredictionAgent()
result = agent.analyze(
    query="分析 iPhone 15 Pro 的销量",
    thread_id="otel-demo-001",
)
```

### 7.3 用环境变量控制

```bash
# 只用 LangSmith
export LANGCHAIN_API_KEY=lsv2_pt_xxxx
export LANGCHAIN_TRACING_V2=true

# 只用 OTEL（如 Grafana Tempo）
export OTLP_ENDPOINT=http://localhost:4317

# 两者同时用（fanout）
export LANGCHAIN_API_KEY=lsv2_pt_xxxx
export OTLP_ENDPOINT=http://localhost:4317

python examples/basic_usage.py
```

---

## 8. 常见后端接入（OTLP Exporter）

只需要改 OTLP endpoint，就能换不同的后端：

```python
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Grafana Tempo
OTLPSpanExporter(endpoint="http://tempo:4317")

# Datadog（DD_API_KEY 通过环境变量传递）
# 不用 OTLPSpanExporter，用 DatadogSpanExporter
from ddtrace import patch
patch(opentelemetry=True)

# Jaeger（HTTP 协议）
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger",
    agent_port=6831,
)

# Zipkin
from opentelemetry.exporter.zipkin.proto.http import ZipkinExporter
zipkin_exporter = ZipkinExporter(
    endpoint="http://zipkin:9411/api/v2/spans",
)

# Phoenix (Arize 开源的可视化平台)
# 只需设置一个环境变量，不需要代码修改
export PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006

# 然后在代码里用 HTTP Exporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
OTLPSpanExporter(endpoint="http://localhost:6006/v1/traces")
```

---

## 9. OpenInference GenAI 语义约定

OpenInference 定义了一套标准 OTEL 属性，专门描述 GenAI 应用特有的数据（LLM token、model name、tool call 等）。主流后端（Grafana AI Observability、Datadog LLM Observability、Phoenix）都认这套约定。

### 9.1 核心属性

| 属性名 | 说明 | 示例 |
|-------|------|------|
| `gen_ai.system` | LLM 提供商 | `openai`, `deepseek`, `anthropic` |
| `gen_ai.operation.name` | 操作类型 | `chat`, `completion` |
| `gen_ai.request.model` | 模型名称 | `deepseek-chat`, `gpt-4o-mini` |
| `gen_ai.request.max_tokens` | 最大 token 数 | `4000` |
| `gen_ai.response.id` | 请求 ID | `gen-xxx` |
| `gen_ai.token.type` | token 类型 | `input`, `output` |
| `gen_ai.token.count` | token 数量 | `1250` |
| `gen_ai.usage.total_tokens` | 总 token 消耗 | `1500` |
| `gen_ai.langgraph.node` | 节点名称 | `product_identification` |
| `gen_ai.langgraph.step` | 当前步骤 | `analysis` |
| `gen_ai.tool.name` | 工具名称 | `plot_sales_forecast` |
| `gen_ai.tool.call.id` | 工具调用 ID | `call_xxx` |

### 9.2 手动写入 GenAI 属性

```python
from opentelemetry import trace

tracer = get_tracer()

def analysis_node(state: AgentState) -> dict:
    with tracer.start_as_current_span("analysis") as span:
        # 设置 LLM 相关属性
        span.set_attribute("gen_ai.system", "deepseek")
        span.set_attribute("gen_ai.request.model", "deepseek-chat")
        span.set_attribute("gen_ai.langgraph.node", "analysis")
        span.set_attribute("gen_ai.langgraph.thread_id",
                          state.get("_thread_id", ""))

        # 调用 LLM
        response = llm.invoke(...)

        # 设置输出属性
        span.set_attribute("gen_ai.response.id", response.id)
        span.set_attribute("gen_ai.usage.total_tokens",
                          response.usage.total_tokens)
        span.set_attribute("gen_ai.token.count",
                          {"type": "output", "count": response.usage.completion_tokens})

        return {...}
```

### 9.3 成本计算

有了 token 数量，可以算费用：

```python
def compute_cost(span: trace.Span) -> float:
    """根据 span 属性计算 LLM 调用费用（美元）。"""
    pricing = {
        "deepseek-chat": {"input": 0.27, "output": 1.10},  # $/M tokens
        "gpt-4o-mini":   {"input": 0.15, "output": 0.60},
    }
    model = span.attributes.get("gen_ai.request.model", "")
    usage = span.attributes.get("gen_ai.usage", {})

    rates = pricing.get(model, {"input": 0, "output": 0})
    input_cost = (usage.get("input_tokens", 0) / 1_000_000) * rates["input"]
    output_cost = (usage.get("output_tokens", 0) / 1_000_000) * rates["output"]

    return input_cost + output_cost
```

---

## 总结：三种接入方式对比

| 维度 | LangSmith Fanout | OpenInference | 手动 OTel SDK |
|------|-----------------|-------------|-------------|
| 接入工作量 | ⭐⭐（设置环境变量） | ⭐⭐⭐（安装 + 初始化） | ⭐⭐⭐⭐（每个节点 wrap） |
| 可视化 UI | ✅ 完整 Dashboard | ❌ 需接后端 | ❌ 需接后端 |
| 节点 span | ✅ 自动 | ✅ 自动 | 需要手动 |
| LLM span | ✅ 自动 | ✅ 自动 | 需要手动 |
| 条件边 span | ❌ 无 | ❌ 无 | ✅ 手动 |
| 跨后端 | ✅（fanout） | ✅（换 OTLP endpoint） | ✅（换 OTLP endpoint） |
| 适用场景 | 快速接入，优先用 LangSmith | 生产级，需要接 Grafana/Datadog | 自定义追踪需求 |

**推荐路径**：

1. 快速验证 → LangSmith Fanout（`LANGSMITH_OTEL_ENABLED=true`）
2. 接入 Grafana Tempo / Datadog → OpenInference + OTLP Exporter
3. 追踪条件边路由决策 → 手动 OTel SDK 补充

---

*文档基于 OpenTelemetry SDK 1.39+ / LangGraph 0.2+ / OpenInference，生成时间：2026-06-25*
