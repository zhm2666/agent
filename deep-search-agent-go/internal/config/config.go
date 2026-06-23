package config

import (
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"strings"
)

type Config struct {
	DeepSeekAPIKey        string `json:"deepseek_api_key"`
	OpenAIAPIKey          string `json:"openai_api_key"`
	TavilyAPIKey          string `json:"tavily_api_key"`
	DefaultLLMProvider    string `json:"default_llm_provider"`
	DeepSeekModel         string `json:"deepseek_model"`
	OpenAIModel           string `json:"openai_model"`
	MaxSearchResults      int    `json:"max_search_results"`
	SearchTimeout         int    `json:"search_timeout"`
	MaxContentLength      int    `json:"max_content_length"`
	MaxReflections        int    `json:"max_reflections"`
	MaxParagraphs         int    `json:"max_paragraphs"`
	OutputDir             string `json:"output_dir"`
	SaveIntermediateState bool   `json:"save_intermediate_state"`
}

func DefaultConfig() *Config {
	return &Config{
		DefaultLLMProvider:    "deepseek",
		DeepSeekModel:         "deepseek-chat",
		OpenAIModel:           "gpt-4o-mini",
		MaxSearchResults:      3,
		SearchTimeout:         240,
		MaxContentLength:      20000,
		MaxReflections:        2,
		MaxParagraphs:         5,
		OutputDir:             "reports",
		SaveIntermediateState: true,
	}
}

func LoadFromEnv() *Config {
	cfg := DefaultConfig()
	
	if apiKey := os.Getenv("DEEPSEEK_API_KEY"); apiKey != "" {
		cfg.DeepSeekAPIKey = apiKey
	}
	if apiKey := os.Getenv("OPENAI_API_KEY"); apiKey != "" {
		cfg.OpenAIAPIKey = apiKey
	}
	if apiKey := os.Getenv("TAVILY_API_KEY"); apiKey != "" {
		cfg.TavilyAPIKey = apiKey
	}
	if provider := os.Getenv("DEFAULT_LLM_PROVIDER"); provider != "" {
		cfg.DefaultLLMProvider = provider
	}
	
	return cfg
}

func LoadFromFile(filepath string) (*Config, error) {
	data, err := os.ReadFile(filepath)
	if err != nil {
		return nil, fmt.Errorf("failed to read config file: %w", err)
	}

	cfg := DefaultConfig()
	
	if strings.HasSuffix(filepath, ".json") {
		if err := json.Unmarshal(data, cfg); err != nil {
			return nil, fmt.Errorf("failed to parse JSON config: %w", err)
		}
	} else {
		cfg = parseEnvFormat(data, filepath)
	}

	return cfg, nil
}

func parseEnvFormat(data []byte, filepath string) *Config {
	cfg := DefaultConfig()
	
	lines := strings.Split(string(data), "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}
		
		key := strings.TrimSpace(parts[0])
		value := strings.TrimSpace(parts[1])
		value = strings.Trim(value, "\"'")
		
		switch key {
		case "DEEPSEEK_API_KEY":
			cfg.DeepSeekAPIKey = value
		case "OPENAI_API_KEY":
			cfg.OpenAIAPIKey = value
		case "TAVILY_API_KEY":
			cfg.TavilyAPIKey = value
		case "DEFAULT_LLM_PROVIDER":
			cfg.DefaultLLMProvider = value
		case "DEEPSEEK_MODEL":
			cfg.DeepSeekModel = value
		case "OPENAI_MODEL":
			cfg.OpenAIModel = value
		case "MAX_SEARCH_RESULTS":
			fmt.Sscanf(value, "%d", &cfg.MaxSearchResults)
		case "SEARCH_TIMEOUT":
			fmt.Sscanf(value, "%d", &cfg.SearchTimeout)
		case "MAX_CONTENT_LENGTH":
			fmt.Sscanf(value, "%d", &cfg.MaxContentLength)
		case "MAX_REFLECTIONS":
			fmt.Sscanf(value, "%d", &cfg.MaxReflections)
		case "MAX_PARAGRAPHS":
			fmt.Sscanf(value, "%d", &cfg.MaxParagraphs)
		case "OUTPUT_DIR":
			cfg.OutputDir = value
		case "SAVE_INTERMEDIATE_STATES":
			cfg.SaveIntermediateState = strings.ToLower(value) == "true"
		}
	}
	
	return cfg
}

func (c *Config) Validate() error {
	if c.DefaultLLMProvider == "deepseek" && c.DeepSeekAPIKey == "" {
		return fmt.Errorf("DeepSeek API key is required when using deepseek provider")
	}
	if c.DefaultLLMProvider == "openai" && c.OpenAIAPIKey == "" {
		return fmt.Errorf("OpenAI API key is required when using openai provider")
	}
	if c.TavilyAPIKey == "" {
		return fmt.Errorf("Tavily API key is required")
	}
	return nil
}

func (c *Config) GetLLMProvider() string {
	return c.DefaultLLMProvider
}

func (c *Config) MaskSensitive() string {
	mask := func(s string) string {
		if len(s) <= 8 {
			return "****"
		}
		return s[:4] + "****" + s[len(s)-4:]
	}
	
	dsKey := mask(c.DeepSeekAPIKey)
	oaiKey := mask(c.OpenAIAPIKey)
	tavKey := mask(c.TavilyAPIKey)
	
	return fmt.Sprintf("Config{Provider:%s, DeepSeek:%s, OpenAI:%s, Tavily:%s, Model:%s}",
		c.DefaultLLMProvider, dsKey, oaiKey, tavKey, c.DeepSeekModel)
}

func (c *Config) SetAPIKeys(deepseek, openai, tavily string) {
	if deepseek != "" {
		c.DeepSeekAPIKey = deepseek
	}
	if openai != "" {
		c.OpenAIAPIKey = openai
	}
	if tavily != "" {
		c.TavilyAPIKey = tavily
	}
}

func LoadConfig(configFile string) (*Config, error) {
	var cfg *Config
	var err error
	
	if configFile != "" {
		cfg, err = LoadFromFile(configFile)
		if err != nil {
			return nil, err
		}
	} else {
		for _, path := range []string{"config.json", "config.env", ".env"} {
			if _, statErr := os.Stat(path); statErr == nil {
				cfg, err = LoadFromFile(path)
				if err == nil {
					break
				}
			}
		}
		if cfg == nil {
			cfg = LoadFromEnv()
		}
	}
	
	if err := cfg.Validate(); err != nil {
		return nil, err
	}
	
	return cfg, nil
}

func ExtractJSON(input string) string {
	jsonPattern := regexp.MustCompile(`\{[\s\S]*\}`)
	match := jsonPattern.FindString(input)
	if match == "" {
		jsonPattern = regexp.MustCompile(`\[[\s\S]*\]`)
		match = jsonPattern.FindString(input)
	}
	return match
}
