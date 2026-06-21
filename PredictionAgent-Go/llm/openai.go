package llm

import (
	"context"
	"errors"
	"fmt"

	"github.com/sashabaranov/go-openai"
)

// OpenAILLM OpenAI LLM客户端
type OpenAILLM struct {
	apiKey    string
	modelName string
	client    *openai.Client
}

// NewOpenAILLM 创建OpenAI LLM客户端
func NewOpenAILLM(apiKey, modelName string) *OpenAILLM {
	client := openai.NewClient(apiKey)

	return &OpenAILLM{
		apiKey:    apiKey,
		modelName: modelName,
		client:    client,
	}
}

// Invoke 调用LLM
func (l *OpenAILLM) Invoke(ctx context.Context, systemPrompt, userPrompt string, opts ...Option) (string, error) {
	if l.client == nil {
		return "", errors.New("OpenAI client not initialized")
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
		return "", fmt.Errorf("OpenAI API error: %w", err)
	}

	if len(resp.Choices) == 0 {
		return "", errors.New("no response from OpenAI")
	}

	return resp.Choices[0].Message.Content, nil
}

// GetModelInfo 获取模型信息
func (l *OpenAILLM) GetModelInfo() map[string]string {
	return map[string]string{
		"provider": "openai",
		"model":    l.modelName,
	}
}
