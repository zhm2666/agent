package utils

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
)

func CleanJSONTags(text string) string {
	patterns := []string{
		"```json\\s*",
		"```\\s*$",
		"```",
	}
	
	for _, pattern := range patterns {
		re := regexp.MustCompile(pattern)
		text = re.ReplaceAllString(text, "")
	}
	
	return strings.TrimSpace(text)
}

func CleanMarkdownTags(text string) string {
	patterns := []string{
		"```markdown\\s*",
		"```\\s*$",
		"```",
	}
	
	for _, pattern := range patterns {
		re := regexp.MustCompile(pattern)
		text = re.ReplaceAllString(text, "")
	}
	
	return strings.TrimSpace(text)
}

func RemoveReasoningFromOutput(text string) string {
	patterns := []string{
		`(?i)(?:reasoning|推理|思考|分析)[:：]\s*.*?(?=\{|\[)`,
		`(?i)(?:explanation|解释|说明)[:：]\s*.*?(?=\{|\[)`,
		`^.*?(?=\{|\[)`,
	}
	
	for _, pattern := range patterns {
		re := regexp.MustCompile(pattern)
		text = re.ReplaceAllString(text, "")
	}
	
	return strings.TrimSpace(text)
}

func ExtractCleanResponse(text string) (map[string]interface{}, error) {
	cleaned := CleanJSONTags(text)
	cleaned = RemoveReasoningFromOutput(cleaned)
	
	jsonPattern := regexp.MustCompile(`\{[\s\S]*\}`)
	match := jsonPattern.FindString(cleaned)
	if match != "" {
		return ParseJSON(match)
	}
	
	arrayPattern := regexp.MustCompile(`\[[\s\S]*\]`)
	match = arrayPattern.FindString(cleaned)
	if match != "" {
		result, err := ParseJSON(match)
		if err == nil {
			return map[string]interface{}{"array": result}, nil
		}
	}
	
	fmt.Printf("Failed to parse JSON from: %s...\n", cleaned[:min(200, len(cleaned))])
	return map[string]interface{}{"error": "JSON parsing failed", "raw_text": cleaned}, nil
}

func ParseJSON(text string) (map[string]interface{}, error) {
	cleaned := CleanJSONTags(text)
	
	var result map[string]interface{}
	
	if strings.HasPrefix(cleaned, "[") {
		var arr []interface{}
		if err := json.Unmarshal([]byte(cleaned), &arr); err != nil {
			return nil, err
		}
		return map[string]interface{}{"array": arr}, nil
	}
	
	if err := json.Unmarshal([]byte(cleaned), &result); err != nil {
		return nil, err
	}
	
	return result, nil
}

func TruncateContent(content string, maxLength int) string {
	if len(content) <= maxLength {
		return content
	}
	
	truncated := content[:maxLength]
	lastSpace := strings.LastIndex(truncated, " ")
	
	if lastSpace > maxLength*8/10 {
		return truncated[:lastSpace] + "..."
	}
	
	return truncated + "..."
}

func FormatSearchResultsForPrompt(results []map[string]interface{}, maxLength int) []string {
	formatted := make([]string, 0, len(results))
	
	for _, result := range results {
		if content, ok := result["content"].(string); ok && content != "" {
			truncated := TruncateContent(content, maxLength)
			formatted = append(formatted, truncated)
		}
	}
	
	return formatted
}

func ValidateJSONSchema(data map[string]interface{}, requiredFields []string) bool {
	for _, field := range requiredFields {
		if _, ok := data[field]; !ok {
			return false
		}
	}
	return true
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
