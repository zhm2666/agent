# OpenTelemetry Python Demo - Distributed Tracing

这是一个参考 [opentelemetry-go](https://github.com/open-telemetry/opentelemetry-go) 实现的 Python 版本分布式链路追踪示例项目。

## 项目结构

```
otel-python-demo/
├── proto/                    # Protocol Buffer 定义
│   ├── strsvc.proto          # 字符串服务接口
│   └── addsvc.proto          # 加法服务接口
├── trace_basic/              # 链路追踪入门示例
│   ├── main.py              # 演示如何创建 Spans
│   └── bus.py               # 业务逻辑（带追踪）
├── metric_basic/            # 指标监控示例
│   └── main.py              # Counter/Gauge/Histogram
├── strsvc/                   # 字符串服务（下游服务）
│   ├── bus.py               # 业务逻辑
│   ├── middleware.py         # 追踪/指标中间件
│   ├── server.py            # gRPC 服务端
│   └── client.py            # 客户端测试
├── addsvc/                   # 加法服务（上游编排服务）
│   ├── bus.py               # 业务逻辑
│   ├── middleware.py         # 中间件
│   ├── server.py            # gRPC 服务端（调用 strsvc）
│   └── client.py            # 客户端测试
├── otel_utils.py            # OpenTelemetry 初始化工具
└── requirements.txt         # Python 依赖
```

## 核心概念对照

| Go 实现 | Python 实现 |
|---------|-------------|
| `TracerProvider` | `TracerProvider` |
| `Tracer.Start(ctx, name)` | `tracer.start_as_current_span(name)` 或 `tracer.start_span(name)` |
| `span.End()` | `with` 语句自动结束 |
| `span.SetAttributes()` | `span.set_attribute()` |
| `span.AddEvent()` | `span.add_event()` |
| `BatchSpanProcessor` | `BatchSpanProcessor` |
| `otel.SetTracerProvider()` | `trace.set_tracer_provider()` |
| `otel.GetTracer()` | `trace.get_tracer()` |
| `Propagators` | `Propagators` (TraceContext, Baggage) |
| `MeterProvider` | `MeterProvider` |
| `Counter/Histogram/ObservableGauge` | 同名实现 |

## 快速开始

### 1. 安装依赖

```bash
cd otel-python-demo
pip install -r requirements.txt
```

### 2. 生成 gRPC 代码

```bash
# 安装 grpcio-tools 后，运行:
python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./strsvc \
    --grpc_python_out=./strsvc \
    ./proto/strsvc.proto

python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./addsvc \
    --grpc_python_out=./addsvc \
    ./proto/addsvc.proto
```

或者使用项目提供的脚本:

```bash
python generate_proto.py
```

### 3. 启动 OTEL Collector

使用 Go 版本的 collector 配置:

```bash
# 在 opentelemetry-master 目录下
otelcol --config otel-collector-config.yaml
```

或使用 Docker:

```bash
docker run -p 4317:4317 -p 4318:4318 \
    -v $(pwd)/otel-collector-config.yaml:/etc/otelcol/config.yaml \
    otel/opentelemetry-collector:latest
```

### 4. 运行示例

#### 4.1 基础追踪示例

```bash
OTLP_ENDPOINT=http://localhost:4317 python trace_basic/main.py
```

#### 4.2 指标示例

```bash
OTLP_ENDPOINT=http://localhost:4317 python metric_basic/main.py
```

#### 4.3 启动服务

```bash
# 终端 1: 启动 strsvc (下游服务)
python strsvc/server.py

# 终端 2: 启动 addsvc (上游编排服务)
STRVCP_ADDRESS=localhost:50052 python addsvc/server.py

# 终端 3: 测试客户端
python addsvc/client.py
```

## 架构说明

### 服务调用链

```
addsvc-cli → addsvc (:50051)
                │
                ├─ bus.Sum/Concat (本地业务)
                │
                └─ strsvc.Count/Uppercase (:50052) → strsvc
```

### 追踪上下文传播

1. **上游 (addsvc)**:
   - 创建父 Span
   - 使用 `inject()` 将 trace context 注入到 gRPC metadata
   - 可选: 添加 Baggage 到 context

2. **下游 (strsvc)**:
   - 从 gRPC metadata 使用 `extract()` 提取 trace context
   - 创建子 Span，自动关联到父 Span
   - 从 Baggage 读取上游传递的自定义数据

### 中间件模式

```python
# 装饰器模式：业务逻辑与可观测性分离
raw_bus = AddBus(tracer)
traced_bus = TraceMiddleware(raw_bus, tracer)
metricked_bus = MetricMiddleware(traced_bus, meter)
```

等价于 Go 版本:

```go
bus := TracerMiddleware(metricBus, tracer)
```

## 主要代码示例

### 创建 Span

```python
from otel_utils import get_tracer

tracer = get_tracer("my-module")

# 方式 1: 使用 with 语句（推荐）
with tracer.start_as_current_span("operation-name") as span:
    span.set_attribute("key", "value")
    span.add_event("Processing started")
    # 业务逻辑
    result = do_work()
    span.set_attribute("result", result)

# 方式 2: 手动管理生命周期
span = tracer.start_span("operation-name")
try:
    # ...
finally:
    span.end()
```

### 分布式追踪传播

```python
from opentelemetry.propagate import inject, extract

# 服务端: 注入 trace context
metadata = []
carrier = {}
inject(carrier)  # 注入 W3C TraceContext
for key, value in carrier.items():
    metadata.append((key, value))

# 调用下游服务
response = stub.MyMethod(request, metadata=metadata)

# 客户端: 提取 trace context
metadata = dict(context.invocation_metadata())
carrier = {k: v for k, v in metadata.items()}
ctx = extract(carrier)

# 创建子 span
ctx, span = tracer.start_span("handler", context=ctx)
```

### 指标记录

```python
from otel_utils import get_meter

meter = get_meter("my-module")

# Counter
counter = meter.create_counter("requests_total")
counter.add(1, {"endpoint": "/api/users"})

# Histogram
histogram = meter.create_histogram("request_duration")
histogram.record(0.234, {"endpoint": "/api/users"})

# ObservableGauge
gauge = meter.create_observable_gauge(
    name="queue_depth",
    callbacks=[lambda options: [metrics.Observation(current_queue_depth())]]
)
```

## 配置选项

通过环境变量配置:

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `OTLP_ENDPOINT` | `http://localhost:4317` | OTLP 收集器地址 |
| `STRVCP_PORT` | `50052` | strsvc 服务端口 |
| `STRVCP_ADDRESS` | `localhost:50052` | strsvc 服务地址 |
| `ADDSVC_PORT` | `50051` | addsvc 服务端口 |
| `ADDSVC_ADDRESS` | `localhost:50051` | addsvc 服务地址 |

## 查看追踪结果

1. **Jaeger UI**: http://localhost:16686
2. **OTEL Collector Prometheus**: http://localhost:8889/metrics
3. **Zipkin**: http://localhost:9411

## 与 Go 版本对比

| 特性 | Go | Python |
|------|-----|--------|
| 初始化 | 显式创建 Provider | 同左 |
| Span 创建 | `tracer.Start(ctx, name)` | `tracer.start_as_current_span(name)` |
| Span 结束 | `defer span.End()` | `with` 语句自动 |
| Context 传递 | 通过 ctx 参数 | 通过 ctx 参数 |
| 中间件 | 函数式装饰器 | 类装饰器 |
| 批量处理 | `BatchSpanProcessor` | 同左 |
| gRPC 集成 | grpc.UnaryInterceptor | grpcio interceptors |

## 依赖说明

```
# Core OpenTelemetry
opentelemetry-api>=1.22.0
opentelemetry-sdk>=1.22.0

# Exporters
opentelemetry-exporter-otlp>=1.22.0

# gRPC
grpcio>=1.60.0
grpcio-tools>=1.60.0
protobuf>=4.25.0
```

## License

MIT
