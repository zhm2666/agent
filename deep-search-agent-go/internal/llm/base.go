package llm

type LLMResponse struct {
	Content   string
	RawOutput string
	Model     string
}

type BaseLLM interface {
	Invoke(systemPrompt, userPrompt string, options ...Option) (string, error)
	GetModelInfo() map[string]interface{}
	GetDefaultModel() string
}

type Option func(*LLMOptions)

type LLMOptions struct {
	Temperature float64
	MaxTokens   int
	Stream      bool
}

func WithTemperature(temp float64) Option {
	return func(o *LLMOptions) {
		o.Temperature = temp
	}
}

func WithMaxTokens(max int) Option {
	return func(o *LLMOptions) {
		o.MaxTokens = max
	}
}

func WithStream(stream bool) Option {
	return func(o *LLMOptions) {
		o.Stream = stream
	}
}

func DefaultOptions() *LLMOptions {
	return &LLMOptions{
		Temperature: 0.7,
		MaxTokens:   4000,
		Stream:      false,
	}
}

func ValidateResponse(response string) string {
	if response == "" {
		return ""
	}
	return response
}
