# 从零到分布式链路追踪：bak 版本详解与演进之路

> 本文档从 `bak/` 版本的纯业务代码开始讲解，然后逐步演进成分布式链路追踪。适合从头理解整个链路追踪的设计思路。

---

## 第一部分：bak 版本详解

### 1.1 项目架构

bak 版本是一个最简化的微服务架构，没有 OpenTelemetry，只有纯业务逻辑。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            bak 版本架构                                      │
│                                                                          │
│  addsvc-cli                          strsvc-cli                            │
│  (测试客户端)                        (测试客户端)                            │
│       │                                  │                                 │
│       │ gRPC :50051                      │ gRPC :50052                     │
│       ▼                                  ▼                                 │
│  ┌──────────────┐                  ┌──────────────┐                    │
│  │ addsvc-server │                  │ strsvc-server │                    │
│  │              │                  │              │                    │
│  │ server.go    │                  │ server.go    │                    │
│  │   │          │                  │   │          │                    │
│  │   ▼          │                  │   ▼          │                    │
│  │ bus.go       │                  │ bus.go       │                    │
│  │   • Sum()    │                  │   • Count()  │                    │
│  │   • Concat() │                  │   • Uppercase() │                  │
│  └──────────────┘                  └──────────────┘                    │
│                                                                          │
│  两个服务完全独立，不知道对方存在                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**每个服务都是独立的进程**，它们之间**没有通信**。每个服务只处理自己的业务，然后返回结果。

---

### 1.2 Proto 定义（接口契约）

#### addsvc 的 Proto

```protobuf
service Add {
  rpc Sum (SumRequest) returns (SumReply)       // 两数相加
  rpc Concat (ConcatRequest) returns (ConcatReply) // 字符串拼接
}

message SumRequest { int64 a = 1; int64 b = 2; }
message SumReply { int64 v = 1; }

message ConcatRequest { string a = 1; string b = 2; }
message ConcatReply { string v = 1; }
```

#### strsvc 的 Proto

```protobuf
service Str {
  rpc Count (CountRequest) returns (CountReply)       // 字符串长度
  rpc Uppercase (UppercaseRequest) returns (UppercaseReply) // 转大写
}

message CountRequest { string str = 1; }
message CountReply { int64 v = 1; }

message UppercaseRequest { string str = 1; }
message UppercaseReply { string v = 1; }
```

**为什么要用 Proto**：
- 定义清晰的服务接口契约
- gRPC 自动生成客户端/服务端代码
- 强类型，不会传错参数

---

### 1.3 业务层（bus.go）

#### addsvc/bus.go

```go
package bus

func Concat(a, b string) string {
	return a + b
}
func Sum(a, b int64) int64 {
	return a + b
}
```

**纯粹的数学函数**，没有任何外部依赖：
- `Sum(1, 2)` → `3`
- `Concat("abc", "def")` → `"abcdef"`

#### strsvc/bus.go

```go
package bus

import "strings"

func Count(str string) int64 {
	return int64(len(str))
}

func Uppercase(str string) string {
	return strings.ToUpper(str)
}
```

**纯粹的字符串处理函数**：
- `Count("abcdef")` → `6`
- `Uppercase("abc")` → `"ABC"`

**这些函数的共同特点**：
- 输入 → 输出，无副作用
- 不访问网络
- 不访问数据库
- 不依赖任何外部服务
- **最容易测试和理解**

---

### 1.4 服务端（server.go）

#### addsvc/server.go

```go
type addSvc struct {
	proto.UnimplementedAddServer  // gRPC 要求嵌入此类型
}

func NewAddSvc() proto.AddServer {
	return &addSvc{}
}

func (s *addSvc) Sum(ctx context.Context, in *proto.SumRequest) (*proto.SumReply, error) {
	c := bus.Sum(in.A, in.B)   // 调用业务层
	return &proto.SumReply{V: c}, nil  // 返回结果
}

func (s *addSvc) Concat(ctx context.Context, in *proto.ConcatRequest) (*proto.ConcatReply, error) {
	c := bus.Concat(in.A, in.B)
	return &proto.ConcatReply{V: c}, nil
}
```

**职责**：接收 gRPC 请求，调用业务层，返回结果。

#### strsvc/server.go

```go
type strSvc struct {
	proto.UnimplementedStrServer
}

func NewStrSvc() proto.StrServer {
	return &strSvc{}
}

func (s *strSvc) Count(ctx context.Context, in *proto.CountRequest) (*proto.CountReply, error) {
	count := bus.Count(in.Str)
	return &proto.CountReply{V: count}, nil
}

func (s *strSvc) Uppercase(ctx context.Context, in *proto.UppercaseRequest) (*proto.UppercaseReply, error) {
	str := bus.Uppercase(in.Str)
	return &proto.UppercaseReply{V: str}, nil
}
```

**职责**：接收 gRPC 请求，调用业务层，返回结果。

---

### 1.5 服务启动（main.go）

#### addsvc-server/main.go

```go
func main() {
	// ① 监听 TCP 端口
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatal(err)
	}

	// ② 创建 gRPC Server
	s := grpc.NewServer()

	// ③ 注册服务实现
	proto.RegisterAddServer(s, server.NewAddSvc())

	// ④ 启动服务（阻塞）
	if err := s.Serve(lis); err != nil {
		log.Fatal(err)
	}
}
```

#### strsvc-server/main.go

```go
func main() {
	lis, err := net.Listen("tcp", ":50052")
	if err != nil {
		log.Fatal(err)
	}
	s := grpc.NewServer()
	proto.RegisterStrServer(s, server.NewStrSvc())
	if err := s.Serve(lis); err != nil {
		log.Fatal(err)
	}
}
```

**启动流程**：
```
net.Listen("tcp", ":50051")   ← 告诉操作系统打开端口 50051
        ↓
grpc.NewServer()              ← 创建 gRPC 服务器实例
        ↓
RegisterAddServer()           ← 把服务实现绑定到服务器
        ↓
s.Serve(lis)                 ← 开始接收请求（阻塞）
```

---

### 1.6 客户端（addsvc-cli/main.go）

```go
func sum() {
	// ① 连接服务器
	conn, err := grpc.Dial("localhost:50051", grpc.WithTransportCredentials(insecure.NewCredentials()))
	defer conn.Close()

	// ② 创建客户端
	client := proto.NewAddClient(conn)
	ctx := context.Background()

	// ③ 构造请求
	in := &proto.SumRequest{A: 11, B: 12}

	// ④ 调用远程方法
	res, err := client.Sum(ctx, in)
	fmt.Println(res)  // v:23
}
```

**调用流程**：
```
grpc.Dial("localhost:50051")  ← 建立 TCP 连接
        ↓
proto.NewAddClient(conn)      ← 创建 gRPC 客户端
        ↓
client.Sum(ctx, in)          ← 调用远程方法
        ↓
返回 SumReply{V: 23}         ← 得到结果
```

---

### 1.7 bak 版本总结

```
┌─────────────────────────────────────────────────────────────────┐
│                     bak 版本：极简微服务架构                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  架构：                                                          │
│  CLI ── gRPC ──▶ Server ──▶ bus (业务函数)                      │
│                                                                  │
│  特点：                                                          │
│  • 业务代码极其简洁（bus.go 就是数学函数）                        │
│  • 无任何外部依赖（无 DB、无缓存、无链路追踪）                    │
│  • 两个服务完全独立，不知道对方存在                               │
│  • 没有分布式概念，只是两个独立的 RPC 服务                        │
│                                                                  │
│  问题：                                                          │
│  ❌ 如果服务变慢，不知道慢在哪里（是 Server 还是 bus？）          │
│  ❌ 如果调用失败，不知道是谁的错                                  │
│  ❌ 如果想统计调用次数，需要自己写代码                             │
│  ❌ 如果有 10 个服务，无法串联成一个请求的完整链路                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 第二部分：一步步演进成分布式链路追踪

现在我们从 bak 版本开始，一步步加入链路追踪功能，最终演变成主版本的完整架构。

---

### 演进第一步：引入单机追踪（trace-basic）

**问题**：我们想知道 `Sum` 函数执行了多久，`Concat` 函数执行了多久。

**解决方案**：给每个函数调用创建 Span，记录执行时间。

#### 演进 1.0 → 1.1：加追踪（破坏性修改）

```go
// ❌ 演进前：直接调用
func Sum(a, b int64) int64 {
	return a + b
}

// ✅ 演进后：加上追踪
func Sum(ctx context.Context, a, b int64) int64 {
	_, span := tracer.Start(ctx, "Sum")
	defer span.End()
	return a + b
}
```

**代价**：
- 函数签名变了：`Sum(a, b)` → `Sum(ctx, a, b)`
- 所有调用方都要改：传入 ctx
- bus 包从"纯业务"变成了"有追踪的业务"

**这是不好的做法**，因为业务代码被污染了。

---

#### 演进 1.2：中间件模式（不污染业务）

**解决方案**：不修改 bus.go，而是用装饰器包裹它。

```go
// 定义接口（抽象）
type Bus interface {
	Sum(ctx context.Context, a, b int64) int64
	Concat(ctx context.Context, a, b string) string
}

// 原始业务（不包含追踪）
type busImpl struct{}
func (busImpl) Sum(ctx context.Context, a, b int64) int64 {
	return a + b
}

// 追踪中间件（包裹业务）
type traceBus struct {
	tracer trace.Tracer
	Next   Bus  // 指向真正的业务实现
}
func (traceBus) Sum(ctx context.Context, a, b int64) int64 {
	_, span := bus.tracer.Start(ctx, "Sum")
	defer span.End()
	return bus.Next.Sum(ctx, a, b)  // 调用真正的业务
}

// 组装：原始业务被追踪中间件包裹
bus := busImpl{}
bus = traceBus{tracer: tracer, Next: bus}
```

**好处**：
- bus.go 保持纯净，不用修改
- 追踪逻辑在中间件中，随时可以添加/移除
- 可以组合多个中间件（追踪 + 指标 + 日志）

---

### 演进第二步：初始化链路追踪（trace-basic 的 initProvider）

**问题**：有了追踪代码，但 Span 数据存在内存里，怎么发送到 Jaeger？

**解决方案**：初始化 TracerProvider，配置 Exporter。

```go
func initProvider(endpoint string) func(ctx context.Context) error {
	ctx := context.Background()

	// ① 创建资源（服务标识）
	res, _ := resource.New(ctx,
		resource.WithAttributes(
			semconv.ServiceName("add-service"),
			semconv.ServiceVersion("1.0.0"),
		),
	)

	// ② 创建 Exporter（发送到哪里）
	conn, _ := grpc.DialContext(ctx, endpoint, ...)
	exporter, _ := otlptracegrpc.New(ctx, otlptracegrpc.WithGRPCConn(conn))

	// ③ 创建 TracerProvider
	provider := sdktrace.NewTracerProvider(
		sdktrace.WithSampler(sdktrace.AlwaysSample()),  // 100% 采样
		sdktrace.WithResource(res),
		sdktrace.WithSpanProcessor(
			sdktrace.NewBatchSpanProcessor(exporter),  // 批量发送
		),
	)

	// ④ 设置全局 Provider
	otel.SetTracerProvider(provider)

	return provider.Shutdown
}
```

**为什么需要这些步骤**：

| 步骤 | 作用 |
|---|---|
| Resource | 告诉后端"这条数据来自哪个服务" |
| Exporter | 负责把数据从内存发送到网络 |
| BatchSpanProcessor | 攒一批再发，减少网络 IO |
| SetTracerProvider | 设为全局，后续 `otel.Tracer()` 才能工作 |

---

### 演进第三步：跨服务传递（分布式链路）

**问题**：addsvc 调用 strsvc，但 Span 信息没有传递过去。在 Jaeger 上看到的是两条独立的链路，而不是一条完整的链路。

```
在 Jaeger 上看到的：
┌─────────────┐          ┌─────────────┐
│ addsvc.Sum  │          │ strsvc.Count│
│  Trace: A   │          │  Trace: B   │  ← 两个不同的 Trace
└─────────────┘          └─────────────┘
```

**我们想要的**：
```
在 Jaeger 上看到的：
┌──────────────────────────────┐
│ addsvc.Concat               │
│   ├── bus.Concat            │
│   ├── strsvc.Count          │  ← 全部在同一个 Trace 下
│   └── strsvc.Uppercase      │
└──────────────────────────────┘
```

**解决方案**：把 Trace 上下文（TraceID、SpanID）从 addsvc 传递给 strsvc。

---

#### 演进 3.1：定义传播器

```go
// 设置全局的 Propagator（传播器）
otel.SetTextMapPropagator(
	propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{},   // 传播 TraceID、SpanID
		propagation.Baggage{},       // 传播自定义数据
	),
)
```

**Propagator 的作用**：
- `TraceContext`：负责传播链路追踪的 ID（TraceID、SpanID）
- `Baggage`：负责传播自定义的业务数据

---

#### 演进 3.2：发送方注入（Inject）

在 addsvc-server 调用 strsvc 之前，把上下文注入到 gRPC Headers 中：

```go
func (s *addSvc) Concat(ctx context.Context, in *proto.ConcatRequest) (*proto.ConcatReply, error) {
	// ① 创建 Span（这会自动把 TraceID 放进 ctx）
	ctx, span := tracer.Start(ctx, "addsvc.Concat")
	defer span.End()

	// ② 把 ctx 中的 Trace 信息注入到 MapCarrier
	md := &propagation.MapCarrier{}
	propagator.Inject(ctx, md)

	// ③ 把 MapCarrier 塞进 gRPC 的 metadata
	ctx = metadata.NewOutgoingContext(ctx, metadata.New(*md))

	// ④ 调用下游服务（ctx 带着 Trace 信息）
	c := bus.Concat(ctx, in.A, in.B)
	res, _ := strClient.Count(ctx, countIn)

	return &proto.ConcatReply{V: res.V}, nil
}
```

**传播的数据是什么**：

```
HTTP Headers 中会增加：
traceparent: 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01
             │  │                            │                    │
             │  │                            │                    └── 采样标志
             │  │                            └──────────────────── Span ID
             │  └────────────────────────────────────────────── Trace ID
             └── 版本号
```

---

#### 演进 3.3：接收方提取（Extract）

在 strsvc-server 收到请求后，从 Headers 中提取 Trace 上下文：

```go
func (s *strSvc) Count(ctx context.Context, in *proto.CountRequest) (*proto.CountReply, error) {
	// ① 从 gRPC 请求中取出 metadata
	md, _ := metadata.FromIncomingContext(ctx)

	// ② 转成 Propagator 认识的 MapCarrier
	mp := &propagation.MapCarrier{}
	for key, value := range md {
		mp[key] = value[0]
	}

	// ③ 从 MapCarrier 中提取 Trace 上下文
	ctx = propagator.Extract(ctx, mp)

	// ④ 创建子 Span（自动关联到父 Span）
	ctx, span := tracer.Start(ctx, "strsvc.Count")
	defer span.End()

	count := bus.Count(ctx, in.Str)
	return &proto.CountReply{V: count}, nil
}
```

**为什么能自动关联**：
- `propagator.Extract()` 把 traceparent 中的 TraceID、SpanID 还原到 ctx
- `tracer.Start(ctx, "strsvc.Count")` 从 ctx 中读取父 SpanID
- 新 Span 的 parent_id 自动设为父 SpanID
- 最终在 Jaeger 上显示为树形结构

---

### 演进第四步：Baggage 跨服务传递

**问题**：addsvc 想知道请求的发起人是谁，想把这个信息传给所有下游服务。

**传统方式**：每个调用都手动传递。

```go
// ❌ 不好：每个接口都要加参数
type CountRequest struct {
	Str   string
	UserID string  // 手动加
}
```

**Baggage 方式**：存到上下文，自动传播。

#### 演进 4.1：创建和设置 Baggage

```go
func (s *addSvc) Concat(ctx context.Context, in *proto.ConcatRequest) (*proto.ConcatReply, error) {
	// ① 创建 Baggage
	b, _ := baggage.New()
	gender, _ := baggage.NewKeyValueProperty("gender", "1")
	author, _ := baggage.NewMember("author", "nick", gender)
	org, _ := baggage.NewMember("org", "0voice")
	b1, _ := baggage.New(author, org)

	// ② 把 Baggage 附加到上下文
	ctx = baggage.ContextWithBaggage(ctx, b1)

	// ③ 后续调用会自动传播 Baggage
	res, _ := strClient.Count(ctx, countIn)
}
```

#### 演进 4.2：接收方读取 Baggage

```go
func (s *strSvc) Uppercase(ctx context.Context, in *proto.UppercaseRequest) (*proto.UppercaseReply, error) {
	// ① 提取 Trace 上下文（Baggage 也一起提取）
	md, _ := metadata.FromIncomingContext(ctx)
	mp := &propagation.MapCarrier{}
	for key, value := range md {
		mp[key] = value[0]
	}
	ctx = propagator.Extract(ctx, mp)

	// ② 从上下文中读取 Baggage
	b := baggage.FromContext(ctx)

	// ③ 记录到 Span 属性中
	ctx, span := tracer.Start(ctx, "strsvc.Uppercase")
	defer span.End()
	span.SetAttributes(
		attribute.String("author", b.Member("author").Value()),  // "nick"
		attribute.String("org", b.Member("org").Value()),        // "0voice"
	)

	str := bus.Uppercase(ctx, in.Str)
	return &proto.UppercaseReply{V: str}, nil
}
```

**Baggage 的传播链路**：
```
addsvc.Concat                    strsvc.Uppercase
   │                                  │
   │ Baggage:                         │
   │   author="nick"                  │
   │   org="0voice"                   │
   │                                  │
   │ propagator.Inject()              │
   │        │                        │
   │        ▼                        │
   │   gRPC Headers                  │
   │   tracestate: author=nick,       │
   │            org=0voice           │
   │        │                        │
   │        ▼                        │
   │ propagator.Extract()             │
   │        │                        │
   │        ▼                        │
   │ baggage.FromContext()            │
   │        │                        │
   │        ▼                        │
   │ span.SetAttributes()             │
   │   author="nick"                 │  ✅ 自动收到
   │   org="0voice"                 │  ✅ 自动收到
```

---

### 演进第五步：添加指标监控（MetricMiddleware）

**问题**：我们想统计每个函数被调用了多少次，结果分布是什么样的。

**解决方案**：添加 MetricMiddleware。

```go
// 定义指标
meter := otel.Meter("addsvc")
sumCounter, _ := meter.Int64Counter("sum", api.WithDescription("累计调用次数"))
sumHistogram, _ := meter.Int64Histogram("sum_histogram", api.WithDescription("求和结果分布"))

// 创建指标中间件
type metricBus struct {
	sumCounter    metric.Int64Counter
	sumHistogram  metric.Int64Histogram
	Next          Bus
}

func (bus *metricBus) Sum(ctx context.Context, a, b int64) int64 {
	bus.sumCounter.Add(ctx, 1)              // 调用次数 +1
	c := bus.Next.Sum(ctx, a, b)           // 调用业务
	bus.sumHistogram.Record(ctx, c)         // 记录结果分布
	return c
}
```

---

### 演进第六步：组装所有中间件

**最终组装**：

```go
func getBus() Bus {
	// ① 最底层：原始业务
	b := bus.NewBus()

	// ② 包裹追踪中间件
	tracer := otel.Tracer("addsvc")
	b = bus.TracerMiddleware(b, tracer)

	// ③ 再包裹指标中间件
	meter := otel.Meter("addsvc")
	sumCounter, _ := meter.Int64Counter("sum", ...)
	sumHistogram, _ := meter.Int64Histogram("sum_histogram", ...)
	b = bus.MetricMiddleware(b, sumCounter, sumHistogram)

	return b
}
```

**调用链**：
```
调用方
    │
    ▼
MetricMiddleware.Sum()     ← 计数器 +1，记录直方图
    │
    ▼
TracerMiddleware.Sum()    ← 创建 Span，记录属性
    │
    ▼
busImpl.Sum()             ← 原始业务（不包含任何追踪代码）
```

---

## 第三部分：完整演进流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          演进流程总览                                        │
│                                                                          │
│  阶段1: 纯业务（bak 版本）                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │ bus.Sum(a, b) { return a + b }                                  │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│  问题: 不知道执行时间，不知道调用次数                                        │
│                                    │                                      │
│                                    ▼ 加上单机追踪                          │
│  阶段2: 单机追踪（trace-basic）                                           │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │ TracerMiddleware.Sum()                                          │     │
│  │   tracer.Start(ctx, "Sum")                                      │     │
│  │     bus.Sum(a, b)                                              │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│  问题: 跨服务调用时，Span 没有关联                                          │
│                                    │                                      │
│                                    ▼ 加上 Propagator                       │
│  阶段3: 分布式追踪（主版本 addsvc + strsvc）                              │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │ addsvc                          strsvc                          │     │
│  │   tracer.Start()                   tracer.Start()                  │     │
│  │   propagator.Inject()  ───────▶   propagator.Extract()           │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│  问题: 想传递业务数据，需要每个接口加参数                                     │
│                                    │                                      │
│                                    ▼ 加上 Baggage                          │
│  阶段4: 完整可观测性（主版本）                                             │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │ addsvc                          strsvc                          │     │
│  │   baggage 设置                     baggage 读取                    │     │
│  │   propagator.Inject()  ───────▶   propagator.Extract()           │     │
│  │   tracer.Start()         ───────▶   tracer.Start()                │     │
│  │   counter.Add()                    counter.Add()                  │     │
│  │   histogram.Record()               histogram.Record()             │     │
│  └─────────────────────────────────────────────────────────────────┘     │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 第四部分：各阶段代码对比

### 函数签名对比

```go
// 阶段1: 纯业务
func Sum(a, b int64) int64

// 阶段2-4: 有追踪（需要 ctx）
func Sum(ctx context.Context, a, b int64) int64
```

### 中间件链对比

```go
// 阶段2: 只有追踪
b = TracerMiddleware(b, tracer)

// 阶段3: 追踪 + 指标
b = MetricMiddleware(b, counter, histogram)
b = TracerMiddleware(b, tracer)

// 阶段4: 完整（顺序很重要）
b = MetricMiddleware(b, counter, histogram)  // 先（最外层）
b = TracerMiddleware(b, tracer)               // 后
```

### 服务启动对比

```go
// 阶段1-2: 只启动 gRPC
func main() {
	s := grpc.NewServer()
	proto.RegisterAddServer(s, server.NewAddSvc())
	s.Serve(lis)
}

// 阶段3-4: 启动 gRPC + OTEL
func main() {
	// 初始化链路追踪
	initTracerProvider(endpoint)
	// 初始化指标
	initMeterProvider(endpoint)
	// 启动 gRPC
	s := grpc.NewServer()
	proto.RegisterAddServer(s, server.NewAddSvc())
	s.Serve(lis)
}
```

---

## 总结

```
┌──────────────────────────────────────────────────────────────────────┐
│                       演进过程总结                                    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  第1步: 纯业务                                                       │
│  bus.go 是数学函数，无任何外部依赖                                     │
│                                                                       │
│  第2步: 单机追踪                                                      │
│  中间件包裹业务：TracerMiddleware → bus                               │
│  问题：跨服务时 Span 断开                                            │
│                                                                       │
│  第3步: 分布式追踪                                                    │
│  Propagator.Inject() → gRPC Headers → Propagator.Extract()           │
│  自动形成树形 Span 结构                                               │
│                                                                       │
│  第4步: Baggage 传播                                                  │
│  baggage.ContextWithBaggage() → propagator.Inject()                    │
│  baggage.FromContext() → propagator.Extract()                          │
│  自动跨服务传递业务数据                                                │
│                                                                       │
│  第5步: 指标监控                                                      │
│  MetricMiddleware → TracerMiddleware → bus                            │
│  计数器 + 直方图 + 追踪同时生效                                       │
│                                                                       │
│  关键设计：                                                           │
│  • 装饰器模式：不污染业务代码                                         │
│  • Propagator：统一抽象，不关心 HTTP 还是 gRPC                         │
│  • 中间件链顺序：Metric在外层，Tracer在内层，bus在最内层                │
└──────────────────────────────────────────────────────────────────────┘
```
