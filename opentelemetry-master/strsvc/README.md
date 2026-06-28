# strsvc — 字符串服务（gRPC + 链路追踪接收端 + 指标监控）

## 模块概述

本模块是 **addsvc 的下游服务**，展示了作为"被调用方"如何：
- **接收并提取**上游传递的 Trace 上下文
- **读取并使用** Baggage 中的自定义数据
- **继续追踪**：创建子 Span，自动关联父 Span
- **记录指标**：Counter 和 Histogram

---

## 服务架构

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           strsvc 模块架构                                  │
│                                                                          │
│  addsvc-server (:50051) ──────────────────────────────────────────┐    │
│       │                                                              │    │
│       │ gRPC 调用 Count(str)                                        │    │
│       │ gRPC 调用 Uppercase(str)                                    │    │
│       │ Headers 中携带 traceparent + tracestate(Baggage)            │    │
│       └────────────────────────────────────────────────────────────┘    │
│                                                                           │
│       ▼                                                                   │
│  strsvc-server (:50052)                                                  │
│       │                                                                  │
│       │ Extract: 从 Headers 提取 Trace 上下文                            │
│       │ Extract: 从 Headers 提取 Baggage                                 │
│       │ Start Span: 自动关联到父 Span                                   │
│       │ Read Baggage: 读取 author, org 等自定义数据                      │
│       │ Record Metric: Counter +1, Histogram.Record                      │
│       │                                                                  │
│       ▼                                                                  │
│  strsvc-cli (测试客户端)                                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

### Proto 定义

```protobuf
service Str {
  rpc Count (CountRequest) returns (CountReply)       // len(str)，返回字符串长度
  rpc Uppercase (UppercaseRequest) returns (UppercaseReply) // strings.ToUpper()
}

message CountRequest { string str = 1; }
message CountReply { int64 v = 1; }

message UppercaseRequest { string str = 1; }
message UppercaseReply { string v = 1; }
```

---

## 核心职责：作为链路接收端

### 与 addsvc 的对比

| 维度 | addsvc（发送方） | strsvc（接收方） |
|---|---|---|
| 主要职责 | 创建 Span、注入上下文 | 提取上下文、创建子 Span |
| Propagator 操作 | `Inject()` | `Extract()` |
| Span 创建 | 根 Span 或子 Span | 一定是子 Span（自动关联父 Span） |
| Baggage | 设置值 | 读取值 |
| 调用下游 | 有（调用 strsvc） | 无（是最终端） |

### 接收端的核心任务

作为链路接收端，`strsvc-server` 需要完成三件事：

```
┌─────────────────────────────────────────────────────────────┐
│                    strsvc-server 的核心任务                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  任务1: Extract（提取上下文）                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ metadata.FromIncomingContext() → MapCarrier            │ │
│  │ → propagator.Extract() → ctx (包含 TraceID + Baggage)  │ │
│  └───────────────────────────────────────────────────────┘ │
│                      ↓                                      │
│  任务2: Start Span（创建子 Span）                            │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ tracer.Start(ctx, "strsvc.Count")                     │ │
│  │        ↑                                             │ │
│  │   ctx 中有父 Span ID，自动关联                         │ │
│  └───────────────────────────────────────────────────────┘ │
│                      ↓                                      │
│  任务3: Read Baggage（读取自定义数据）                        │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ baggage.FromContext(ctx) → b.Member("author").Value()  │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 代码实现详解

### 1. Extract（提取上下文）

```go
func (s *strSvc) Count(ctx context.Context, in *proto.CountRequest) (*proto.CountReply, error) {
	// ① 从 gRPC 请求中获取 metadata
	md, _ := metadata.FromIncomingContext(ctx)

	// ② 转成 Propagator 认识的 MapCarrier
	mp := propagation.MapCarrier{}
	for key, value := range md {
		mp[key] = value[0]  // 提取第一个值
	}

	// ③ 从 MapCarrier 中提取 Trace 上下文
	// 这会把 traceparent 中的 TraceID、SpanID 还原到 ctx 中
	ctx = s.propagator.Extract(ctx, mp)

	// ④ 继续传递 ctx（Baggage 也在 ctx 中了）
	ctx, span := s.tracer.Start(ctx, "strsvc.Count")
	defer span.End()

	count := s.bus.Count(ctx, in.Str)
	return &proto.CountReply{V: count}, nil
}
```

**为什么必须 Extract**：
- 上游把 Trace 信息藏在 HTTP Headers 中
- gRPC 请求到达时，这些信息在 `metadata` 里
- Propagator.Extract() 把 metadata → MapCarrier → ctx，还原 Trace 上下文

**为什么 `tracer.Start(ctx, "strsvc.Count")` 会自动创建子 Span**：
- 因为 ctx 中已经有了父 Span 的 ID
- SDK 自动读取 ctx 中的父 Span 信息
- 新 Span 的 parent_id 自动设为 ctx 中的 SpanID

### 2. Read Baggage（读取自定义数据）

```go
func (s *strSvc) Uppercase(ctx context.Context, in *proto.UppercaseRequest) (*proto.UppercaseReply, error) {
	// ① 同样先 Extract（Uppercase 也是被调用方）
	md, _ := metadata.FromIncomingContext(ctx)
	mp := propagation.MapCarrier{}
	for key, value := range md {
		mp[key] = value[0]
	}
	ctx = s.propagator.Extract(ctx, mp)

	// ② 从上下文中读取 Baggage（addsvc 那边塞进来的）
	b := baggage.FromContext(ctx)

	// ③ 创建 Span 并记录 Baggage 数据
	ctx, span := s.tracer.Start(ctx, "strsvc.Uppercase")
	defer span.End()

	// ④ 把 Baggage 的值记录到 Span 属性中
	// 在 Jaeger UI 上可以看到 author="nick", org="0voice"
	span.SetAttributes(
		attribute.String("author", b.Member("author").Value()),
		attribute.String("org", b.Member("org").Value()),
	)

	str := s.bus.Uppercase(ctx, in.Str)
	return &proto.UppercaseReply{V: str}, nil
}
```

**为什么在 Jaeger 上能看到 Baggage**：
- `span.SetAttributes()` 把 Baggage 的值记录到 Span 属性中
- Span 数据被 Exporter 发送到 OTEL Collector
- 最终在 Jaeger UI 的 Span Details 中显示

### 3. 完整的调用链

```
addsvc-cli 调用 Concat("abcd", "efg")
        │
        │ Baggage: author="nick", org="0voice"
        ▼
┌─────────────────────────────────────────────────────────────────┐
│ addsvc.Concat                                                   │
│   ├── bus.Concat → "abcdefg"                                    │
│   │                                                              │
│   ├── strsvc.Count("abcdefg")                                    │
│   │   └── 返回 7                                                 │
│   │                                                              │
│   └── strsvc.Uppercase("abcdefg")                                │
│         └── 返回 "ABCDEFG"                                       │
│             ├── Span 属性: author="nick", org="0voice"          │
│             └── Baggage 来自上游，无需任何手动传递                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 装饰器模式在 strsvc 中的应用

和 addsvc 一样，strsvc 也使用了装饰器模式，但侧重点不同：

| 模块 | 主要中间件 | 关注点 |
|---|---|---|
| addsvc | TracerMiddleware + MetricMiddleware | 统计加法/拼接的调用次数和结果 |
| strsvc | TracerMiddleware + MetricMiddleware | 统计字符串操作的调用次数和长度分布 |

### 追踪中间件（trace.go）

```go
func (bus *traceBus) Count(ctx context.Context, str string) int64 {
	ctx, span := bus.tracer.Start(ctx, "Count")
	defer span.End()
	count := bus.Next.Count(ctx, str)
	span.SetAttributes(
		attribute.String("str", str),       // 记录输入
		attribute.Int64("count", count),    // 记录输出
	)
	return count
}
```

### 指标中间件（metric.go）

```go
func (bus *metricBus) Count(ctx context.Context, str string) int64 {
	bus.countCounter.Add(ctx, 1)         // 调用次数 +1
	count := bus.Next.Count(ctx, str)    // 实际业务
	bus.countHistogram.Record(ctx, count) // 记录结果分布
	return count
}

func (bus *metricBus) Uppercase(ctx context.Context, str string) string {
	bus.uppercaseCounter.Add(ctx, 1)    // 调用次数 +1
	return bus.Next.Uppercase(ctx, str) // 实际业务
}
```

**为什么 Count 记录 Histogram，Uppercase 不记录**：
- Count 返回 `len(str)`，是个数值，适合用直方图统计分布（很多短字符串 vs 少数长字符串）
- Uppercase 返回字符串，不适合用数值直方图

---

## 与 addsvc 的对称性

```
┌─────────────────────────┬─────────────────────────────────────────────┐
│         addsvc          │                 strsvc                       │
├─────────────────────────┼─────────────────────────────────────────────┤
│ addsvc-server (:50051) │ strsvc-server (:50052)                      │
│                         │                                             │
│ Propagator.Inject()    │ Propagator.Extract()                       │
│   把 Trace 注入 Headers │   从 Headers 提取 Trace                    │
│                         │                                             │
│ baggage.ContextWithBaggage() │ baggage.FromContext()                 │
│   设置 Baggage          │   读取 Baggage                             │
│                         │                                             │
│ 调用下游服务            │ 被上游调用（最终端）                        │
│                         │                                             │
│ strClient.Count()      │ bus.Count()                                 │
│ strClient.Uppercase()  │ bus.Uppercase()                             │
├─────────────────────────┼─────────────────────────────────────────────┤
│ 作为: 调用方            │ 作为: 被调用方                              │
│ 发送 Trace 上下文       │ 接收 Trace 上下文                          │
│ 设置 Baggage            │ 读取 Baggage                               │
└─────────────────────────┴─────────────────────────────────────────────┘
```

---

## 快速运行

### 先启动 strsvc（下游服务）

```bash
cd strsvc/strsvc-server
go run main.go --otlp-grpc=192.168.239.154:5317
# 监听 :50052
```

### 启动 strsvc-cli 测试客户端

```bash
cd strsvc/strsvc-cli
go run main.go
# 输出:
# v:11
# v:"ABCDEFGHIJK"
```

### 查看链路效果

在 Jaeger UI 中搜索 `strsvc-server`，可以看到：
- 所有从 addsvc 传来的请求链路
- Span 自动关联到父 Span
- `strsvc.Uppercase` Span 上可以看到 `author=nick`, `org=0voice` 属性

---

## 总结

```
┌──────────────────────────────────────────────────────────────────────┐
│                       strsvc 核心知识点                               │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  作为链路接收端的核心职责：                                             │
│                                                                       │
│  1. Extract（提取上下文）                                             │
│     metadata.FromIncomingContext() → MapCarrier                        │
│     → propagator.Extract() → ctx                                      │
│                                                                       │
│  2. Start Span（创建子 Span）                                          │
│     tracer.Start(ctx, "strsvc.Count")                                 │
│     ctx 中有父 Span ID → 自动关联到树形结构中                          │
│                                                                       │
│  3. Read Baggage（读取自定义数据）                                    │
│     baggage.FromContext(ctx) → b.Member("name").Value()                │
│     读取后可以记录到 Span 属性中，在 Jaeger 上看到                      │
│                                                                       │
│  与 addsvc 的对称关系：                                                │
│  ┌──────────────┬────────────────────────────────┐                   │
│  │ addsvc        │ strsvc                          │                   │
│  │ Inject        │ Extract                         │                   │
│  │ 设置 Baggage   │ 读取 Baggage                    │                   │
│  │ 调用下游       │ 被调用（终端）                   │                   │
│  └──────────────┴────────────────────────────────┘                   │
│                                                                       │
│  装饰器模式保持一致：                                                  │
│  MetricMiddleware → TracerMiddleware → bus (原始业务)                  │
│  Counter: 统计调用次数                                                 │
│  Histogram: 统计 Count 的返回值分布                                   │
└──────────────────────────────────────────────────────────────────────┘
```
