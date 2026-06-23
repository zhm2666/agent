package llm

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

type OpenAILLM struct {
	apiKey       string
	modelName    string
	defaultModel string
	client       *http.Client
}

func NewOpenAILLM(apiKey, modelName string) *OpenAILLM {
	if apiKey == "" {
		apiKey = "your-openai-api-key"
	}
	if modelName == "" {
		modelName = "gpt-4o-mini"
	}
	
	return &OpenAILLM{
		apiKey:       apiKey,
		modelName:    modelName,
		defaultModel: "gpt-4o-mini",
		client: &http.Client{
			Timeout: 120 * time.Second,
		},
	}
}

func (o *OpenAILLM) GetDefaultModel() string {
	return o.defaultModel
}

func (o *OpenAILLM) GetModelInfo() map[string]interface{} {
	return map[string]interface{}{
		"provider": "OpenAI",
		"model":    o.modelName,
		"api_base": "https://api.openai.com/v1",
	}
}

func (o *OpenAILLM) Invoke(systemPrompt, userPrompt string, options ...Option) (string, error) {
	opts := DefaultOptions()
	for _, opt := range options {
		opt(opts)
	}

	messages := []map[string]string{
		{"role": "system", "content": systemPrompt},
		{"role": "user", "content": userPrompt},
	}

	requestBody := map[string]interface{}{
		"model": o.modelName,
		"messages": messages,
		"temperature": opts.Temperature,
		"max_tokens": opts.MaxTokens,
		"stream": false,
	}

	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		return "", fmt.Errorf("failed to marshal request: %w", err)
	}

	url := "https://api.openai.com/v1/chat/completions"
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+o.apiKey)

	resp, err := o.client.Do(req)
	if err != nil {
		return "", fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("API request failed with status %d: %s", resp.StatusCode, string(body))
	}

	var result map[string]interface{}
	if err := json.Unmarshal(body, &result); err != nil {
		return "", fmt.Errorf("failed to parse response: %w", err)
	}

	choices, ok := result["choices"].([]interface{})
	if !ok || len(choices) == 0 {
		return "", fmt.Errorf("no choices in response")
	}

	choice, ok := choices[0].(map[string]interface{})
	if !ok {
		return "", fmt.Errorf("invalid choice format")
	}

	message, ok := choice["message"].(map[string]interface{})
	if !ok {
		return "", fmt.Errorf("no message in choice")
	}

	content, ok := message["content"].(string)
	if !ok {
		return "", fmt.Errorf("invalid content format")
	}

	return ValidateResponse(content), nil
}
