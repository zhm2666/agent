package main

import (
	"flag"
	"fmt"
	"os"

	"github.com/deepsearch/deep-search-agent/internal/agent"
	"github.com/deepsearch/deep-search-agent/internal/config"
)

func main() {
	configFile := flag.String("config", "", "Path to config file")
	query := flag.String("query", "", "Research query")
	saveReport := flag.Bool("save", true, "Save report to file")
	
	flag.Parse()
	
	if *query == "" {
		*query = "2025年人工智能发展趋势"
		fmt.Println("No query provided, using default: 2025年人工智能发展趋势")
	}
	
	cfg, err := loadConfiguration(*configFile)
	if err != nil {
		fmt.Printf("Failed to load configuration: %v\n", err)
		fmt.Println("\nPlease set your API keys:")
		fmt.Println("  export DEEPSEEK_API_KEY=your_deepseek_key")
		fmt.Println("  export TAVILY_API_KEY=your_tavily_key")
		fmt.Println("\nOr create a config file (config.env):")
		fmt.Println("  DEEPSEEK_API_KEY=your_key")
		fmt.Println("  TAVILY_API_KEY=your_key")
		os.Exit(1)
	}
	
	fmt.Println("\n=== Deep Search Agent (Go Version) ===")
	fmt.Printf("Config: %s\n", cfg.MaskSensitive())
	fmt.Printf("Query: %s\n", *query)
	fmt.Println()
	
	agentInstance, err := agent.CreateAgent(cfg)
	if err != nil {
		fmt.Printf("Failed to create agent: %v\n", err)
		os.Exit(1)
	}
	
	report, err := agentInstance.Research(*query, *saveReport)
	if err != nil {
		fmt.Printf("Research failed: %v\n", err)
		os.Exit(1)
	}
	
	fmt.Println("\n=== Final Report ===\n")
	fmt.Println(report)
}

func loadConfiguration(configFile string) (*config.Config, error) {
	cfg, err := config.LoadConfig(configFile)
	if err != nil {
		return nil, err
	}
	
	if err := cfg.Validate(); err != nil {
		return nil, err
	}
	
	return cfg, nil
}
