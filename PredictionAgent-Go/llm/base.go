package llm

import (
	"context"
)

// LLMProvider LLM提供者接口
type LLMProvider interface {
	// Invoke 调用LLM生成回复
	Invoke(ctx context.Context, systemPrompt, userPrompt string, opts ...Option) (string, error)
	// GetModelInfo 获取模型信息
	GetModelInfo() map[string]string
}

// Option LLM调用选项
type Option func(*options)

type options struct {
	temperature float64
	maxTokens   int
}

func WithTemperature(t float64) Option {
	return func(o *options) {
		o.temperature = t
	}
}

func WithMaxTokens(tokens int) Option {
	return func(o *options) {
		o.maxTokens = tokens
	}
}
