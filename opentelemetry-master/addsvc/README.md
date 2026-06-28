# addsvc — 加法服务（gRPC + 分布式链路追踪 + 指标监控）

## 模块概述

本模块是整个项目中最复杂的示例，展示了一个**生产级的微服务**如何集成：
- **gRPC 通信**：服务间调用
- **分布式链路追踪**：跨服务的 Trace 上下文传递
- **Propagator**：TraceContext + Baggage 传播
- **装饰器模式**：追踪中间件 + 指标中间件
- **双重导出**：同时导出 Traces 和 Metrics

---

## 服务架构

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            addsvc 模块架构                                 │
│                                                                          │
│  addsvc-cli (客户端)                                                      │
│       │                                                                  │
│       │ gRPC 调用 Sum(a, b)                                              │
│       │ gRPC 调用 Concat(a, b)                                           │
│       ▼                                                                  │
│  addsvc-server (:50051) ───────────────────────────────────────────┐     │
│       │                                                      │     │     │
│       │ gRPC 调用 Count(str)                                   │     │     │
│       │ gRPC 调用 Uppercase(str)                                │     │     │
│       └────────────────────────────────────────────────────────┘     │     │
│                                                                     │     │
│                                                                     ▼     │
│  strsvc-server (:50052) ← (作为独立进程运行在 addsvc 模块中)              │
│       (这个服务的代码在 strsvc 模块，这里只是引用它的 proto)               │
│                                                                          │
│       共享 OTEL Collector (192.168.239.154:5317)                         │
└──────────────────────────────────────────────────────────────────────────┘
```

### Proto 定义

```protobuf
service Add {
  rpc Sum (SumRequest) returns (SumReply)       // a + b，返回 int64
  rpc Concat (ConcatRequest) returns (ConcatReply) // 字符串拼接
}

message SumRequest { int64 a = 1; int64 b = 2; }
message SumReply { int64 v = 1; }

message ConcatRequest { string a = 1; string b = 2; }
message ConcatReply { string v = 1; }
```

---

## 核心设计：装饰器模式

### 为什么需要装饰器模式？

**问题 1**：在业务代码（如 `bus.go`）中直接写追踪代码，会污染业务逻辑。

```go
// ❌ 不好的做法：业务代码和追踪代码混在一起
func (bus *bus) Sum(a, b int) int {
	span := tracer.Start("Sum")        // 追踪代码
	defer span.End()
	result := a + b                    // 业务代码
	span.SetAttribute("result", result) // 追踪代码
	return result
}
```

缺点：
- 业务代码必须依赖 OpenTelemetry 包
- 无法单独测试业务逻辑
- 想加/删追踪功能需要改所有业务函数

**问题 2**：追踪和指标是两套不同的功能，需要分开管理。

### 解决方案：装饰器链

将业务代码层层包裹，追踪和指标作为"外层"存在：

```
调用方
    │
    ▼
┌─────────────────────────────────────────┐
│ MetricMiddleware (指标中间件)             │  ← 计数器 +1、记录直方图
│  ┌─────────────────────────────────────┐ │
│  │ TracerMiddleware (追踪中间件)        │ │  ← 创建 Span、记录属性
│  │  ┌───────────────────────────────┐ │ │
│  │  │ bus.Sum() [原始业务代码]      │ │ │  ← 完全不知道任何追踪/指标
│  │  │ return a + b                  │ │ │
│  │  └───────────────────────────────┘ │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 代码实现

#### 原始业务层（bus.go）

```go
// 纯粹的业务逻辑，不包含任何追踪/指标代码
type bus struct{}

func (bus *bus) Sum(_ context.Context, a, b int64) int64 {
	return a + b
}

func (bus *bus) Concat(_ context.Context, a, b string) string {
	return a + b
}
```

**为什么这样做**：
- 业务代码完全独立，可单独测试
- 不依赖任何外部包（无 import otel）
- 将来想换掉 OpenTelemetry，只改中间件，不改业务代码

#### 追踪中间件（trace.go）

```go
type traceBus struct {
	tracer trace.Tracer
	Next   Bus
}

func TracerMiddleware(bus Bus, tracer trace.Tracer) Bus {
	return &traceBus{tracer: tracer, Next: bus}
}

func (bus *traceBus) Sum(ctx context.Context, a, b int64) int64 {
	// ① 创建 Span
	ctx, span := bus.tracer.Start(ctx, "Sum")
	defer span.End()

	// ② 调用实际业务
	c := bus.Next.Sum(ctx, a, b)

	// ③ 记录结果
	span.SetAttributes(
		attribute.Int64("a", a),
		attribute.Int64("b", b),
		attribute.Int64("c", c),
	)
	return c
}
```

**为什么这样写**：
- `Next` 指向下一层（原始业务），形成链表
- `ctx` 被 `tracer.Start()` 更新，新 Span 的信息被注入到 ctx 中
- `span.SetAttributes` 记录输入输出参数，方便排查问题

#### 指标中间件（metric.go）

```go
type metricBus struct {
	sumCounter    metric.Int64Counter
	concatCounter metric.Int64Counter
	sumHistogram  metric.Int64Histogram
	Next          Bus
}

func MetricMiddleware(bus Bus, ...) Bus {
	return &metricBus{..., Next: bus}
}

func (bus *metricBus) Sum(ctx context.Context, a, b int64) int64 {
	bus.sumCounter.Add(ctx, 1)           // 计数器 +1
	c := bus.Next.Sum(ctx, a, b)         // 调用实际业务
	bus.sumHistogram.Record(ctx, c, ...) // 记录结果分布
	return c
}
```

**为什么这样写**：
- 计数器在调用**之前**增加（记录发生了这次调用）
- 直方图在调用**之后**记录（记录业务返回值）
- 顺序不重要，重要的是指标和业务逻辑完全解耦

#### 组装中间件链（main.go）

```go
func getBus() (bus.Bus, trace.Tracer) {
	tracer := otel.Tracer("addsvc")
	b := bus.NewBus()                     // ① 最底层：原始业务

	b = bus.TracerMiddleware(b, tracer)    // ② 包裹追踪

	meter := otel.Meter("addsvc")
	sumCounter, _ := meter.Int64Counter("sum", ...)
	sumHistogram, _ := meter.Int64Histogram("sum_histogram", ...)
	b = bus.MetricMiddleware(b, sumCounter, concatCounter, sumHistogram) // ③ 再包裹指标

	return b, tracer
}
```

**为什么 MetricMiddleware 在 TracerMiddleware 之后**：
- 调用顺序：`MetricMiddleware.Sum()` → `TracerMiddleware.Sum()` → `bus.Sum()`
- 返回顺序：`bus.Sum()` → `TracerMiddleware.Sum()` → `MetricMiddleware.Sum()`
- 这样每个中间件都能完整地观测到整个调用过程

---

## 分布式链路：Propagator 传播器

### 核心问题：跨服务传递 Trace ID

`addsvc-server` 调用 `strsvc-server` 时，它们是**两个独立的进程**，内存地址不共享。怎么让 `strsvc-server` 知道自己在哪条 Trace 上？

### 解决方案：把 Trace ID 写入 HTTP Headers

```
addsvc-server                                    strsvc-server
内存中的 ctx                                       内存中的 ctx
┌────────────────┐                            ┌────────────────┐
│ TraceID: abc   │  ── gRPC 请求 ──▶         │ TraceID: ???   │
│ SpanID: 001    │    HTTP Headers           │ 不知道是谁的   │
│ ParentID: nil  │    traceparent:           │ 子Span        │
└────────────────┘    abc-001-0             └────────────────┘

通过 Propagator 注入      Headers 传输      通过 Propagator 提取
```

### 代码实现

#### 发送方：Inject（注入）

```go
func (s *addSvc) Sum(ctx context.Context, in *proto.SumRequest) (*proto.SumReply, error) {
	// ① 创建 Span（这会自动把 TraceID 放进 ctx）
	ctx, span := s.tracer.Start(ctx, "addsvc.Sum")
	defer span.End()

	// ② 把 ctx 中的 Trace 信息注入到 MapCarrier
	md := &propagation.MapCarrier{}
	s.propagator.Inject(ctx, md)  // md 现在包含 traceparent 等信息

	// ③ 把 MapCarrier 塞进 gRPC 的 metadata
	ctx = metadata.NewOutgoingContext(ctx, metadata.New(*md))

	// ④ 调用下游服务
	c := s.bus.Sum(ctx, in.A, in.B)

	return &proto.SumReply{V: c}, nil
}
```

**为什么要用 MapCarrier**：
- Propagator 不知道也不关心底层是 HTTP 还是 gRPC
- 它只负责"把 Trace 信息放进一个 K-V 容器"
- MapCarrier 是最简单的 K-V 容器实现

**为什么要转成 metadata.New()**：
- gRPC 只认 metadata，不认 MapCarrier
- 需要把 Map 转成 metadata 塞进请求

#### 接收方：Extract（提取）

```go
func (s *strSvc) Count(ctx context.Context, in *proto.CountRequest) (*proto.CountReply, error) {
	// ① 从 gRPC 请求中取出 metadata
	md, _ := metadata.FromIncomingContext(ctx)

	// ② 转成 Propagator 认识的 MapCarrier
	mp := propagation.MapCarrier{}
	for key, value := range md {
		mp[key] = value[0]
	}

	// ③ 从 MapCarrier 中还原 Trace 上下文
	ctx = s.propagator.Extract(ctx, mp)  // ctx 现在有 TraceID 了

	// ④ 创建子 Span，自动关联到父 Span
	ctx, span := s.tracer.Start(ctx, "strsvc.Count")
	defer span.End()

	count := s.bus.Count(ctx, in.Str)
	return &proto.CountReply{V: count}, nil
}
```

**为什么要两步转换**：
- gRPC 的 API 是 `metadata.FromIncomingContext()`
- Propagator 的 API 是 `Extract(ctx, MapCarrier)`
- 所以：metadata → MapCarrier → Propagator.Extract()

**为什么这样做的效果是"子 Span 自动关联父 Span"**：
- `tracer.Start(ctx, "strsvc.Count")` 拿到 ctx 中的 TraceID
- 新 Span 的 parent_id 字段自动设为 ctx 中的 SpanID
- 最终在 Jaeger UI 上显示为树形结构

### traceparent 格式

```
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
             │  │                            │                    │
             │  │                            │                    └── 采样标志(01=采样)
             │  │                            └─────────────────────────── Span ID (16字符)
             │  └────────────────────────────────────────────────────── Trace ID (32字符)
             └── 版本号(00)
```

---

## Baggage（ baggage 行李）

### 什么是 Baggage？

除了 Trace 上下文（TraceID、SpanID），你还想传递一些**自定义业务数据**（如 `user_id`、`tenant_id`），让所有下游服务都能读取。

**传统方式**：每个服务调用时手动传递。

```go
// ❌ 手动传递，每个接口都要改
type CountRequest struct {
	Str     string
	UserID  string
	TenantID string
}
```

**Baggage 方式**：存到上下文，自动随请求传播。

```go
// ✅ 存到上下文，所有下游服务都能读取
b := customBaggage()
ctx = baggage.ContextWithBaggage(ctx, b)
```

### 代码实现

#### 创建 Baggage

```go
func customBaggage() baggage.Baggage {
	b, _ := baggage.New()

	// 定义属性元数据（用于校验/文档）
	gender, _ := baggage.NewKeyValueProperty("gender", "1")
	age, _ := baggage.NewKeyValueProperty("age", "18")

	// 创建 baggage 成员
	author, _ := baggage.NewMember("author", "nick", gender, age)
	org, _ := baggage.NewMember("org", "0voice")

	b1, _ := baggage.New(author, org)
	return b1
}
```

**为什么要用 Property 定义属性**：
- Property 可以定义**元数据**（如值类型、验证规则）
- 例子：`gender` 属性只能接受 "1" 或 "2"，Property 可以帮你在创建时校验

#### 附加 Baggage

```go
func (s *addSvc) Concat(ctx context.Context, in *proto.ConcatRequest) (*proto.ConcatReply, error) {
	// ① 附加 Baggage 到上下文
	b := customBaggage()
	ctx = baggage.ContextWithBaggage(ctx, b)

	ctx, span := s.tracer.Start(ctx, "addsvc.Concat")
	defer span.End()

	md := &propagation.MapCarrier{}
	s.propagator.Inject(ctx, md)  // Baggage 会随 traceparent 一起注入
	ctx = metadata.NewOutgoingContext(ctx, metadata.New(*md))

	// ② 调用下游服务（Baggage 自动跟着 ctx 走）
	c := s.bus.Concat(ctx, in.A, in.B)
	countRes, err := s.strClient.Count(ctx, countIn)
	uppercaseRes, err := s.strClient.Uppercase(ctx, uppercaseIn)
}
```

#### 读取 Baggage

```go
func (s *strSvc) Uppercase(ctx context.Context, in *proto.UppercaseRequest) (*proto.UppercaseReply, error) {
	// 从上下文中读取 Baggage（不需要手动传递，自动注入/提取）
	b := baggage.FromContext(ctx)

	ctx, span := s.tracer.Start(ctx, "strsvc.Uppercase")
	defer span.End()

	span.SetAttributes(
		attribute.String("author", b.Member("author").Value()),  // "nick"
		attribute.String("org", b.Member("org").Value()),       // "0voice"
	)

	str := s.bus.Uppercase(ctx, in.Str)
	return &proto.UppercaseReply{V: str}, nil
}
```

### Baggage vs 普通参数

| 维度 | 普通参数 | Baggage |
|---|---|---|
| 传递方式 | 每个服务手动转发 | 自动随请求传播 |
| 需要改接口吗？ | 是 | 否 |
| 跨服务传递？ | 每个服务都要转 | 自动 |
| 用途 | 业务数据 | 诊断/追踪元数据 |
| 示例 | user_id, amount, product_id | env, tenant, version |

### Baggage 的传播原理

Baggage 之所以能跨服务传播，是因为 Propagator 同时传播了：
- `traceparent` → Trace 上下文
- `tracestate` → 额外的键值对（Baggage 放在这里）

**发送时**：`propagator.Inject()` 把 Baggage 序列化到 `tracestate` header。

**接收时**：`propagator.Extract()` 从 `tracestate` 反序列化，恢复 Baggage 到 ctx。

---

## Propagator 配置

```go
otel.SetTextMapPropagator(
	propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{},   // 传播 TraceID、SpanID
		propagation.Baggage{},        // 传播自定义键值对
	),
)
```

**为什么要组合**：
- `TraceContext` 负责链路追踪的 ID 传递
- `Baggage` 负责自定义数据的传递
- 两者协同工作，确保整个链路既有追踪能力，又有业务上下文

---

## 双重初始化：TracerProvider + MeterProvider

```go
func main() {
	// ① 初始化链路追踪
	tracerShutdown, _ := initTracerProvider(*otlpGrpcEndpoint)
	defer tracerShutdown(context.Background())

	// ② 初始化指标监控
	meterShutdown, _ := initMeterProvider(*otlpGrpcEndpoint)
	defer meterShutdown(context.Background())

	// ③ 启动 gRPC 服务
	s := grpc.NewServer()
	proto.RegisterAddServer(s, server.NewAddSvc(...))
	s.Serve(lis)
}
```

**为什么要分别初始化**：
- TracerProvider 管理 Span 数据
- MeterProvider 管理 Counter、Histogram 数据
- 两者独立配置、独立导出
- 实际场景中可能 Trace 和 Metric 导送到不同的后端

---

## Concat 方法的完整链路

`Concat` 方法是最复杂的示例，展示了一个完整的分布式调用链：

```go
func (s *addSvc) Concat(ctx context.Context, in *proto.ConcatRequest) (*proto.ConcatReply, error) {
	// ① 添加 Baggage（所有下游服务都能读到）
	ctx = baggage.ContextWithBaggage(ctx, customBaggage())

	// ② 创建 Span
	ctx, span := s.tracer.Start(ctx, "addsvc.Concat")
	defer span.End()

	// ③ 注入上下文，准备调用下游
	md := &propagation.MapCarrier{}
	s.propagator.Inject(ctx, md)
	ctx = metadata.NewOutgoingContext(ctx, metadata.New(*md))

	// ④ 字符串拼接
	c := s.bus.Concat(ctx, in.A, in.B)

	// ⑤ 调用 strsvc 获取长度
	countRes, _ := s.strClient.Count(ctx, countIn)
	span.SetAttributes(attribute.Int64("str_len", countRes.V))  // 记录中间结果

	// ⑥ 调用 strsvc 转大写
	uppercaseRes, _ := s.strClient.Uppercase(ctx, uppercaseIn)
	span.SetAttributes(attribute.String("str_uppercase", uppercaseRes.V))

	return &proto.ConcatReply{V: uppercaseRes.V}, nil
}
```

**在 Jaeger UI 上呈现的 Span 树**：

```
addsvc.Concat
    │
    ├── bus.Concat              (a="abcd", b="efg", c="abcdefg")
    │
    ├── strsvc.Count            (str="abcdefg", str_len=7)
    │
    └── strsvc.Uppercase         (str="abcdefg", str_uppercase="ABCDEFG")
             ↑
             ↑ Baggage: author="nick", org="0voice"
             ↑ 自动传播，无需手动传递
```

---

## 快速运行

### 先启动 strsvc（下游服务）

```bash
cd strsvc/strsvc-server
go run main.go --otlp-grpc=192.168.239.154:5317
# 监听 :50052
```

### 再启动 addsvc（上游服务）

```bash
cd addsvc/addsvc-server
go run main.go --otlp-grpc=192.168.239.154:5317 --strsvc-endpoint=localhost:50052
# 监听 :50051
```

### 启动 CLI 客户端

```bash
cd addsvc/addsvc-cli
go run main.go
# 输出:
# v:23
# v:"ABCDEFG"
```

---

## 总结

```
┌──────────────────────────────────────────────────────────────────────┐
│                          addsvc 核心设计                               │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  装饰器模式（三层结构）：                                              │
│  MetricMiddleware → TracerMiddleware → bus (原始业务)                  │
│                                                                       │
│  分布式链路传播：                                                     │
│  addsvc-server                                                      │
│       │                                                              │
│       │ propagator.Inject() → metadata.New() → gRPC Headers           │
│       ▼                                                              │
│  strsvc-server                                                      │
│       │                                                              │
│       │ metadata.FromIncomingContext() → propagator.Extract()         │
│       │                                                              │
│       │ tracer.Start() → 自动关联父 Span，形成树形结构                 │
│                                                                       │
│  Baggage（自动跨服务传播的自定义数据）：                                │
│  baggage.ContextWithBaggage() → propagator.Inject()                   │
│  propagator.Extract() → baggage.FromContext()                         │
│                                                                       │
│  两种初始化：                                                        │
│  initTracerProvider() → otel.SetTracerProvider()                     │
│  initMeterProvider()  → otel.SetMeterProvider()                      │
│                                                                       │
│  Proto 定义：gRPC 接口契约，独立于业务逻辑                            │
└──────────────────────────────────────────────────────────────────────┘
```
