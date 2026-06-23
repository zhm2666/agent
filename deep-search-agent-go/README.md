# Deep Search Agent (Go Version)

A Go implementation of a Deep Search AI Agent that generates high-quality research reports through multi-round search and reflection.

## Features

- **Framework-free design**: Built from scratch without heavy frameworks like LangChain
- **Multi-LLM support**: Supports DeepSeek, OpenAI and other major LLMs
- **Intelligent search**: Integrated with Tavily search engine for high-quality web search
- **Reflection mechanism**: Multi-round reflection optimization for research depth and completeness
- **State management**: Complete research process state tracking and recovery
- **Markdown output**: Beautifully formatted research reports

## Project Structure

```
deep-search-agent-go/
├── cmd/
│   └── main.go              # CLI entry point
├── internal/
│   ├── agent/               # Main agent implementation
│   ├── config/              # Configuration management
│   ├── llm/                # LLM client implementations
│   ├── nodes/              # Processing nodes
│   ├── prompts/            # Prompt definitions
│   ├── search/             # Search tool (Tavily)
│   ├── state/              # State management
│   └── utils/              # Utility functions
├── config.env.example       # Example environment config
├── config.json.example      # Example JSON config
├── go.mod                  # Go module file
└── README.md              # This file
```

## Prerequisites

- Go 1.21 or higher
- DeepSeek API key (get from [DeepSeek Platform](https://platform.deepseek.com/))
- Tavily API key (get from [Tavily](https://tavily.com/) - 1000 free searches/month)

## Installation

```bash
# Clone or copy the project
cd deep-search-agent-go

# Install dependencies
go mod tidy
```

## Configuration

Create a `config.env` file or set environment variables:

### Option 1: Environment Variables

```bash
export DEEPSEEK_API_KEY=your_deepseek_api_key
export TAVILY_API_KEY=your_tavily_api_key
export DEFAULT_LLM_PROVIDER=deepseek
```

### Option 2: Config File

Copy the example config:

```bash
cp config.env.example config.env
# Edit config.env with your API keys
```

## Usage

### Basic Usage

```bash
# Run with default query
go run cmd/main.go

# Run with custom query
go run cmd/main.go -query "量子计算的发展现状"

# Run without saving report
go run cmd/main.go -query "人工智能" -save=false

# Use custom config file
go run cmd/main.go -config config.json -query "区块链技术"
```

### Programmatic Usage

```go
package main

import (
    "fmt"
    "github.com/deepsearch/deep-search-agent/internal/agent"
    "github.com/deepsearch/deep-search-agent/internal/config"
)

func main() {
    cfg := config.DefaultConfig()
    cfg.DeepSeekAPIKey = "your_api_key"
    cfg.TavilyAPIKey = "your_tavily_key"
    
    agent, err := agent.CreateAgent(cfg)
    if err != nil {
        panic(err)
    }
    
    report, err := agent.Research("人工智能发展趋势", true)
    if err != nil {
        panic(err)
    }
    
    fmt.Println(report)
}
```

## How It Works

1. **Structure Generation**: Generate report outline and paragraph structure based on query
2. **Initial Research**: Generate search queries for each paragraph and fetch relevant information
3. **Initial Summary**: Generate first draft of each paragraph based on search results
4. **Reflection Optimization**: Multi-round reflection to discover gaps and supplementary search
5. **Final Integration**: Integrate all paragraphs into a complete Markdown report

## API Reference

### Config

```go
type Config struct {
    DeepSeekAPIKey        string
    OpenAIAPIKey          string
    TavilyAPIKey          string
    DefaultLLMProvider    string  // "deepseek" or "openai"
    DeepSeekModel         string
    OpenAIModel           string
    MaxSearchResults      int
    SearchTimeout         int
    MaxContentLength      int
    MaxReflections        int
    MaxParagraphs         int
    OutputDir             string
    SaveIntermediateState bool
}
```

### DeepSearchAgent

```go
// Create agent
agent, err := agent.CreateAgent(cfg)

// Run research
report, err := agent.Research(query, saveReport)

// Get progress
progress := agent.GetProgressSummary()

// Save/Load state
agent.SaveState("state.json")
agent.LoadState("state.json")
```

## License

MIT License
