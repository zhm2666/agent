# otel-collector-config.yaml — OTEL Collector 配置详解

## 概述

OTEL Collector（OpenTelemetry Collector）是可观测性数据的**中间处理层**，位于应用程序和后端存储之间。

```
┌─────────────┐         ┌─────────────────────┐         ┌──────────────────┐
│  你的应用    │ ──────▶ │   OTEL Collector    │ ──────▶ │  后端存储         │
│ (服务导出)   │  OTLP   │  (收集/处理/转发)    │  OTLP   │ (Jaeger/Promo..) │
└─────────────┘         └─────────────────────┘         └──────────────────┘
                                    │
                                    │ 多种协议接收
                                    ▼
                         ┌─────────────────────┐
                         │ • otlp (:4317/4318) │
                         │ • jaeger (:14250)   │
                         │ • zipkin (:9411)    │
                         │ • prometheus (:8888)│
                         └─────────────────────┘
```

---

## 为什么需要 OTEL Collector？

### 问题 1：多语言、多协议的混乱

你有 Java、Go、Python 三种语言的服务，每种语言可能导出到不同的后端（Jaeger、Prometheus、Zipkin）。如果每个服务都直接连后端：

```
Java服务 → Jaeger
Go服务   → Prometheus
Python服务 → Zipkin
```

问题：
- 每个服务都要配置一套 exporter
- 协议不统一，难以聚合分析
- 后端地址变化时，所有服务都要改

### 问题 2：网络连接爆炸

如果有 100 个服务，每个服务都直连 Jaeger：

```
100 服务 × 1 连接/服务 = 100 个连接到 Jaeger
```

如果用 Collector：

```
100 服务 × 1 连接/Collector = 1 个连接到 Jaeger
```

### 问题 3：生产环境需要采样

线上流量大，不可能 100% 采集所有链路数据。Collector 可以统一做采样策略，而不需要每个服务单独配置。

### 问题 4：需要在发送前处理数据

- 过滤敏感信息（用户手机号、密码）
- 统一添加标签（如 `cluster`、`region`）
- 批量处理减少网络 IO

---

## 整体架构

```yaml
extensions:        # 扩展组件（非数据处理，提供辅助功能）
  health_check:   # 健康检查接口
  pprof:          # 性能分析接口
  zpages:         # 状态页接口

receivers:         # 接收器（入口，接收应用程序的数据）
  otlp:           # OpenTelemetry 标准协议
  jaeger:         # Jaeger 兼容协议
  zipkin:         # Zipkin 兼容协议
  prometheus:     # Prometheus 拉取

processors:        # 处理器（中间处理，过滤/转换/采样）
  batch:          # 批量处理
  memory_limiter: # 内存限制

exporters:        # 导出器（出口，发送到后端存储）
  otlp:           # 发送到另一个 Collector 或后端
  jaeger:         # 直接发送到 Jaeger
  prometheus:     # 暴露给 Prometheus 拉取

service:          # 服务配置（定义数据流水线）
  pipelines:       # 流水线配置
    traces:       # 链路追踪流水线
    metrics:      # 指标流水线
  extensions:     # 启用的扩展组件
```

---

## Extensions（扩展组件）

```yaml
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
  pprof:
    endpoint: 0.0.0.0:1777
  zpages:
    endpoint: 0.0.0.0:55679
```

### 为什么要用 Extension？

Extension 不处理 telemetry 数据（Trace、Metric），而是提供**运维辅助功能**。

| Extension | 端口 | 作用 | 访问方式 |
|---|---|---|---|
| `health_check` | `:13133` | 健康检查，用于 K8s liveness/readiness 探针 | `GET /` |
| `pprof` | `:1777` | Go 性能分析，排查 CPU/内存问题 | `GET /debug/pprof/` |
| `zpages` | `:55679` | OTEL Collector 内置状态页，查看队列情况 | `GET /debug/tracez` |

**为什么这样做**：
- K8s 需要 `/healthz` 端点来判断容器是否存活
- 性能问题时，pprof 可以 dump goroutine、heap 信息
- zpages 可以实时看到 Collector 内部状态

---

## Receivers（接收器）

接收器定义了 Collector 从哪里接收数据。

### 1. OTLP 接收器（推荐）

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317   # gRPC 接收地址
      http:
        endpoint: 0.0.0.0:4318   # HTTP 接收地址
```

**为什么要同时开启 gRPC 和 HTTP**：
- gRPC 更高效（Protobuf 序列化），适合内部网络
- HTTP 更通用，适合穿透防火墙、跨公网
- 应用程序可以选择用哪种

**端口选择惯例**：
```
OTLP gRPC:  4317
OTLP HTTP:  4318
```

### 2. Jaeger 接收器

```yaml
receivers:
  jaeger:
    protocols:
      grpc:
        endpoint: 0.0.0.0:14250
      thrift_binary:     # Jaeger Thrift 二进制协议
      thrift_compact:   # Jaeger Thrift 紧凑协议
      thrift_http:
        endpoint: 0.0.0.0:14268
```

**为什么 Jaeger 有多种协议**：
- Jaeger 支持多种老协议（为了兼容历史版本）
- `thrift_http` 是最常用的（兼容 Agent）
- `grpc` 是新版本推荐的

### 3. Zipkin 接收器

```yaml
receivers:
  zipkin:
    endpoint: 0.0.0.0:9411
```

**为什么保留 Zipkin 兼容**：
- 很多老系统使用 Zipkin
- Apache SkyWalking 等工具也兼容 Zipkin 协议

### 4. Prometheus 接收器

```yaml
receivers:
  prometheus:
    config:
      scrape_configs:
      - job_name: 'otel-collector'
        scrape_interval: 10s
        static_configs:
        - targets: ['localhost:8888']
  prometheus/cus:
    config:
      scrape_configs:
      - job_name: 'otel-collector-2'
        scrape_interval: 10s
        static_configs:
        - targets: ['192.168.2.207:2223']
```

**为什么 Prometheus 是拉模式（Receiver）**：
- Prometheus 的设计是**主动拉取**（Scrape），不是推送
- 所以 Prometheus 是 `receiver` 而不是 `exporter`
- Collector 相当于一个 Prometheus target，等待被拉取

**为什么要配置两个 prometheus**：
- `prometheus`：拉取 Collector 自己产生的内部指标（端口 8888）
- `prometheus/cus`：拉取你的应用产生的指标（端口 2223）
- 注意：`prometheus/cus` 的 targets 是 `192.168.2.207:2223`，说明应用独立暴露了 metrics 端点

---

## Processors（处理器）

处理器对数据进行中间处理，可以链式组合。

### 1. batch（批量处理器）

```yaml
processors:
  batch:
    # 每个批次中可包含的数据包数量
    send_batch_size: 8192
    # 超时时间，超过此时间立即发送
    timeout: 200ms
    # 每个批次中所有数据包的大小之和，0=不限制
    send_batch_max_size: 0
    # 按元数据键分组创建批处理器实例
    metadata_keys:
    - host.name
    - method
    # 元数据组合的最大数量
    metadata_cardinality_limit: 1000
```

**为什么要 batch 处理**：

```
Without Batch:
应用每产生 1 个 Span → 立即发送 1 次网络请求
10000 Span/秒 → 10000 网络请求/秒 ❌

With Batch (send_batch_size=8192):
应用产生 Span → 先攒到缓冲区
攒够 8192 个 OR 超过 200ms → 发送 1 次网络请求
10000 Span/秒 → 约 1-2 网络请求/秒 ✅
```

**为什么要 batch**：
- 减少网络 IO（一次发送大量数据 vs 多次发送少量数据）
- 减少后端压力（后端处理大块数据更高效）

**send_batch_max_size 的作用**：
- 控制单个批次最大多少条
- 防止一个批次太大导致传输超时
- 设为 0 表示不限制

**metadata_keys 的作用**：
- 按 `host.name`、`method` 等标签分组
- 不同组合的数据进入不同的批次
- 好处：同组的Span聚合在一起，便于分析
- 风险：组合太多会消耗大量内存（`metadata_cardinality_limit: 1000` 限制）

### 2. memory_limiter（内存限制器）

```yaml
processors:
  memory_limiter:
    # 内存检查间隔
    check_interval: 1s
    # 硬限制（MiB），超过后拒绝数据
    limit_mib: 500
    # 峰值预留（MiB），允许短时间超过此值
    spike_limit_mib: 100
    # 按百分比限制（优先使用固定值）
    limit_percentage: 0
    spike_limit_percentage: 0
```

**为什么要限制内存**：

```
Collector 收到数据 → 放入缓冲区 → 处理 → 发送

问题：如果数据量突然暴增（流量突增、DDOS、后端故障导致积压）
→ 缓冲区越来越大
→ 内存越来越大
→ OOM 被杀死
```

**软限制 vs 硬限制**：
```
硬限制 (limit_mib) = 500 MiB
软限制 = limit_mib - spike_limit_mib = 500 - 100 = 400 MiB

正常情况：
内存 < 400 MiB → 完全正常，不拒绝任何数据

接近软限制：
400 MiB < 内存 < 500 MiB → 开始丢弃部分数据（采样）

超过硬限制：
内存 > 500 MiB → 拒绝所有新数据，等待缓冲区消化
```

**为什么要预留 spike_limit_mib**：
- 内存使用是波动的
- 预留 100 MiB 的"弹性空间"，允许短暂超过 400 MiB
- 避免正常波动时误触发拒绝

**spike_limit 建议值**：
- 官方建议：约等于 `limit_mib` 的 20%
- 本配置：`100 / 500 = 20%`

**为什么不直接限制死**：
- 纯采样会丢失重要数据
- 软限制策略：优先保证数据不丢失太多，只有真正内存不够时才拒绝

---

## Exporters（导出器）

导出器负责把数据发送到后端存储。

### 1. OTLP 导出器

```yaml
exporters:
  otlp:
    endpoint: 192.168.239.154:4317
    tls:
      insecure: true
```

**为什么要用 OTLP 导出**：
- 发送给另一个 OTEL Collector（多级架构）
- 或者直接发送给支持 OTLP 的后端（如 Jaeger、Prometheus 的新版本）

**为什么用 `insecure: true`**：
- 本地开发/内网环境不需要 TLS
- 生产环境应改为证书配置：

```yaml
exporters:
  otlp:
    endpoint: 192.168.239.154:4317
    tls:
      insecure: false
      cert_file: /path/to/cert.pem
      key_file: /path/to/cert-key.pem
```

### 2. OTLP HTTP 导出器

```yaml
exporters:
  otlphttp:
    endpoint: http://192.168.239.154:4318
```

**为什么单独配置 HTTP 导出**：
- 有些环境只允许 HTTP（公网、防火墙）
- HTTP 比 gRPC 更通用

### 3. Jaeger 导出器

```yaml
exporters:
  jaeger:
    endpoint: 192.168.239.154:14250
    tls:
      insecure: true
```

**为什么 Jaeger 导出和 Jaeger 接收要区分**：
- `receivers.jaeger`：接收应用程序直接发来的 Jaeger 协议数据
- `exporters.jaeger`：把 Collector 处理后的数据发给 Jaeger
- 两者是**独立的**，Collector 可以同时是 Jaeger 的客户端和服务端

### 4. Zipkin 导出器

```yaml
exporters:
  zipkin:
    endpoint: http://192.168.239.154:9411/api/v2/spans
```

**注意**：Zipkin 的 endpoint 要包含完整路径 `/api/v2/spans`，这和 Jaeger 不同。

### 5. Prometheus 导出器

```yaml
exporters:
  prometheus:
    endpoint: 0.0.0.0:8889
    namespace: default
```

**为什么 Prometheus 是 exporter 而不是 receiver**：
- Collector 把 metrics 数据暴露在 `:8889/metrics`
- Prometheus server 主动来拉取（scrape）
- 所以 Collector 在这里扮演的是"被 Prometheus 拉取的目标"

---

## Service（服务配置）

```yaml
service:
  pipelines:
    traces:
      receivers: [otlp, jaeger, zipkin]
      processors: [memory_limiter, batch]
      exporters: [otlp]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus]
  extensions: [health_check, pprof, zpages]
```

### Pipeline（流水线）

Pipeline 定义了完整的数据处理路径：

```
receivers → processors → exporters
   │              │           │
   入口           处理         出口
```

**为什么叫"流水线"**：
- 数据像工厂流水线一样经过多个工序
- 每个工序（processor）可以单独配置
- 可以有多条流水线同时工作（traces、metrics）

### traces 流水线

```yaml
pipelines:
  traces:
    receivers: [otlp, jaeger, zipkin]   # 接收来源
    processors: [memory_limiter, batch]  # 处理顺序
    exporters: [otlp]                    # 发送到后端
```

**数据流向**：
```
应用 (OTLP) ──┐
应用 (Jaeger) ─┼──▶ Collector ──▶ 192.168.239.154:4317
应用 (Zipkin) ─┘
```

**为什么 receivers 接收多种协议**：
- 老系统可能用 Jaeger Agent
- 新系统用 OTLP
- Zipkin 兼容其他系统
- Collector 统一接收，转换成同一种格式输出

### metrics 流水线

```yaml
pipelines:
  metrics:
    receivers: [otlp]
    processors: [memory_limiter, batch]
    exporters: [prometheus]
```

**为什么 metrics 用 Prometheus exporter**：
- metrics 数据被暴露在 `:8889`
- Prometheus server 从 `:8889` 拉取
- 最终在 Prometheus/Grafana 中查看

**为什么 metrics 不导出到 `192.168.239.154:4317`**：
- Jaeger 主要用于 traces，不擅长 metrics 存储
- metrics 通常用 Prometheus/Grafana 生态
- 本配置让 traces 和 metrics 分流到不同后端

### extensions 配置

```yaml
service:
  extensions: [health_check, pprof, zpages]
```

**为什么要显式配置 extensions**：
- Extension 不参与数据流水线
- 需要单独声明启用
- 健康检查、pprof 等是运维相关的，和数据处理无关

---

## 完整数据流向图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              应用程序                                      │
│                                                                          │
│  Go服务 (OTLP :4317) ──────────────────────────────────────────────────┐  │
│  Java服务 (Jaeger :14268) ─────────────────────────────────────────────┤  │
│  Python服务 (Zipkin :9411) ────────────────────────────────────────────┤  │
│  Go服务 (Prometheus :2223) ────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┬──────┘
                                                                         │
                                    ▼                                      │
┌────────────────────────────────────────────────────────────────────┐      │
│                          OTEL Collector                             │      │
│                                                                    │      │
│  Receivers (接收):                                                  │      │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                   │      │
│  │   OTLP   │ │  Jaeger  │ │  Zipkin  │ │Prometheus│                   │      │
│  │  :4317   │ │ :14268  │ │  :9411  │ │  :2223   │                   │      │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘                   │      │
│       │           │            │           │                         │      │
│       └───────────┴───────────┬┴───────────┘                         │      │
│                               ▼                                        │      │
│  Processors (处理):                                                      │      │
│  ┌──────────────────┐  ┌──────────────────┐                        │      │
│  │ memory_limiter    │→ │      batch        │                        │      │
│  │ • 检查内存         │  │ • 攒够8192条      │                        │      │
│  │ • 超过500MB拒绝   │  │ • 超过200ms发送   │                        │      │
│  └──────────────────┘  └────────┬─────────┘                        │      │
│                                │                                     │      │
│  Exporters (导出):             │                                     │      │
│  ┌─────────┐ ┌─────────┐     │                                     │      │
│  │   OTLP   │ │Prometheus│◀────┘                                     │      │
│  │  :4317   │ │  :8889   │                                           │      │
│  └────┬────┘ └────┬────┘                                            │      │
│       │           │                                                 │      │
└───────┼───────────┼─────────────────────────────────────────────────┼──────┘
        │           │
        ▼           ▼
┌──────────────┐  ┌──────────────────────┐
│ Jaeger UI     │  │ Prometheus Server   │
│ Grafana       │  │ (从 :8889 拉取)      │
│ (查链路追踪)   │  │ (查指标数据)         │
└──────────────┘  └──────────────────────┘

Extensions:
┌──────────────┐  ┌──────────────────────┐  ┌──────────────────┐
│ health_check  │  │       pprof           │  │      zpages      │
│  :13133/health │  │     :1777/pprof      │  │   :55679/tracez  │
│ (K8s探针)      │  │ (Go性能分析)         │  │ (Collector状态)   │
└──────────────┘  └──────────────────────┘  └──────────────────┘
```

---

## 生产环境建议配置

### 配置项调整

```yaml
# 采样策略（生产环境不要 100% 采样）
processors:
  memory_limiter:
    limit_mib: 1000          # 生产环境可以更大
    spike_limit_mib: 200

# TLS 加密
exporters:
  otlp:
    endpoint: otel-backend.company.com:4317
    tls:
      insecure: false
      cert_file: /etc/otel/cert.pem
      key_file: /etc/otel/cert-key.pem

# 健康检查（生产必须开启）
extensions:
  health_check:
    endpoint: 0.0.0.0:13133
    check_collector_pipeline: true  # 检查流水线状态

service:
  extensions: [health_check]
```

### 为什么不建议直连 Jaeger

```
开发/测试:
应用 ──────────────▶ Jaeger

生产（有 Collector）:
应用 ──▶ Collector ──▶ Jaeger
         │
         ├──▶ Prometheus (metrics)
         │
         └──▶ Grafana (dashboards)
```

**Collector 的额外价值**：
- 统一采样策略（尾部采样：只保留错误/慢请求）
- 聚合多语言数据
- 提供 metrics（Grafana 看板）
- 负载均衡（多个 Collector 实例）

---

## 快速验证

### 1. 启动 Collector

```bash
# 安装 otelcol
brew install otelcol  # macOS
# 或从 https://github.com/open-telemetry/opentelemetry-collector-releases/releases 下载

# 启动（指定配置文件）
otelcol --config=otel-collector-config.yaml
```

### 2. 检查健康状态

```bash
curl http://localhost:13133/
# 输出: {"status":"Server available","upSince":"2026-06-27T10:00:00Z","version":"0.80.0"}
```

### 3. 检查 Prometheus metrics

```bash
curl http://localhost:8889/metrics | head -20
# 输出 Collector 自身的指标：
# otelcol_exporter_send_success{...} 12345
# otelcol_processor_batch_batch_size{...} 2048
```

### 4. 查看 zpages

```bash
# 查看 traces 相关的内部状态
curl http://localhost:55679/tracez
```

---

## 总结

```
┌──────────────────────────────────────────────────────────────────────┐
│                    OTEL Collector 配置核心知识点                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  为什么需要 Collector：                                               │
│  - 统一多协议接收（OTLP/Jaeger/Zipkin）                              │
│  - 减少网络连接（100服务→1连接）                                       │
│  - 统一采样和处理                                                     │
│  - 提供 metrics（自己监控自己）                                        │
│                                                                       │
│  四大组件：                                                           │
│  ┌──────────────┬──────────────────────────────────────────────┐   │
│  │ Extensions     │ 运维辅助（健康检查、pprof、zpages）          │   │
│  │ Receivers      │ 数据入口（OTLP、Jaeger、Zipkin、Prometheus） │   │
│  │ Processors     │ 数据处理（批量、内存限制、采样）              │   │
│  │ Exporters      │ 数据出口（OTLP、Jaeger、Prometheus）         │   │
│  └──────────────┴──────────────────────────────────────────────┘   │
│                                                                       │
│  Pipeline = Receivers → Processors → Exporters                       │
│                                                                       │
│  Extensions vs Data Pipeline：                                         │
│  - Data Pipeline：处理 Traces/Metrics                                 │
│  - Extensions：提供运维功能，不处理数据                                 │
│                                                                       │
│  memory_limiter:                                                      │
│  - 硬限制 = 500MB（超过拒绝数据）                                      │
│  - 软限制 = 400MB（接近开始丢弃）                                      │
│  - spike_limit = 100MB（允许短暂波动）                                 │
│                                                                       │
│  batch:                                                               │
│  - send_batch_size = 8192（攒够发送）                                 │
│  - timeout = 200ms（超时强制发送）                                     │
└──────────────────────────────────────────────────────────────────────┘
```
