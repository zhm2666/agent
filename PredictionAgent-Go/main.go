package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"

	"prediction-agent/agent"
	"prediction-agent/config"
)

func main() {
	fmt.Println("============================================================")
	fmt.Println("Prediction Agent (Go Version)")
	fmt.Println("============================================================")

	// 加载配置
	cfg := config.LoadConfig()

	// 创建Agent
	predAgent, err := agent.NewPredictionAgent(cfg)
	if err != nil {
		log.Fatalf("Failed to create agent: %v", err)
	}

	// 解析命令行参数
	query := "预测下季度销售额"
	chartType := "combined"
	useMockData := true

	if len(os.Args) > 1 {
		query = os.Args[1]
	}
	if len(os.Args) > 2 {
		chartType = os.Args[2]
	}

	// 执行分析
	ctx := context.Background()
	req := agent.AnalyzeRequest{
		Query:       query,
		ChartType:   chartType,
		UseMockData: useMockData,
	}

	resp := predAgent.Analyze(ctx, req)

	// 输出结果
	fmt.Println("\n============================================================")
	fmt.Println("Analysis Result")
	fmt.Println("============================================================")

	if resp.Success {
		fmt.Println("Status: SUCCESS")
		fmt.Printf("Product: %s (%s)\n", resp.Product["name"], resp.Product["code"])
		fmt.Printf("Chart URL: %s\n", resp.Chart["url"])
		fmt.Println("\nKey Insights:")
		for _, insight := range resp.Analysis["key_insights"].([]string) {
			fmt.Printf("  - %s\n", insight)
		}
		fmt.Println("\nRecommendations:")
		for _, rec := range resp.Analysis["recommendations"].([]string) {
			fmt.Printf("  - %s\n", rec)
		}

		// 保存状态
		if err := predAgent.SaveState("output/agent_state.json"); err != nil {
			log.Printf("Failed to save state: %v", err)
		}
	} else {
		fmt.Println("Status: FAILED")
		fmt.Printf("Error: %s\n", resp.Error)
	}

	// 输出JSON格式完整结果
	jsonData, _ := json.MarshalIndent(resp, "", "  ")
	fmt.Println("\n--- Full JSON Response ---")
	fmt.Println(string(jsonData))
}
