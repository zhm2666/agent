# AI Chat 流式交互技术文档

## 一、项目概述

这是一个基于 Vue 3 + TypeScript + Pinia 的 AI 聊天前端项目，核心功能是与后端进行流式(SSE)对话交互，实现逐字显示 AI 回复效果。

### 核心特性
- 流式文本响应（逐字显示）
- 多会话管理
- 上下文连贯对话
- Markdown 渲染
- 代码高亮

## 二、核心文件结构

| 文件 | 路径 | 作用 |
|------|------|------|
| API模块 | src/api/index.ts | 封装所有API请求，含流式请求核心函数 fetchChatAPIProcess |
| Chat Store | src/store/modules/chat/index.ts | 聊天状态管理，消息存储和更新 |
| 聊天页面 | src/views/chat/index.vue | 聊天主页面，消息发送和展示入口 |
| 消息组件 | src/views/chat/components/Message/index.vue | 单条消息容器组件 |
| 文本组件 | src/views/chat/components/Message/Text.vue | Markdown文本渲染组件 |

## 三、流式实现的位置

### 3.1 流式请求函数 (src/api/index.ts)

流式交互的核心实现位于 `src/api/index.ts` 文件的 `fetchChatAPIProcess` 函数中（第86-222行）。

该函数使用 Fetch API 的 ReadableStream 来处理后端返回的 SSE 流式响应。

关键代码逻辑：
1. 使用 fetch 发送 POST 请求到 /chat-process 接口
2. 通过 response.body.getReader() 获取流读取器
3. 使用 TextDecoder 解码二进制数据
4. 按双换行符分割 SSE 消息
5. 解析 data: 字段中的 JSON 数据
6. 通过 onDownloadProgress 回调实时返回增量文本

### 3.2 流式请求调用处 (src/views/chat/index.vue)

聊天页面中的 `onConversation` 函数（第62-206行）调用了流式请求。

关键代码：

```typescript
await fetchChatAPIProcess({
  prompt: message,
  options,
  signal: controller.signal,
  onDownloadProgress: ({ event }) => {
    const data = JSON.parse(event.target.responseText)
    updateChat(+uuid, index, {
      text: data.text,
      loading: false,
      conversationOptions: {
        conversationId: data.conversationId,
        parentMessageId: data.id
      },
    })
  },
})
```

### 3.3 消息渲染 (src/views/chat/components/Message/index.vue)

消息组件接收 text 属性并传递给 TextComponent 进行渲染。

关键代码：

```vue
<TextComponent
  :inversion="inversion"
  :error="error"
  :text="text"
  :loading="loading"
  :as-raw-text="asRawText"
/>
```

### 3.4 Markdown渲染 (src/views/chat/components/Message/Text.vue)

Text.vue 组件负责将纯文本转换为 Markdown 并渲染，支持标题、列表、引用、代码块语法高亮、表格渲染、数学公式（KaTeX）等。

当 text 属性变化时，Vue 响应式系统自动触发重新渲染，实现流式显示效果。

## 四、与后端交互流程

### 4.1 请求发送

前端通过 Fetch API 发送 POST 请求到 /chat-process 接口，请求体包含 prompt（用户消息）、options（会话选项）、systemMessage（系统提示词）。

### 4.2 后端响应格式

后端采用 SSE（Server-Sent Events）格式返回流式数据，每条消息以 data: 开头，以双换行符结束

响应示例：

data: {"id":"msg-xxx","role":"assistant","text":"你","delta":"你"}

data: {"id":"msg-xxx","role":"assistant","text":"你好","delta":"好"}

data: [DONE]

### 4.3 数据解析

前端接收到 SSE 数据后，按以下步骤处理：
1. 使用 TextDecoder 解码二进制数据
2. 将数据追加到缓冲区
3. 按双换行符分割消息
4. 提取 data: 后面的 JSON 字符串
5. 解析 JSON 获取 delta（增量文本）和 text（累积文本）
6. 调用 onDownloadProgress 回调返回给调用方

### 4.4 状态更新

接收到增量数据后，通过 updateChat 更新 Pinia Store 中的消息文本。Vue 响应式系统检测到数据变化，自动重新渲染 TextComponent，实现逐字显示效果。

## 五、完整数据流图

用户输入消息 -> chat/index.vue 的 onConversation -> addChat 添加用户消息 -> addChat 添加AI空消息占位 -> fetchChatAPIProcess 发送POST请求 -> 后端返回SSE流 -> ReadableStream 逐块读取 -> 解析 data: 字段 -> onDownloadProgress 回调 -> updateChat 更新Store -> Vue响应式更新 -> Text.vue 渲染 Markdown -> 页面显示

## 六、总结

1. 流式实现核心：使用 Fetch API + ReadableStream 读取 SSE 流
2. 数据解析：按双换行符分割，解析 data: 字段提取增量文本
3. 状态管理：通过 Pinia Store 管理消息列表
4. 实时渲染：Vue 响应式系统自动更新组件
5. 请求取消：使用 AbortController 支持停止生成