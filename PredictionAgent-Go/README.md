# Prediction Agent Go

预测分析Agent的Go语言实现版本

## 项目结构

```
PredictionAgent-Go/
├── config/           # 配置管理
├── logging/           # 日志工厂
├── state/            # 状态管理
├── llm/              # LLM客户端
├── mcp/              # MCP客户端
├── agent/            # Agent核心实现
├── main.go           # 入口文件
└── go.mod
```

## 快速开始

```bash
# 安装依赖
go mod tidy

# 运行
go run main.go
```

## 环境变量

- `DEEPSEEK_API_KEY`: DeepSeek API密钥
- `OPENAI_API_KEY`: OpenAI API密钥
- `MYSQL_HOST`: 数据库主机
- `MYSQL_PORT`: 数据库端口
- `MYSQL_USER`: 数据库用户名
- `MYSQL_PASSWORD`: 数据库密码
- `MYSQL_DATABASE`: 数据库名称
