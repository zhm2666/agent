# metric-basic — OpenTelemetry 指标（Metrics）入门示例

## 模块概述

本模块展示了 OpenTelemetry Metrics API 的完整用法，涵盖 **Counter（计数器）**、**Gauge（实时指标）**、**Histogram（直方图）** 三种指标类型，以及多种导出方式（OTLP、Prometheus）。

---

## 为什么需要指标（Metrics）？

链路追踪（Trace）回答的是"**这次请求**发生了什么"，而指标（Metric）回答的是"**系统整体**表现如何"。

| 维度 | Trace（链路） | Metric（指标） |
|---|---|---|
| 数据粒度 | 单次请求 | 聚合统计 |
| 数据量 | 每请求1条 | 每指标1条/周期 |
| 保存周期 | 短期（7-30天） | 长期（几年） |
| 回答的问题 | "这次为什么失败？" | "系统健康吗？趋势如何？" |
| 典型用途 | 排查具体Bug | 容量规划、告警、SLO |

**两者是互补关系**：Trace 帮你定位问题，Metric 帮你发现问题。

---

## 核心概念

### 1. MeterProvider — 指标的全局管理器

**问题**：程序中可能有多处产生指标数据（HTTP服务、DB连接池、缓存等），如果各自管理导出，会造成连接浪费和配置混乱。

**解决**：全局只创建一个 `MeterProvider`，统一管理所有指标和导出逻辑。

```go
// 初始化顺序：Resource → Reader(Exporter) → MeterProvider → SetMeterProvider
provider := metric.NewMeterProvider(
	metric.WithResource(res),      // 带上服务标识
	metric.WithReader(metricReader), // 带上导出器
)
otel.SetMeterProvider(provider)    // 设置全局
```

**为什么这样做**：
- 所有指标自动带上 `service.name`、`service.version` 等资源信息
- 所有指标走同一个导出器，避免重复连接
- 便于统一配置采样率、导出间隔

### 2. Meter — 指标的创建工厂

**问题**：一个服务有多个功能模块（HTTP、DB、缓存），每个模块的指标需要区分命名空间。

**解决**：通过 `Meter("命名空间")` 创建不同模块的指标工厂。

```go
meter := otel.Meter("metric-basic-meter")  // 所有该模块的指标都在此命名空间下
counter, _ := meter.Float64Counter("counter")  // 完整名称 = "metric-basic-meter/counter"
```

---

## 三种指标类型详解

### 类型一：Counter（累计计数器）

**使用场景**：统计只会增加的值，如请求总数、错误次数、订单数量。

```go
counter, err := meter.Float64Counter("counter", api.WithDescription("累计指标"))
counter.Add(ctx, 5, api.WithAttributes(attrs...))  // 累计 +5
```

**为什么用 Counter 而不是普通变量**：
- 自动处理并发安全（内部有锁）
- 自动聚合（多实例可合并）
- 可附加标签（`attributes`），实现多维度统计

**应用举例**：想知道每个 API 路径的请求数，可以这样加标签：

```go
counter.Add(ctx, 1, api.WithAttributes(
	attribute.String("path", "/api/orders"),
	attribute.String("method", "POST"),
	attribute.Int("status", 200),
))
```

### 类型二：ObservableCounter（异步计数器）

**问题**：有些值不是你自己产生的，比如从外部系统（Kafka、Redis）读取当前偏移量，你无法主动调用 `Add()`。

**解决**：注册一个回调函数，每次指标系统采集时才获取当前值。

```go
meter.Float64ObservableCounter("counter1",
	api.WithFloat64Callback(func(ctx context.Context, o api.Float64Observer) error {
		o.Observe(float64(time.Now().Unix()))  // 采集时才计算
		return nil
	}),
)
```

**执行时机**：不是代码执行时立即记录，而是当 `PeriodicReader` 每5秒采集一次时，回调函数被触发。这种模式叫 **Pull 模式**（指标系统主动拉取）。

### 类型三：ObservableGauge（实时指标）

**使用场景**：测量随时变化的瞬时值，如当前 CPU 使用率、内存占用、队列深度。

```go
rng := rand.New(rand.NewSource(time.Now().UnixNano()))
gauge, _ := meter.Float64ObservableGauge("gauge", api.WithDescription("实时指标"))
meter.RegisterCallback(func(ctx context.Context, o api.Observer) error {
	n := rng.Intn(100)  // 每次采集时随机生成 0-99
	o.ObserveFloat64(gauge, float64(n))
	return nil
}, gauge)
```

**为什么叫"Gauge"（仪表盘）**：
- 像汽车仪表盘上的时速表，读取的是**某一时刻的瞬时值**
- 不累加，只记录当前快照

**和 Counter 的本质区别**：
```
Counter:   ████████████░░░░░░░░░░░░  累计值，只增不减
Gauge:     ████████░░░░████████░░░░  瞬时值，可增可减
```

### 类型四：Histogram（直方图/分布图）

**使用场景**：统计一组数值的分布，用于计算平均值、P50/P90/P99 等百分位数。

```go
histogram, _ := meter.Float64Histogram("histogram", api.WithDescription("直方图"))
histogram.Record(ctx, 233)  // 记录多个值
histogram.Record(ctx, 23)
histogram.Record(ctx, 33)
// ...
```

**为什么需要 Histogram**：
- 知道平均延迟是 100ms 没用，你需要知道"99% 的请求延迟在 500ms 以内"
- Histogram 自动帮你计算百分位数（P50、P90、P99）

**内部原理**：SDK 将数值落入不同的"桶"（bucket），最终导出时提供每个桶的累计计数，从而计算出百分位数。

---

## View（自定义视图）

**问题**：默认的 Histogram 桶边界是 `[0, 5, 10, 25, 50, 75, 100, 250, 500, 1000, ...]`，但你的业务延迟范围可能完全不同（0-50ms vs 0-10000ms）。

**解决**：通过 `View` 自定义指标名称和聚合方式。

```go
view := metric.NewView(
	metric.Instrument{
		Name:  "custom_histogram",                   // 原始指标名
		Scope: instrumentation.Scope{Name: "metric-basic-meter"},  // 作用范围
	},
	metric.Stream{
		Name: "myhistogram",                                   // 导出后的新名称
		Aggregation: aggregation.ExplicitBucketHistogram{       // 自定义桶边界
			Boundaries: []float64{2, 4, 8, 16, 32, 64, 128, 256, 512},
		},
	},
)
```

**为什么需要 View**：
- 重命名指标（`custom_histogram` → `myhistogram`），不改变已有代码
- 自定义 Histogram 桶边界，适应不同业务场景
- 过滤或聚合不需要的指标

---

## 导出器（Exporter）

### 三种导出方式对比

| 方式 | 触发机制 | 适用场景 | 端口 |
|---|---|---|---|
| `PeriodicReader` + OTLP | 定时推送（每5秒） | 生产环境，推送到 Collector | — |
| `Prometheus` | Prometheus 主动拉取 | Prometheus 监控生态 | `:2223/metrics` |
| Console | 打印到标准输出 | 本地调试 | — |

### 方式一：OTLP 导出（推模式）

```go
exporter, _ := otlpmetricgrpc.New(ctx, otlpmetricgrpc.WithGRPCConn(conn))
metricReader = metric.NewPeriodicReader(exporter, metric.WithInterval(time.Second*5))
```

**为什么用 PeriodicReader**：
- 每 5 秒批量推送一次，减少网络 IO
- 不依赖外部系统拉取，主动推送

### 方式二：Prometheus 导出（拉模式）

```go
metricReader, _ = prometheus.New()
```

```go
func serveMetrics() {
	http.Handle("/metrics", promhttp.Handler())
	http.ListenAndServe(":2223", nil)
}
```

**Prometheus 的优势**：
- 不需要每个服务都主动推送，减少服务负担
- Prometheus 统一管理所有服务的采集节奏
- 与 Prometheus 生态完美集成（Grafana、Alertmanager）

---

## 标签（Attributes）

**为什么需要标签**：同一个指标名，可以按不同维度拆分。

```go
attrs := []attribute.KeyValue{
	attribute.Key("A").String("B"),
	attribute.Key("C").String("D"),
}
counter.Add(ctx, 5, api.WithAttributes(attrs...))
```

**效果**：在 Prometheus 中，你会看到：

```
# 没有标签
counter_total 5

# 有标签 A=B, C=D
counter_total{A="B",C="D"} 5
```

**为什么这样做**：你可以通过标签区分不同业务维度的数据，而不需要定义多个指标名。比如：

```go
counter.Add(ctx, 1, api.WithAttributes(
	attribute.String("path", "/api/users"),     // 维度1
	attribute.String("method", "GET"),           // 维度2
	attribute.Int("status", 200),                // 维度3
))
```

然后在 Grafana 中按 `path`、`method`、`status` 分别筛选和聚合。

---

## 优雅退出

```go
shutdown, err := initProvider(...)
defer shutdown(ctx)  // 程序退出前确保指标数据发送完毕

ctx, stop := signal.NotifyContext(ctx, os.Kill, os.Interrupt)
<-ctx.Done()  // 等待信号
```

**为什么必须这样做**：
- 程序退出时，可能还有数据在内存缓冲区中未发送
- `shutdown()` 会强制将剩余数据导出后再退出
- 否则会丢失最后一次采集周期内的指标数据

---

## 快速运行

```bash
cd metric-basic

# 方式1：Prometheus 拉取模式（默认）
go run main.go
# 访问 http://localhost:2223/metrics

# 方式2：推送到 OTLP Collector（gRPC）
go run main.go --otlp-grpc=192.168.239.154:5317

# 方式3：推送到 OTLP Collector（HTTP）
go run main.go --otlp-http=192.168.239.154:5318
```

---

## 总结

```
┌─────────────────────────────────────────────────────────────────┐
│                      指标的核心知识点                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  MeterProvider (全局管理器)                                       │
│      │                                                           │
│      ├── Resource: 服务标识 (service.name, version, env)           │
│      ├── Meter:    指标工厂 (按模块命名)                           │
│      ├── View:     自定义聚合方式 (重命名、桶边界)                  │
│      └── Reader:   导出方式 (OTLP推送 / Prometheus拉取)            │
│                                                                  │
│  三种指标对比:                                                    │
│  ┌─────────────┬──────────────┬──────────────────────────┐   │
│  │ Counter      │ 累计值+1      │ 请求数、错误数、订单数        │   │
│  │ ObservableCounter │ 回调拉取 │ 外部系统的当前状态           │   │
│  │ ObservableGauge  │ 回调拉取 │ CPU、内存、队列深度          │   │
│  │ Histogram    │ 记录数值分布  │ 延迟分布，计算P50/P90/P99    │   │
│  └─────────────┴──────────────┴──────────────────────────┘   │
│                                                                  │
│  Attributes 标签: 同指标名多维度拆分                               │
│  BatchSpanProcessor: 批量发送减少网络IO                           │
│  优雅退出: defer shutdown() 确保数据不丢失                        │
└─────────────────────────────────────────────────────────────────┘
```
