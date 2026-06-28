# trace-basic — OpenTelemetry 链路追踪（Trace）入门示例

## 模块概述

本模块展示了 OpenTelemetry Trace API 的完整用法，包括 **Span（跨度）的创建**、**父子关系**、**嵌套调用**、**错误记录**，以及多种导出方式（OTLP、Jaeger、Zipkin）。

这是一个**单进程**的示例，没有任何网络调用，非常适合理解链路追踪的核心概念。

---

## 为什么需要链路追踪（Trace）？

### 现实问题

假设你有如下微服务架构：

```
用户下单请求
    │
    ├─▶ API网关 (50ms)
    │       │
    │       ├─▶ 订单服务 (200ms)
    │       │       │
    │       │       ├─▶ 库存服务 (150ms)
    │       │       ├─▶ 支付服务 (300ms)
    │       │       └─▶ 积分服务 (100ms)
    │       │
    │       └─▶ 通知服务 (50ms)
```

某天用户投诉"下单失败"，你的日志里可能只有：

```
订单服务：[ERROR] 调用库存服务超时
库存服务：[ERROR] 连接池耗尽
```

但你不知道：
1. 这次请求从头到尾耗时多少？
2. 是不是支付服务更慢导致的？
3. 是哪台机器出的问题？
4. 如果库存服务是别的团队维护，你根本看不到他们的日志怎么办？

### 链路追踪的解决方案

给每一次请求分配一个唯一的 **Trace ID**，让这个 ID 跟着请求流经所有服务，最终串联成一条完整的调用链。

---

## 核心概念

### 1. Trace（追踪）

一次完整的请求，从开始到结束，所有 Span 串联起来的整体。

```
Trace ID: abc123
│
├── Span: main (入口)
│       │
│       ├── Span: Sum (计算)
│       │       └── 属性: a=1, b=2, c=3
│       │
│       └── Span: Product (乘法)
│               └── 属性: a=1, b=2, c=2
```

### 2. Span（跨度）

链路上的每一个操作节点，代表一次操作：

- Span 名称（如 `"Sum"`、`"mysql.query"`）
- 开始时间、结束时间 → 自动计算耗时
- 属性（输入参数、输出结果）
- 状态（成功 / 错误）
- 父 Span ID（形成树形关系）

### 3. Tracer（追踪器）

创建 Span 的工具。每个模块使用自己专属的 Tracer：

```go
mainTracer := otel.Tracer("main-tracer")   // main 包用
busTracer := otel.Tracer("bus-tracer")     // bus 包用
```

### 4. TracerProvider（追踪器提供者）

全局管理器，统一管理：
- 所有 Tracer 实例
- 导出器（数据发送给谁）
- 采样策略（采多少数据）
- 资源信息（服务标识）

---

## 初始化流程详解

### 第一步：创建 Resource（资源信息）

```go
res, err := resource.New(
	ctx,
	resource.WithOS(),           // 自动采集操作系统信息
	resource.WithHost(),         // 自动采集主机名、IP
	resource.WithAttributes(
		semconv.ServiceName("trace-basic"),
		semconv.ServiceVersion("1.0.0"),
		attribute.String("env", "dev"),
		attribute.String("author", "nick"),
	),
)
```

**为什么要这样做**：
- 每条追踪数据都带上"这是哪个服务、哪个版本、哪台机器"的信息
- 在 Jaeger UI 上可以按服务名、版本、环境筛选
- 否则所有服务的数据混在一起，无法区分

### 第二步：选择 Exporter（导出器）

```go
var traceExporter sdktrace.SpanExporter
if otlpGrpcEndpoint != "" {
	traceExporter, _ = otlptracegrpc.New(ctx, ...)
} else if otlpHttpEndpoint != "" {
	traceExporter, _ = otlptracehttp.New(ctx, ...)
} else if jaegerEndpoint != "" {
	traceExporter, _ = jaeger.New(jaeger.WithCollectorEndpoint(...))
} else if zipkinEndpoint != "" {
	traceExporter, _ = zipkin.New(zipkinEndpoint)
}
```

**为什么要这样做**：应用程序内存中的 Span 数据需要发送到某个地方（Jaeger / Zipkin / OTEL Collector），Exporter 负责这个发送工作。

| Exporter | 发送给 | 适用场景 |
|---|---|---|
| `otlptracegrpc` | OTEL Collector（gRPC） | 生产环境推荐 |
| `otlptracehttp` | OTEL Collector（HTTP） | 生产环境推荐 |
| `jaeger` | Jaeger 直接 | 快速验证 |
| `zipkin` | Zipkin 直接 | 快速验证 |

### 第三步：创建 TracerProvider

```go
tracerProvider := sdktrace.NewTracerProvider(
	sdktrace.WithSampler(sdktrace.AlwaysSample()),      // 100%采样
	sdktrace.WithResource(res),                        // 带上资源信息
	sdktrace.WithSpanProcessor(                        // 批量处理器
		sdktrace.NewBatchSpanProcessor(traceExporter),
	),
)
otel.SetTracerProvider(tracerProvider)
```

**为什么要这样做**：

1. **`WithSampler(AlwaysSample())`**：开发环境全采样（100%），确保每次请求都被追踪。生产环境通常用 `ParentBased`，即"有父Span则采，无父Span则不采"，避免流量大时数据爆炸。

2. **`WithSpanProcessor`**：Span 处理器。这里用 `BatchSpanProcessor` 批量发送，而不是每产生一个就发一次，减少网络 IO。

3. **`otel.SetTracerProvider`**：设为全局单例，这样后续 `otel.Tracer("name")` 才能工作。

---

## Span 的生命周期

```go
func (bus *bus) Sum(ctx context.Context, a, b int) int {
	// ① 创建 Span，ctx 中携带父 Span 信息
	_, span := bus.tracer.Start(ctx, "sum",
		trace.WithAttributes(
			attribute.Int("a", a),
			attribute.Int("b", b),
		),
	)
	defer span.End()   // ② 确保退出时关闭

	// ③ 执行业务逻辑
	c := a + b
	time.Sleep(time.Millisecond * 100)

	// ④ 记录结果
	span.SetAttributes(attribute.Int("c", c))

	return c
}
```

**为什么必须 defer span.End()**：
- Span 创建后，如果不调用 `End()`，则结束时间永远是 `time.Time{}`（即 1970年），永远不会被导出
- `defer` 确保即使业务逻辑panic，Span 也会被正确关闭

---

## 父子 Span 关系

### 为什么需要父子关系？

想象两个并发请求同时到来：

```
请求A: main → sum → product
请求B: main → sum → product
```

如果 Span 没有父子关系，所有 Span 都是扁平的，就无法区分哪些属于请求A、哪些属于请求B。

### 父子关系的形成

**自动形成**：通过 `ctx` 传递。

```go
// main 函数中
ctx, span := mainTracer.Start(ctx, "main", ...)  // 创建根 Span

// 调用 bus 时，ctx 带着父 Span 信息
busTracer := otel.Tracer("bus-tracer")
c := b.Sum(ctx, 1, 2)  // ctx 中有父 Span ID

// 在 bus 中创建子 Span
_, span := bus.tracer.Start(ctx, "sum", ...)  // 自动关联到父 Span
```

**不需要手动指定父 Span**，只需要：
1. 父 Span 创建时用 `tracer.Start(ctx, ...)` 获得新的 `ctx`（包含父 Span 信息）
2. 子 Span 创建时传入这个 `ctx`，SDK 自动识别父子关系

---

## 错误处理

```go
span.RecordError(errors.New("这里报错了"))
span.SetStatus(codes.Error, "main函数异常")
```

**为什么要这样做**：
- Jaeger UI 上，红色标记表示出错的 Span，一眼就能看到问题所在
- 错误信息会被记录到 Span 的 `events` 中
- `SetStatus` 设置 Span 状态，便于筛选失败的请求

---

## 四种 Exporter 对比

### 方式一：OTLP（推荐生产环境）

```go
traceExporter, _ = otlptracegrpc.New(ctx,
	otlptracegrpc.WithGRPCConn(conn),
)
```

**为什么推荐**：
- OTLP 是 OpenTelemetry 的标准协议
- Collector 可以统一处理多协议（OTLP、Jaeger、Zipkin）
- 支持 Trace、Metric、Log 三种数据
- 方便后续扩展到 Prometheus、Grafana 等后端

### 方式二：Jaeger

```go
traceExporter, _ = jaeger.New(
	jaeger.WithCollectorEndpoint(jaeger.WithEndpoint(jaegerEndpoint)),
)
```

**适用场景**：
- 快速验证，不需要额外部署 OTEL Collector
- 已有 Jaeger 环境

### 方式三：Zipkin

```go
traceExporter, _ = zipkin.New(zipkinEndpoint)
```

**适用场景**：
- 迁移项目，已有 Zipkin 环境
- Zipkin 生态（如 Apache SkyWalking 兼容 Zipkin 协议）

### 为什么不直接发送到 Jaeger/Zipkin？

```
应用 → OTEL Collector → Jaeger/Zipkin/Prometheus
              ↑
         统一中间层
         - 批量处理
         - 采样
         - 协议转换
         - 负载均衡
```

OTEL Collector 作为中间层，接收多种协议、批量处理、统一转发，比每个应用直接连 Jaeger 更高效。

---

## BatchSpanProcessor 的作用

```go
sdktrace.WithSpanProcessor(
	sdktrace.NewBatchSpanProcessor(traceExporter),
)
```

**问题**：如果每产生一个 Span 就发送一次，会造成大量网络请求。

**解决**：先在内存中攒够一批（默认 2048 个），批量发送。

```
Without Batch:  1 Span = 1 网络请求 ❌ 10000 Span/秒 = 10000 请求/秒
With Batch:    2048 Span = 1 网络请求 ✅ 10000 Span/秒 = ~5 请求/秒
```

---

## 快速运行

```bash
cd trace-basic

# 方式1：通过 OTEL Collector（推荐）
go run main.go --otlp-grpc=192.168.239.154:5317

# 方式2：直接发送到 Jaeger
go run main.go --jaeger=http://192.168.239.154:14268/api/traces

# 方式3：直接发送到 Zipkin
go run main.go --zipkin=http://192.168.239.154:9411/api/v2/spans
```

---

## 总结

```
┌─────────────────────────────────────────────────────────────────┐
│                    链路追踪的核心知识点                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Trace = 一次请求的所有 Span 的集合                               │
│  Span  = 链路上的每个操作节点                                    │
│                                                                  │
│  初始化顺序:                                                    │
│  Resource → Exporter → TracerProvider → SetTracerProvider       │
│                                                                  │
│  Span 生命周期:                                                 │
│  Start(ctx, name) → 业务逻辑 → SetAttributes → RecordError      │
│       ↓                                                          │
│  defer End()  (必须调用，否则 Span 永不结束)                      │
│                                                                  │
│  父子关系: 通过 ctx 自动传递，不需要手动指定                       │
│                                                                  │
│  Exporters:                                                     │
│  ┌──────────────┬────────────────────────────────┐           │
│  │ OTLP          │ 生产环境推荐，统一中间层         │           │
│  │ Jaeger        │ 快速验证，不需要 Collector      │           │
│  │ Zipkin        │ 兼容已有 Zipkin 环境            │           │
│  └──────────────┴────────────────────────────────┘           │
│                                                                  │
│  BatchSpanProcessor: 批量发送，减少网络 IO                        │
│  defer shutdown(ctx): 程序退出前导出剩余数据                      │
└─────────────────────────────────────────────────────────────────┘
```
