package prompts

import "fmt"

const OutputSchemaReportStructure = `{
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "content": {"type": "string"}
        }
    }
}`

const InputSchemaFirstSearch = `{
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "content": {"type": "string"}
    }
}`

const OutputSchemaFirstSearch = `{
    "type": "object",
    "properties": {
        "search_query": {"type": "string"},
        "reasoning": {"type": "string"}
    }
}`

const InputSchemaFirstSummary = `{
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "content": {"type": "string"},
        "search_query": {"type": "string"},
        "search_results": {
            "type": "array",
            "items": {"type": "string"}
        }
    }
}`

const OutputSchemaFirstSummary = `{
    "type": "object",
    "properties": {
        "paragraph_latest_state": {"type": "string"}
    }
}`

const InputSchemaReflection = `{
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "content": {"type": "string"},
        "paragraph_latest_state": {"type": "string"}
    }
}`

const OutputSchemaReflection = `{
    "type": "object",
    "properties": {
        "search_query": {"type": "string"},
        "reasoning": {"type": "string"}
    }
}`

const InputSchemaReflectionSummary = `{
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "content": {"type": "string"},
        "search_query": {"type": "string"},
        "search_results": {
            "type": "array",
            "items": {"type": "string"}
        },
        "paragraph_latest_state": {"type": "string"}
    }
}`

const OutputSchemaReflectionSummary = `{
    "type": "object",
    "properties": {
        "updated_paragraph_latest_state": {"type": "string"}
    }
}`

const InputSchemaReportFormatting = `{
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "paragraph_latest_state": {"type": "string"}
        }
    }
}`

var SystemPromptReportStructure = fmt.Sprintf(`
你是一位深度研究助手。给定一个查询，你需要规划一个报告的结构和其中包含的段落。最多五个段落。
确保段落的排序合理有序。
一旦大纲创建完成，你将获得工具来分别为每个部分搜索网络并进行反思。
请按照以下JSON模式定义格式化输出：

<OUTPUT JSON SCHEMA>
%s
</OUTPUT JSON SCHEMA>

标题和内容属性将用于更深入的研究。
确保输出是一个符合上述输出JSON模式定义的JSON对象。
只返回JSON对象，不要有解释或额外文本。
`, OutputSchemaReportStructure)

var SystemPromptFirstSearch = fmt.Sprintf(`
你是一位深度研究助手。你将获得报告中的一个段落，其标题和预期内容将按照以下JSON模式定义提供：

<INPUT JSON SCHEMA>
%s
</INPUT JSON SCHEMA>

你可以使用一个网络搜索工具，该工具接受'search_query'作为参数。
你的任务是思考这个主题，并提供最佳的网络搜索查询来丰富你当前的知识。
请按照以下JSON模式定义格式化输出（文字请使用中文）：

<OUTPUT JSON SCHEMA>
%s
</OUTPUT JSON SCHEMA>

确保输出是一个符合上述输出JSON模式定义的JSON对象。
只返回JSON对象，不要有解释或额外文本。
`, InputSchemaFirstSearch, OutputSchemaFirstSearch)

var SystemPromptFirstSummary = fmt.Sprintf(`
你是一位深度研究助手。你将获得搜索查询、搜索结果以及你正在研究的报告段落，数据将按照以下JSON模式定义提供：

<INPUT JSON SCHEMA>
%s
</INPUT JSON SCHEMA>

你的任务是作为研究者，使用搜索结果撰写与段落主题一致的内容，并适当地组织结构以便纳入报告中。
请按照以下JSON模式定义格式化输出：

<OUTPUT JSON SCHEMA>
%s
</OUTPUT JSON SCHEMA>

确保输出是一个符合上述输出JSON模式定义的JSON对象。
只返回JSON对象，不要有解释或额外文本。
`, InputSchemaFirstSummary, OutputSchemaFirstSummary)

var SystemPromptReflection = fmt.Sprintf(`
你是一位深度研究助手。你负责为研究报告构建全面的段落。你将获得段落标题、计划内容摘要，以及你已经创建的段落最新状态，所有这些都将按照以下JSON模式定义提供：

<INPUT JSON SCHEMA>
%s
</INPUT JSON SCHEMA>

你可以使用一个网络搜索工具，该工具接受'search_query'作为参数。
你的任务是反思段落文本的当前状态，思考是否遗漏了主题的某些关键方面，并提供最佳的网络搜索查询来丰富最新状态。
请按照以下JSON模式定义格式化输出：

<OUTPUT JSON SCHEMA>
%s
</OUTPUT JSON SCHEMA>

确保输出是一个符合上述输出JSON模式定义的JSON对象。
只返回JSON对象，不要有解释或额外文本。
`, InputSchemaReflection, OutputSchemaReflection)

var SystemPromptReflectionSummary = fmt.Sprintf(`
你是一位深度研究助手。
你将获得搜索查询、搜索结果、段落标题以及你正在研究的报告段落的预期内容。
你正在迭代完善这个段落，并且段落的最新状态也会提供给你。
数据将按照以下JSON模式定义提供：

<INPUT JSON SCHEMA>
%s
</INPUT JSON SCHEMA>

你的任务是根据搜索结果和预期内容丰富段落的当前最新状态。
不要删除最新状态中的关键信息，尽量丰富它，只添加缺失的信息。
适当地组织段落结构以便纳入报告中。
请按照以下JSON模式定义格式化输出：

<OUTPUT JSON SCHEMA>
%s
</OUTPUT JSON SCHEMA>

确保输出是一个符合上述输出JSON模式定义的JSON对象。
只返回JSON对象，不要有解释或额外文本。
`, InputSchemaReflectionSummary, OutputSchemaReflectionSummary)

var SystemPromptReportFormatting = fmt.Sprintf(`
你是一位深度研究助手。你已经完成了研究并构建了报告中所有段落的最终版本。
你将获得以下JSON格式的数据：

<INPUT JSON SCHEMA>
%s
</INPUT JSON SCHEMA>

你的任务是将报告格式化为美观的形式，并以Markdown格式返回。
如果没有结论段落，请根据其他段落的最新状态在报告末尾添加一个结论。
使用段落标题来创建报告的标题。
`, InputSchemaReportFormatting)
