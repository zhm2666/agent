package llm

func CreateLLM(provider, apiKey, modelName string) (BaseLLM, error) {
	switch provider {
	case "deepseek":
		return NewDeepSeekLLM(apiKey, modelName), nil
	case "openai":
		return NewOpenAILLM(apiKey, modelName), nil
	default:
		return nil, &LLMError{Provider: provider, Message: "unsupported LLM provider"}
	}
}

type LLMError struct {
	Provider string
	Message string
}

func (e *LLMError) Error() string {
	return "LLM Error [" + e.Provider + "]: " + e.Message
}
