# gRPC 完整指南：从 Proto 定义到分布式调用

> 本文档详细讲解 gRPC 的使用方法，基于 `addsvc` 和 `strsvc` 项目。涵盖 Proto 编写、代码生成、服务端实现、客户端调用、拦截器、中间件等核心概念。

---

## 目录

1. [gRPC 是什么](#1-grpc-是什么)
2. [Proto 文件编写](#2-proto-文件编写)
3. [代码生成](#3-代码生成)
4. [服务端实现](#4-服务端实现)
5. [客户端调用](#5-客户端调用)
6. [完整调用流程](#6-完整调用流程)
7. [进阶用法](#7-进阶用法)

---

## 1. gRPC 是什么

gRPC 是 Google 开发的**高性能、开源**的远程过程调用（RPC）框架。

### 1.1 对比传统 HTTP API

| 维度 | HTTP REST API | gRPC |
|---|---|---|
| 协议 | HTTP/1.1 或 HTTP/2 | HTTP/2（强制） |
| 数据格式 | JSON / XML | **Protocol Buffers**（二进制） |
| 接口定义 | 无标准（OpenAPI可选） | **必须写 .proto** |
| 代码生成 | 可选（Swagger） | **自动生成**（proto 文件） |
| 流式支持 | 需额外实现 | **原生支持**（服务端/客户端/双向） |
| 性能 | 较慢（文本解析） | 快（Protobuf 二进制） |
| 适用场景 | 浏览器/移动端 | **服务间通信** |

### 1.2 为什么选 gRPC

```
浏览器/移动端 ──▶ REST API ──▶ API Gateway ──▶ 内部服务 ──▶ 数据库
                                       ↑
                                  gRPC 推荐用这里
```

**gRPC 的优势**：
- **性能高**：二进制序列化，比 JSON 快 5-10 倍
- **类型安全**：Proto 定义强类型，编译期检查
- **多语言支持**：自动生成各语言客户端
- **流式通信**：支持服务端流、客户端流、双向流
- **双向心跳**：HTTP/2 支持连接复用

### 1.3 本项目的架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           gRPC 服务调用架构                                  │
│                                                                          │
│  addsvc-cli (客户端)                                                       │
│       │                                                                   │
│       │ grpc.Dial("localhost:50051")                                     │
│       │ proto.NewAddClient(conn)                                          │
│       │ client.Sum(ctx, req)                                             │
│       ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    addsvc-server (:50051)                        │   │
│  │                                                                  │   │
│  │  server.go:                                                       │   │
│  │    func (s *addSvc) Sum(ctx, req) (*res, err)                   │   │
│  │      │                                                           │   │
│  │      ▼                                                           │   │
│  │    bus.Sum(ctx, a, b)                                            │   │
│  │                                                                  │   │
│  │  server.go:                                                       │   │
│  │    func (s *addSvc) Concat(ctx, req) (*res, err)                │   │
│  │      │                                                           │   │
│  │      ▼                                                           │   │
│  │    bus.Concat(ctx, a, b)  ──▶  strsvc-server (:50052)          │   │
│  │                              grpc.Dial("localhost:50052")         │   │
│  │                              client.Count(ctx, req)               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Proto 文件编写

Proto（Protocol Buffers）是 gRPC 的接口定义语言（IDL）。

### 2.1 Proto 文件结构

```protobuf
// 1. 语法声明（必须第一行）
syntax = "proto3";

// 2. 包名（用于避免命名冲突）
package addsvc;

// 3. Go 包路径（生成代码放到哪里）
option go_package = "addsvc/proto";

// 4. 消息定义（类似 struct）
message SumRequest {
  int64 a = 1;  // 字段序号
  int64 b = 2;
}
message SumReply {
  int64 v = 1;
}

// 5. 服务定义（类似 interface）
service Add {
  rpc Sum (SumRequest) returns (SumReply) {}
}
```

### 2.2 消息类型详解

#### 基本字段类型

| Proto 类型 | Go 类型 | 说明 |
|---|---|---|
| `int32` | `int32` | 有符号 32 位整数 |
| `int64` | `int64` | 有符号 64 位整数 |
| `uint32` | `uint32` | 无符号 32 位整数 |
| `uint64` | `uint64` | 无符号 64 位整数 |
| `float` | `float32` | 32 位浮点数 |
| `double` | `float64` | 64 位浮点数 |
| `bool` | `bool` | 布尔值 |
| `string` | `string` | 字符串 |
| `bytes` | `[]byte` | 字节数组 |

#### 字段序号

```protobuf
// 字段序号（Tag）
message User {
  int32 id = 1;      // 必须从 1 开始
  string name = 2;   // 不能重复
  int64 age = 3;     // 最大 536,870,911（2^29 - 1）
  // 19000-19999 保留给 gRPC 内部使用
}
```

**重要规则**：
- 序号一旦使用，**不能更改**（否则数据格式不兼容）
- 推荐预留一些序号给未来扩展：`reserved 10, 11, 12;`

#### 字段修饰符

```protobuf
message Request {
  // 普通字段
  string name = 1;

  // repeated：可重复（类似 slice）
  repeated int32 scores = 2;  // → []int32

  // map：键值对
  map<string, int32> ages = 3;  // → map[string]int32

  // 嵌套消息
  message Phone {
    string number = 1;
  }
  Phone phone = 4;
}
```

### 2.3 服务定义详解

#### 普通 RPC（Unary）

```protobuf
// 客户端发一个请求，服务端返回一个响应
service Add {
  rpc Sum (SumRequest) returns (SumReply) {}
}
```

```
Client ────────────────────────────────▶ Server
        SumRequest {a:1, b:2}
              ───────────────────────────────▶
                                         [处理]
              ◀───────────────────────────────
              SumReply {v:3}
```

#### 服务端流式 RPC

```protobuf
service StreamService {
  // 服务端返回多个响应
  rpc StreamFromServer(Request) returns (stream Response) {}
}
```

```
Client ────────────────────────────────▶ Server
        Request
              ───────────────────────────────▶
              ◀───────────────────────────────
              Response 1
              ◀───────────────────────────────
              Response 2
              ◀───────────────────────────────
              Response 3
              ...
```

#### 客户端流式 RPC

```protobuf
service StreamService {
  // 客户端发送多个请求，服务端返回一个响应
  rpc StreamFromClient(stream Request) returns (Response) {}
}
```

```
Client ────────────────────────────────▶ Server
        Request 1
              ────────────────────────────────▶
        Request 2
              ────────────────────────────────▶
        Request 3
              ────────────────────────────────▶
                                         [处理]
              ◀───────────────────────────────
              Response
```

#### 双向流式 RPC

```protobuf
service StreamService {
  // 双方都可以发送多个消息
  rpc StreamBidirectional(stream Request) returns (stream Response) {}
}
```

```
Client ────────────────────────────────▶ Server
        Request 1 ──────────────────────────▶
        Request 2 ──────────────────────────▶
              ◀───────────────────────────────
              Response 1
        Request 3 ──────────────────────────▶
              ◀───────────────────────────────
              Response 2
              ...
```

### 2.4 完整 Proto 示例

#### addsvc 的 Proto（addsvc/proto/addsvc.proto）

```protobuf
syntax = "proto3";
package addsvc;
option go_package = "addsvc/proto";

// ========== 消息定义 ==========

// 两数相加请求
message SumRequest {
  int64 a = 1;  // 第一个数
  int64 b = 2;  // 第二个数
}
message SumReply {
  int64 v = 1;  // 结果
}

// 字符串拼接请求
message ConcatRequest {
  string a = 1;  // 第一个字符串
  string b = 2;  // 第二个字符串
}
message ConcatReply {
  string v = 1;  // 拼接结果
}

// ========== 服务定义 ==========

// 加法服务
service Add {
  // RPC 方法：两数相加
  rpc Sum (SumRequest) returns (SumReply) {}

  // RPC 方法：字符串拼接（调用下游服务 strsvc）
  rpc Concat (ConcatRequest) returns (ConcatReply) {}
}
```

#### strsvc 的 Proto（strsvc/proto/strsvc.proto）

```protobuf
syntax = "proto3";
package strsvc;
option go_package = "strsvc/proto";

// ========== 消息定义 ==========

// 字符串长度请求
message CountRequest {
  string str = 1;  // 待计数的字符串
}
message CountReply {
  int64 v = 1;     // 字符长度
}

// 转大写请求
message UppercaseRequest {
  string str = 1;  // 待转换的字符串
}
message UppercaseReply {
  string v = 1;     // 转换后的字符串
}

// ========== 服务定义 ==========

// 字符串处理服务
service Str {
  // RPC 方法：计算字符串长度
  rpc Count (CountRequest) returns (CountReply) {}

  // RPC 方法：转大写
  rpc Uppercase (UppercaseRequest) returns (UppercaseReply) {}
}
```

---

## 3. 代码生成

### 3.1 安装 protoc

```bash
# macOS
brew install protobuf

# Linux
apt install protobuf-compiler

# Windows
# 从 https://github.com/protocolbuffers/protobuf/releases 下载 protoc.exe
```

### 3.2 安装 Go 插件

```bash
# 安装 protoc-gen-go（生成消息类型代码）
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest

# 安装 protoc-gen-go-grpc（生成 gRPC 代码）
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# 确保 PATH 包含 $GOPATH/bin
export PATH=$PATH:$(go env GOPATH)/bin
```

### 3.3 生成代码

```bash
# 进入项目目录
cd /path/to/addsvc

# 生成消息类型代码（*.pb.go）
protoc --go_out . --go_opt paths=source_relative proto/addsvc.proto

# 生成 gRPC 代码（*_grpc.pb.go）
protoc --go-grpc_out . --go-grpc_opt paths=source_relative proto/addsvc.proto
```

### 3.4 参数说明

| 参数 | 作用 |
|---|---|
| `--go_out=.` | 生成 Go 代码到当前目录 |
| `--go_opt paths=source_relative` | 按 proto 文件相对路径生成（保持目录结构） |
| `--go-grpc_out=.` | 生成 gRPC 代码到当前目录 |
| `--go-grpc_opt paths=source_relative` | 同上 |

### 3.5 生成的文件

```
addsvc/
├── proto/
│   ├── addsvc.proto           ← 原始定义
│   ├── addsvc.pb.go          ← 消息类型代码（SumRequest, SumReply 等）
│   └── addsvc_grpc.pb.go     ← gRPC 代码（AddClient, AddServer 等）
```

### 3.6 生成的代码解析

#### addsvc.pb.go（消息类型）

```go
// SumRequest 自动生成为结构体
type SumRequest struct {
	A int64 `protobuf:"varint,1,opt,name=a,proto3" json:"a,omitempty"`
	B int64 `protobuf:"varint,2,opt,name=b,proto3" json:"b,omitempty"`
}

// SumReply 自动生成为结构体
type SumReply struct {
	V int64 `protobuf:"varint,1,opt,name=v,proto3" json:"v,omitempty"`
}
```

#### addsvc_grpc.pb.go（gRPC 代码）

```go
// 服务端接口（需要我们实现）
type AddServer interface {
	Sum(context.Context, *SumRequest) (*SumReply, error)
	Concat(context.Context, *ConcatRequest) (*ConcatReply, error)
	mustEmbedUnimplementedAddServer()
}

// 客户端接口（供调用方使用）
type AddClient interface {
	Sum(ctx context.Context, in *SumRequest, opts ...grpc.CallOption) (*SumReply, error)
	Concat(ctx context.Context, in *ConcatRequest, opts ...grpc.CallOption) (*ConcatReply, error)
}

// 客户端结构体
type addClient struct {
	cc *grpc.ClientConn  // 底层连接
}

// 创建客户端
func NewAddClient(cc *grpc.ClientConn) AddClient {
	return &addClient{cc}
}
```

---

## 4. 服务端实现

### 4.1 服务端结构

```go
// 1. 定义服务结构体（必须嵌入 UnimplementedAddServer）
type addSvc struct {
	proto.UnimplementedAddServer  // 必须！gRPC 版本兼容用
}

// 2. 创建服务实例的工厂函数
func NewAddSvc(...) proto.AddServer {
	return &addSvc{...}
}

// 3. 实现 RPC 方法
func (s *addSvc) Sum(ctx context.Context, req *proto.SumRequest) (*proto.SumReply, error) {
	// 处理请求
	result := req.A + req.B
	return &proto.SumReply{V: result}, nil
}
```

### 4.2 服务启动流程

```go
func main() {
	// ① 监听 TCP 端口
	lis, err := net.Listen("tcp", ":50051")

	// ② 创建 gRPC Server
	s := grpc.NewServer()

	// ③ 注册服务实现
	proto.RegisterAddServer(s, server.NewAddSvc(...))

	// ④ 启动服务（阻塞）
	s.Serve(lis)
}
```

**启动流程图**：

```
┌─────────────────────────────────────────────────────────────────┐
│                        main()                                   │
│                                                                  │
│  net.Listen("tcp", ":50051")                                    │
│       │                                                          │
│       │  告诉操作系统：打开端口 50051，准备接收连接                │
│       ▼                                                          │
│  ┌─────────────────┐                                           │
│  │  TCP Socket     │                                           │
│  │  状态: LISTEN   │                                           │
│  │  端口: 50051    │                                           │
│  └────────┬────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  grpc.NewServer()                                               │
│       │                                                          │
│       │  创建 gRPC Server，但还没有绑定任何服务                   │
│       ▼                                                          │
│  ┌─────────────────┐                                           │
│  │  gRPC Server    │                                           │
│  │  services: []    │                                           │
│  └────────┬────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  RegisterAddServer(s, NewAddSvc())                             │
│       │                                                          │
│       │  把服务实现绑定到 gRPC Server                            │
│       ▼                                                          │
│  ┌─────────────────┐                                           │
│  │  gRPC Server    │                                           │
│  │  services: [Add]│                                           │
│  └────────┬────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  s.Serve(lis)                                                   │
│       │                                                          │
│       │  阻塞！开始接收请求并分发到对应的服务                     │
│       ▼                                                          │
│  客户端请求 ──▶ 分发到 Add.Sum() 或 Add.Concat()                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 gRPC Server 选项

```go
// 创建 Server 时可以传入各种选项

// 1. 启用 TLS
creds, _ := credentials.NewServerTLSFromFile(certFile, keyFile)
s := grpc.NewServer(grpc.Creds(creds))

// 2. 设置最大接收/发送消息大小
s := grpc.NewServer(
	grpc.MaxRecvMsgSize(1024*1024*10),  // 最大接收 10MB
	grpc.MaxSendMsgSize(1024*1024*10), // 最大发送 10MB
)

// 3. 设置连接超时
s := grpc.NewServer(
	grpc.KeepaliveParams(keepalive.ServerParameters{
		MaxConnectionIdle: 5 * time.Minute,
		MaxConnectionAge: 2 * time.Hour,
	}),
)

// 4. 添加拦截器
s := grpc.NewServer(
	grpc.UnaryInterceptor(loggingInterceptor),
	grpc.StreamInterceptor(streamInterceptor),
)

// 5. 同时添加多个拦截器（链式）
s := grpc.NewServer(
	grpc.ChainUnaryInterceptor(
		loggingInterceptor,
		recoveryInterceptor,
		tracingInterceptor,
	),
)
```

### 4.4 服务方法实现

#### 简单 RPC

```go
// Sum：简单的加法，直接返回结果
func (s *addSvc) Sum(ctx context.Context, in *proto.SumRequest) (*proto.SumReply, error) {
	// ctx：包含请求的上下文（超时、取消信号等）
	// in：客户端发来的请求数据
	// 返回：响应数据和错误

	c := s.bus.Sum(ctx, in.A, in.B)
	return &proto.SumReply{
		V: c,
	}, nil
}
```

#### 调用下游服务

```go
// Concat：拼接字符串，并调用下游 strsvc
func (s *addSvc) Concat(ctx context.Context, in *proto.ConcatRequest) (*proto.ConcatReply, error) {
	// 1. 字符串拼接
	c := s.bus.Concat(ctx, in.A, in.B)

	// 2. 调用下游服务
	countIn := &strProto.CountRequest{Str: c}
	countRes, err := s.strClient.Count(ctx, countIn)
	if err != nil {
		return nil, err
	}

	// 3. 返回结果
	return &proto.ConcatReply{
		V: countRes.V,
	}, nil
}
```

### 4.5 错误处理

```go
func (s *addSvc) Sum(ctx context.Context, in *proto.SumRequest) (*proto.SumReply, error) {
	// 1. 正常返回（无错误）
	return &proto.SumReply{V: result}, nil

	// 2. 返回错误
	return nil, status.Errorf(codes.InvalidArgument, "参数错误: %v", err)

	// 3. 包装错误（保留堆栈）
	return nil, status.Errorf(codes.Internal, "内部错误: %v", err)
}
```

**gRPC 错误码**：

| Code | 说明 | 使用场景 |
|---|---|---|
| `OK` | 成功 | 无错误时 |
| `InvalidArgument` | 参数错误 | 输入验证失败 |
| `NotFound` | 资源不存在 | 查询不存在的 ID |
| `AlreadyExists` | 资源已存在 | 创建重复的唯一键 |
| `PermissionDenied` | 权限不足 | 未授权访问 |
| `Unauthenticated` | 未认证 | 登录失败 |
| `ResourceExhausted` | 资源耗尽 | 配额超限 |
| `Internal` | 内部错误 | 服务器异常 |

---

## 5. 客户端调用

### 5.1 客户端结构

```go
func main() {
	// 1. 连接服务器
	conn, err := grpc.Dial("localhost:50051", grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Fatal(err)
	}
	defer conn.Close()

	// 2. 创建客户端
	client := proto.NewAddClient(conn)

	// 3. 准备请求
	ctx := context.Background()
	req := &proto.SumRequest{A: 11, B: 12}

	// 4. 调用 RPC
	res, err := client.Sum(ctx, req)

	// 5. 处理响应
	fmt.Println(res.V)  // 输出: 23
}
```

### 5.2 连接选项

```go
// 1. 不使用 TLS（内网）
conn, err := grpc.Dial(
	"localhost:50051",
	grpc.WithTransportCredentials(insecure.NewCredentials()),
)

// 2. 使用 TLS
creds, err := credentials.NewClientTLSFromFile(caFile, serverNameOverride)
conn, err := grpc.Dial(
	"localhost:50051",
	grpc.WithTransportCredentials(creds),
)

// 3. 使用 Token 认证
conn, err := grpc.Dial(
	"localhost:50051",
	grpc.WithPerRPCCredentials(tokenAuth{
		token: "Bearer xxx",
	}),
)

// 4. 连接超时
conn, err := grpc.Dial(
	"localhost:50051",
	grpc.WithTransportCredentials(insecure.NewCredentials()),
	grpc.WithBlock(),           // 阻塞直到连接成功或超时
	grpc.WithTimeout(5*time.Second),
)

// 5. 非阻塞连接
conn, err := grpc.Dial(
	"localhost:50051",
	grpc.WithTransportCredentials(insecure.NewCredentials()),
	grpc.WithBlock(),  // 不加这个是非阻塞的
)
```

### 5.3 客户端调用流程图

```
┌─────────────────────────────────────────────────────────────────┐
│                      客户端调用流程                              │
│                                                                  │
│  grpc.Dial("localhost:50051")                                   │
│       │                                                          │
│       │  1. DNS 解析 "localhost" → 127.0.0.1                   │
│       │  2. TCP 连接到 :50051                                    │
│       │  3. HTTP/2 协议握手                                      │
│       ▼                                                          │
│  ┌─────────────────┐                                           │
│  │  grpc.ClientConn │  ← 底层连接，复用给所有 RPC                │
│  └────────┬────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  proto.NewAddClient(conn)                                       │
│       │                                                          │
│       │  创建一个轻量级客户端对象，持有连接引用                   │
│       ▼                                                          │
│  ┌─────────────────┐                                           │
│  │  proto.AddClient │  ← 实际调用时用的对象                     │
│  │  cc: *ClientConn │                                           │
│  └────────┬────────┘                                           │
│           │                                                      │
│           ▼                                                      │
│  client.Sum(ctx, req)                                           │
│       │                                                          │
│       │  1. Protobuf 序列化 req                                 │
│       │  2. HTTP/2 发送请求                                      │
│       │  3. 等待响应（或超时）                                   │
│       │  4. 反序列化响应                                        │
│       ▼                                                          │
│  res, err                                                       │
└─────────────────────────────────────────────────────────────────┘
```

### 5.4 完整调用示例

#### addsvc-cli/main.go

```go
package main

import (
	"context"
	"fmt"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	"log"
	"addsvc/proto"
)

func main() {
	sum()
	concat()
}

func sum() {
	// 1. 连接服务器
	conn, err := grpc.Dial(
		"localhost:50051",
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		log.Fatal(err)
	}
	defer conn.Close()

	// 2. 创建客户端
	client := proto.NewAddClient(conn)

	// 3. 构造请求
	ctx := context.Background()
	in := &proto.SumRequest{
		A: 11,
		B: 12,
	}

	// 4. 调用 RPC
	res, err := client.Sum(ctx, in)
	if err != nil {
		log.Println(err)
		return
	}

	// 5. 处理结果
	fmt.Println(res)  // 输出: v:23
}

func concat() {
	conn, err := grpc.Dial(
		"localhost:50051",
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil {
		log.Fatal(err)
	}
	defer conn.Close()

	client := proto.NewAddClient(conn)
	ctx := context.Background()
	in := &proto.ConcatRequest{
		A: "abcd",
		B: "efg",
	}

	res, err := client.Concat(ctx, in)
	if err != nil {
		log.Println(err)
		return
	}

	fmt.Println(res)  // 输出: v:ABCDEFG
}
```

### 5.5 带超时的调用

```go
func callWithTimeout() {
	// 1. 创建带超时的 Context
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()  // 重要：防止内存泄漏

	// 2. 连接服务器
	conn, err := grpc.Dial("localhost:50051", grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		log.Fatal(err)
	}
	defer conn.Close()

	// 3. 调用 RPC（超时会自动取消）
	client := proto.NewAddClient(conn)
	res, err := client.Sum(ctx, &proto.SumRequest{A: 1, B: 2})
	if err != nil {
		if ctx.Err() == context.DeadlineExceeded {
			fmt.Println("调用超时")
		} else {
			fmt.Printf("调用失败: %v", err)
		}
		return
	}

	fmt.Println(res)
}
```

### 5.6 客户端拦截器

```go
// 1. 定义拦截器
func loggingInterceptor(ctx context.Context, method string, req, reply interface{}, cc *grpc.ClientConn, invoker grpc.UnaryInvoker, opts ...grpc.CallOption) error {
	fmt.Printf("调用方法: %s\n", method)
	fmt.Printf("请求: %v\n", req)
	err := invoker(ctx, method, req, reply, cc, opts...)
	fmt.Printf("响应: %v, 错误: %v\n", reply, err)
	return err
}

// 2. 使用拦截器
conn, err := grpc.Dial(
	"localhost:50051",
	grpc.WithTransportCredentials(insecure.NewCredentials()),
	grpc.WithUnaryInterceptor(loggingInterceptor),  // 单次调用拦截
)

// 3. 链式拦截器
conn, err := grpc.Dial(
	"localhost:50051",
	grpc.WithTransportCredentials(insecure.NewCredentials()),
	grpc.WithChainUnaryInterceptor(
		loggingInterceptor,
		authInterceptor,
		recoveryInterceptor,
	),
)
```

---

## 6. 完整调用流程

### 6.1 单次 RPC 调用流程

```
┌─────────────────┐                           ┌─────────────────┐
│   addsvc-cli    │                           │ addsvc-server   │
│  (客户端)        │                           │  (服务端)        │
└────────┬────────┘                           └────────┬────────┘
         │                                             │
         │  1. grpc.Dial("localhost:50051")            │
         │     TCP 连接 + HTTP/2 握手                  │
         │ ─────────────────────────────────────────▶ │
         │                                             │
         │  2. proto.NewAddClient(conn)                │
         │     创建客户端对象                          │
         │                                             │
         │  3. client.Sum(ctx, req)                   │
         │     │                                      │
         │     │  req = SumRequest{A:11, B:12}        │
         │     │                                      │
         │     ▼                                      │
         │  序列化请求为 Protobuf 二进制               │
         │     │                                      │
         │     ▼                                      │
         │  HTTP/2 发送                               │
         │ ─────────────────────────────────────────▶ │
         │                                             │
         │              │                              │
         │              │  4. gRPC Server 接收请求      │
         │              │     反序列化                  │
         │              ▼                              │
         │         路由到 Sum() 方法                   │
         │              │                              │
         │              ▼                              │
         │         执行业务逻辑                        │
         │         bus.Sum(11, 12) = 23              │
         │              │                              │
         │              ▼                              │
         │         构造响应                            │
         │         res = SumReply{V:23}               │
         │                                             │
         │  响应: SumReply{V:23}                      │
         │ ◀───────────────────────────────────────── │
         │                                             │
         │  5. 反序列化响应                           │
         │     res.V = 23                             │
         │                                             │
         ▼                                             │
    处理结果                                            │
    fmt.Println(res.V)  // 23                          │
```

### 6.2 跨服务调用流程（分布式）

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         分布式 gRPC 调用流程                                  │
│                                                                          │
│  addsvc-cli                addsvc-server              strsvc-server         │
│      │                        │                          │               │
│      │ grpc.Dial(:50051)       │                          │               │
│      │ ───────────────────────▶│                          │               │
│      │                         │                          │               │
│      │ client.Sum()            │                          │               │
│      │ ───────────────────────▶│                          │               │
│      │                         │                          │               │
│      │                         │ 1. Sum() 执行业务         │               │
│      │                         │    bus.Sum(11, 12)        │               │
│      │                         │                          │               │
│      │                         ▼                          │               │
│      │                   SumReply{V:23}                  │               │
│      │ ◀─────────────────────────────────────────────── │               │
│      │                         │                          │               │
│      │                         │                          │               │
│      │                         │ grpc.Dial(:50052)        │               │
│      │                         │ ────────────────────────▶│               │
│      │                         │                          │               │
│      │                         │ client.Concat()          │               │
│      │                         │  1. bus.Concat("ab","c") │               │
│      │                         │     → "abc"              │               │
│      │                         │                          │               │
│      │                         │  2. strClient.Count()    │               │
│      │                         │ ───────────────────────▶│               │
│      │                         │                          │               │
│      │                         │                          │ Count()       │
│      │                         │                          │ bus.Count()  │
│      │                         │                          │               │
│      │                         │ CountReply{V:3}          │               │
│      │                         │ ◀─────────────────────── │               │
│      │                         │                          │               │
│      │                         │  3. strClient.Uppercase()│               │
│      │                         │ ────────────────────────▶│               │
│      │                         │                          │               │
│      │                         │                          │ Uppercase()  │
│      │                         │                          │ bus.Upper()  │
│      │                         │                          │               │
│      │                         │ UppercaseReply{V:"ABC"}  │               │
│      │                         │ ◀─────────────────────── │               │
│      │                         │                          │               │
│      │                         ▼                          │               │
│      │                   ConcatReply{V:"ABC"}             │               │
│      │ ◀──────────────────────────────────────────────── │               │
│      │                         │                          │               │
│      ▼                         ▼                          ▼               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 为什么需要连接复用

```go
// ❌ 不好：每次调用都新建连接
func badExample() {
	for i := 0; i < 1000; i++ {
		conn, _ := grpc.Dial("localhost:50051", ...)  // 每次新建！
		client := proto.NewAddClient(conn)
		client.Sum(ctx, req)  // 调用
		conn.Close()  // 关闭
	}
	// 结果：1000 次 TCP 握手 + 1000 次 HTTP/2 握手
}

// ✅ 好：复用连接
func goodExample() {
	conn, _ := grpc.Dial("localhost:50051", ...)
	defer conn.Close()
	client := proto.NewAddClient(conn)

	for i := 0; i < 1000; i++ {
		client.Sum(ctx, req)  // 复用同一个连接
	}
	// 结果：1 次 TCP 握手 + 1 次 HTTP/2 握手
}
```

**HTTP/2 的优势**：
- 单个 TCP 连接上可以并发多个请求（多路复用）
- 不需要为每个 RPC 新建连接

---

## 7. 进阶用法

### 7.1 服务端拦截器（Unary）

```go
// 日志拦截器
func loggingInterceptor(
	ctx context.Context,
	req interface{},
	info *grpc.UnaryServerInfo,
	handler grpc.UnaryHandler,
) (interface{}, error) {
	// 前置处理
	fmt.Printf("收到请求: %s.%s\n", info.FullMethod, req)

	// 调用实际的处理函数
	resp, err := handler(ctx, req)

	// 后置处理
	fmt.Printf("返回响应: %v, 错误: %v\n", resp, err)
	return resp, err
}

// 使用拦截器
s := grpc.NewServer(
	grpc.UnaryInterceptor(loggingInterceptor),
)
proto.RegisterAddServer(s, server.NewAddSvc(...))
```

### 7.2 服务端拦截器（Stream）

```go
func streamLoggingInterceptor(
	srv interface{},
	ss grpc.ServerStream,
	info *grpc.StreamServerInfo,
	handler grpc.StreamHandler,
) error {
	fmt.Printf("流式请求: %s\n", info.FullMethod)
	return handler(srv, ss)
}

s := grpc.NewServer(
	grpc.StreamInterceptor(streamLoggingInterceptor),
)
```

### 7.3 gRPC 元数据（Metadata）

gRPC 通过 Metadata 在请求中传递额外信息，类似 HTTP Headers。

```go
// 服务端读取 Metadata
func (s *addSvc) Sum(ctx context.Context, req *proto.SumRequest) (*proto.SumReply, error) {
	// 从 context 中获取 metadata
	md, ok := metadata.FromIncomingContext(ctx)
	if !ok {
		return nil, status.Error(codes.InvalidArgument, "无 metadata")
	}

	// 读取特定字段
	if values := md.Get("authorization"); len(values) > 0 {
		fmt.Println("Token:", values[0])
	}

	// 响应时添加 header
	grpc.SendHeader(ctx, metadata.New(map[string]string{
		"trace-id": "xxx",
	}))

	// 设置 trailer（最后发送）
	grpc.SetTrailer(ctx, metadata.New(map[string]string{
		"status": "ok",
	}))

	return &proto.SumReply{V: req.A + req.B}, nil
}

// 客户端发送 Metadata
func clientWithMetadata() {
	// 创建 outbound metadata
	md := metadata.New(map[string]string{
		"authorization": "Bearer xxx",
		"user-id":      "12345",
	})

	// 把 metadata 附加到 context
	ctx := metadata.NewOutgoingContext(context.Background(), md)

	// 调用 RPC（metadata 会自动发送）
	client.Sum(ctx, req)
}
```

### 7.4 客户端连接池

```go
type ClientPool struct {
	clients []proto.AddClient
	index   int
	mu      sync.Mutex
}

func NewClientPool(addresses []string) (*ClientPool, error) {
	pool := &ClientPool{
		clients: make([]proto.AddClient, len(addresses)),
	}

	for i, addr := range addresses {
		conn, err := grpc.Dial(addr, grpc.WithTransportCredentials(insecure.NewCredentials()))
		if err != nil {
			return nil, err
		}
		pool.clients[i] = proto.NewAddClient(conn)
	}

	return pool, nil
}

// 负载均衡获取客户端
func (p *ClientPool) GetClient() proto.AddClient {
	p.mu.Lock()
	defer p.mu.Unlock()
	client := p.clients[p.index]
	p.index = (p.index + 1) % len(p.clients)
	return client
}
```

### 7.5 健康检查

```go
import "google.golang.org/grpc/health"
import "google.golang.org/grpc/health/grpc_health_v1"

func main() {
	// 创建健康检查服务
	healthServer := health.NewServer()

	// 注册到 gRPC Server
	s := grpc.NewServer()
	grpc_health_v1.RegisterHealthServer(s, healthServer)

	// 设置服务健康状态
	healthServer.SetServingStatus("addsvc.Add", grpc_health_v1.HealthCheckResponse_SERVING)
}
```

---

## 总结

```
┌──────────────────────────────────────────────────────────────────────┐
│                        gRPC 核心知识点                                │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Proto 文件：                                                         │
│  • syntax = "proto3"  ← 必须声明                                    │
│  • message 定义数据结构  ← 类似 struct                               │
│  • service 定义 RPC 方法  ← 类似 interface                           │
│  • 字段序号不能重复也不能改                                          │
│                                                                       │
│  代码生成：                                                           │
│  • protoc-gen-go  → *.pb.go（消息类型）                             │
│  • protoc-gen-go-grpc → *_grpc.pb.go（客户端/服务端）               │
│                                                                       │
│  服务端：                                                            │
│  • 嵌入 UnimplementedAddServer                                       │
│  • 实现 RPC 方法签名                                                  │
│  • grpc.NewServer() → RegisterServer() → Serve()                     │
│                                                                       │
│  客户端：                                                            │
│  • grpc.Dial() → NewXxxClient() → client.Xxx()                       │
│  • Dial 一次，复用连接                                                │
│  • 记得 defer conn.Close()                                          │
│                                                                       │
│  Context：                                                            │
│  • 传递请求截止时间、超时控制                                        │
│  • 传递 Metadata（类似 HTTP Headers）                                │
│  • 传递取消信号                                                      │
│                                                                       │
│  拦截器：                                                            │
│  • 服务端：UnaryInterceptor / StreamInterceptor                      │
│  • 客户端：WithUnaryInterceptor / WithStreamInterceptor              │
│  • 可以链式组合多个拦截器                                            │
└──────────────────────────────────────────────────────────────────────┘
```
