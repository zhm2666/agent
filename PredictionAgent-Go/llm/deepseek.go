package llm

import (
	"context"
	"errors"
	"fmt"

	"github.com/sashabaranov/go-openai"
)

// DeepSeekLLM DeepSeek LLM客户端
type DeepSeekLLM struct {
	apiKey    string
	modelName string
	client    *openai.Client
}

// NewDeepSeekLLM 创建DeepSeek LLM客户端
func NewDeepSeekLLM(apiKey, modelName string) *DeepSeekLLM {
	config := openai.DefaultConfig(apiKey)
	config.BaseURL = "https://api.deepseek.com/v1"

	client := openai.NewClientWithConfig(config)

	return &DeepSeekLLM{
		apiKey:    apiKey,
		modelName: modelName,
		client:    client,
	}
}

// Invoke 调用LLM
func (l *DeepSeekLLM) Invoke(ctx context.Context, systemPrompt, userPrompt string, opts ...Option) (string, error) {
	if l.client == nil {
		return "", errors.New("DeepSeek client not initialized")
	}

	// 解析选项
	options := &options{temperature: 0.7, maxTokens: 2048}
	for _, opt := range opts {
		opt(options)
	}

	req := openai.ChatCompletionRequest{
		Model: l.modelName,
		Messages: []openai.ChatCompletionMessage{
			{Role: openai.ChatMessageRoleSystem, Content: systemPrompt},
			{Role: openai.ChatMessageRoleUser, Content: userPrompt},
		},
		Temperature: float32(options.temperature),
		MaxTokens:   options.maxTokens,
	}

	resp, err := l.client.CreateChatCompletion(ctx, req)
	if err != nil {
		return "", fmt.Errorf("DeepSeek API error: %w", err)
	}

	if len(resp.Choices) == 0 {
		return "", errors.New("no response from DeepSeek")
	}

	return resp.Choices[0].Message.Content, nil
}

// GetModelInfo 获取模型信息
func (l *DeepSeekLLM) GetModelInfo() map[string]string {
	return map[string]string{
		"provider": "deepseek",
		"model":    l.modelName,
	}
}
