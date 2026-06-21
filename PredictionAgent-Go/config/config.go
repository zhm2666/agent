package config

import (
	"os"
	"strconv"
)

// Config 应用配置
type Config struct {
	// LLM配置
	DefaultLLMProvider string
	DeepSeekAPIKey    string
	DeepSeekModel     string
	OpenAIAPIKey      string
	OpenAIModel       string

	// 数据库配置
	MySQLHost     string
	MySQLPort     int
	MySQLUser     string
	MySQLPassword string
	MySQLDatabase string

	// 图表配置
	ChartOutputDir string
	ChartBaseURL   string

	// 预测配置
	PredictionDays int

	// 输出配置
	OutputDir string
}

// DefaultConfig 默认配置
func DefaultConfig() *Config {
	return &Config{
		// LLM配置
		DefaultLLMProvider: "deepseek",
		DeepSeekAPIKey:    "",
		DeepSeekModel:     "deepseek-chat",
		OpenAIAPIKey:      "",
		OpenAIModel:       "gpt-4o-mini",

		// 数据库配置
		MySQLHost:     "localhost",
		MySQLPort:     3306,
		MySQLUser:     "root",
		MySQLPassword: "",
		MySQLDatabase: "prediction_db",

		// 图表配置
		ChartOutputDir: "output/charts",
		ChartBaseURL:   "/charts",

		// 预测配置
		PredictionDays: 30,

		// 输出配置
		OutputDir: "output",
	}
}

// LoadConfig 从环境变量加载配置
func LoadConfig() *Config {
	cfg := DefaultConfig()

	// LLM配置
	if apiKey := os.Getenv("DEEPSEEK_API_KEY"); apiKey != "" {
		cfg.DeepSeekAPIKey = apiKey
	}
	if apiKey := os.Getenv("OPENAI_API_KEY"); apiKey != "" {
		cfg.OpenAIAPIKey = apiKey
	}

	// 数据库配置
	if host := os.Getenv("MYSQL_HOST"); host != "" {
		cfg.MySQLHost = host
	}
	if port := os.Getenv("MYSQL_PORT"); port != "" {
		if p, err := strconv.Atoi(port); err == nil {
			cfg.MySQLPort = p
		}
	}
	if user := os.Getenv("MYSQL_USER"); user != "" {
		cfg.MySQLUser = user
	}
	if password := os.Getenv("MYSQL_PASSWORD"); password != "" {
		cfg.MySQLPassword = password
	}
	if database := os.Getenv("MYSQL_DATABASE"); database != "" {
		cfg.MySQLDatabase = database
	}

	// 图表配置
	if outputDir := os.Getenv("CHART_OUTPUT_DIR"); outputDir != "" {
		cfg.ChartOutputDir = outputDir
	}
	if baseURL := os.Getenv("CHART_BASE_URL"); baseURL != "" {
		cfg.ChartBaseURL = baseURL
	}

	return cfg
}
