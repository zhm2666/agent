package llm

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

type DeepSeekLLM struct {
	apiKey       string
	modelName    string
	defaultModel string
	client       *http.Client
}

func NewDeepSeekLLM(apiKey, modelName string) *DeepSeekLLM {
	if apiKey == "" {
		apiKey = "your-deepseek-api-key"
	}
	if modelName == "" {
		modelName = "deepseek-chat"
	}
	
	return &DeepSeekLLM{
		apiKey:       apiKey,
		modelName:    modelName,
		defaultModel: "deepseek-chat",
		client: &http.Client{
			Timeout: 120 * time.Second,
		},
	}
}

func (d *DeepSeekLLM) GetDefaultModel() string {
	return d.defaultModel
}

func (d *DeepSeekLLM) GetModelInfo() map[string]interface{} {
	return map[string]interface{}{
		"provider": "DeepSeek",
		"model":    d.modelName,
		"api_base": "https://api.deepseek.com",
	}
}

func (d *DeepSeekLLM) Invoke(systemPrompt, userPrompt string, options ...Option) (string, error) {
	opts := DefaultOptions()
	for _, opt := range options {
		opt(opts)
	}

	messages := []map[string]string{
		{"role": "system", "content": systemPrompt},
		{"role": "user", "content": userPrompt},
	}

	requestBody := map[string]interface{}{
		"model": d.modelName,
		"messages": messages,
		"temperature": opts.Temperature,
		"max_tokens": opts.MaxTokens,
		"stream": false,
	}

	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		return "", fmt.Errorf("failed to marshal request: %w", err)
	}

	url := "https://api.deepseek.com/chat/completions"
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+d.apiKey)

	resp, err := d.client.Do(req)
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
