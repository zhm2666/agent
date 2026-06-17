/**
 * API 请求模块
 *
 * 功能说明：
 * 1. 封装所有与后端的API请求
 * 2. 支持普通POST请求（使用Axios）
 * 3. 支持SSE流式请求（使用Fetch API）
 * 4. 自动处理认证Token
 *
 * API接口：
 * - /chat - 普通聊天请求
 * - /config - 获取聊天配置
 * - /chat-process - 流式聊天请求（SSE）
 * - /session - 获取会话信息
 * - /verify - 验证Token
 * - /v1/sms/send/code - 发送短信验证码
 * - /v1/user/login - 用户登录
 */

 // ==================== Axios 相关类型 ====================
 // AxiosProgressEvent - Axios下载进度事件类型
 // GenericAbortSignal - AbortController信号类型
 import type { AxiosProgressEvent, GenericAbortSignal } from 'axios'

 // ==================== 请求工具 ====================
 // post - 封装的POST请求函数
 import { post } from '@/utils/request'

 // ==================== 状态管理 ====================
 // 设置Store - 用于获取系统消息等配置
 import { useSettingStore } from '@/store'

 // ==================== Cookie工具 ====================
 // getCookieValue - 获取Cookie值
 import { getCookieValue } from '@/utils/cookie'

 // ==================== 普通聊天请求 ====================
 /**
  * 发送普通聊天请求
  *
  * @template T - 响应数据类型
  * @param prompt - 用户输入的消息
  * @param options - 可选的会话选项（对话ID、父消息ID）
  * @param signal - AbortSignal，用于取消请求
  * @returns Promise<T> - 响应数据
  */
 export function fetchChatAPI<T = any>(
   prompt: string,
   options?: { conversationId?: string; parentMessageId?: string },
   signal?: GenericAbortSignal,
 ) {
   return post<T>({
     url: '/chat',
     data: { prompt, options },
     signal,
   })
 }

 // ==================== 获取聊天配置 ====================
 /**
  * 获取聊天配置信息
  *
  * @template T - 响应数据类型
  * @returns Promise<T> - 配置数据
  */
 export function fetchChatConfig<T = any>() {
   return post<T>({
     url: '/config',
   })
 }

// ==================== 流式聊天请求 ====================
/**
 * 发送流式聊天请求（SSE）
 *
 * 支持实时流式响应，用于AI对话
 *
 * @template T - 响应数据类型
 * @param params - 请求参数
 * @param params.prompt - 用户输入的消息
 * @param params.options - 会话选项
 * @param params.signal - AbortSignal，用于取消请求
 * @param params.onDownloadProgress - 下载进度回调
 * @returns Promise<T> - 响应数据
 */
export function fetchChatAPIProcess<T = any>(
  params: {
    prompt: string
    options?: { conversationId?: string; parentMessageId?: string }
    signal?: GenericAbortSignal
    onDownloadProgress?: (progressEvent: AxiosProgressEvent) => void
  },
): Promise<T> {
  return new Promise((resolve, reject) => {
    // 获取设置Store中的系统消息
    const settingStore = useSettingStore()

    // 构建请求头
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }

    // 从Cookie获取访问令牌
    const access_token = getCookieValue('sso_0voice_access_token')
    if (access_token)
      headers.Authorization = access_token

    // 使用 Fetch API 处理 SSE 流式响应
    const baseURL = import.meta.env.VITE_GLOB_API_URL || ''
    const url = baseURL + '/chat-process'

    // 累积变量
    let accumulatedText = ''
    let lastId = ''
    let conversationId = ''

    fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        prompt: params.prompt,
        options: params.options,
        systemMessage: settingStore.systemMessage
      }),
      signal: params.signal,
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const reader = response.body?.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        const read = () => {
          reader?.read().then(({ done, value }) => {
            if (done) {
              // 处理剩余缓冲数据
              if (buffer.trim()) {
                processBuffer(buffer)
              }
              resolve({} as T)
              return
            }

            // 解码并追加到缓冲区
            buffer += decoder.decode(value, { stream: true })

            // 按双换行符分割（每个SSE消息以\n\n结束）
            const messages = buffer.split('\n\n')
            buffer = messages.pop() || ''

            // 处理每条消息
            for (const message of messages) {
              processBuffer(message)
            }

            // 继续读取下一块数据
            read()
          })
        }

        // 处理缓冲区内容
        function processBuffer(content: string) {
          const lines = content.split('\n')
          for (const line of lines) {
            if (line.startsWith('data:')) {
              const jsonStr = line.slice(5).trim()
              // 忽略 [DONE] 消息
              if (jsonStr === '[DONE]' || jsonStr === '[DONE]\n' || jsonStr === '[object Object]') {
                resolve({} as T)
                return
              }
              try {
                const data = JSON.parse(jsonStr)
                // 累积文本
                if (data.delta !== undefined) {
                  accumulatedText += data.delta
                } else if (data.text !== undefined) {
                  accumulatedText = data.text
                }
                // 保存 ID 和 conversationId
                if (data.id)
                  lastId = data.id
                if (data.conversationId)
                  conversationId = data.conversationId

                // 构建完整的数据对象并传递给回调
                const completeData = {
                  id: lastId,
                  conversationId: conversationId,
                  text: accumulatedText,
                  role: data.role || 'assistant',
                }

                // 模拟 AxiosProgressEvent 格式
                params.onDownloadProgress?.({
                  event: {
                    target: {
                      responseText: JSON.stringify(completeData)
                    }
                  }
                } as AxiosProgressEvent)
              } catch (e) {
                // 忽略解析错误
              }
            }
          }
        }

        read()
      })
      .catch(err => {
        if (err.name === 'AbortError') {
          resolve({} as T)
        } else {
          reject(err)
        }
      })
  })
}

 // ==================== 获取会话信息 ====================
 /**
  * 获取当前用户的会话信息
  *
  * @template T - 响应数据类型
  * @returns Promise<T> - 会话数据
  */
 export function fetchSession<T>() {
   return post<T>({
     url: '/session',
   })
 }

 // ==================== 验证Token ====================
 /**
  * 验证用户Token
  *
  * @template T - 响应数据类型
  * @param token - 要验证的Token
  * @returns Promise<T> - 验证结果
  */
 export function fetchVerify<T>(token: string) {
   return post<T>({
     url: '/verify',
     data: { token },
   })
 }

 // ==================== 发送短信验证码 ====================
 /**
  * 发送短信验证码
  *
  * @template T - 响应数据类型
  * @param phone - 手机号码
  * @returns Promise<T> - 发送结果
  */
 export function fetchCode<T>(phone: string) {
   return post<T>({
     url: '/v1/sms/send/code',
     data: { phone },
   })
 }

 // ==================== 用户登录 ====================
 /**
  * 用户登录
  *
  * @template T - 响应数据类型
  * @param phone - 用户名/手机号
  * @param code - 密码/验证码
  * @returns Promise<T> - 登录结果
  */
 export function login<T>(phone: string, code: string) {
   return post<T>({
     url: '/v1/user/login',
     // 用户名和密码字段，登录类型为1
     data: { user_name: phone, pwd: code, type: 1 },
   })
 }

 // ==================== SSE 流式请求（Fetch实现） ====================
 /**
  * 使用Fetch API实现SSE流式请求
  *
  * 与Axios相比，Fetch可以更好地处理流式响应
  *
  * @template T - 响应数据类型
  * @param url - API地址
  * @param data - 请求数据
  * @param options - 选项配置
  * @param options.signal - AbortSignal，用于取消请求
  * @param options.onMessage - 接收到消息的回调
  * @param options.onError - 错误回调
  * @param options.onDone - 请求完成的回调
  * @returns Promise<void>
  */
 export function fetchChatAPISSE<T = any>(
   url: string,
   data: any,
   options?: {
     signal?: AbortSignal
     onMessage?: (data: T) => void
     onError?: (error: any) => void
     onDone?: () => void
   }
 ): Promise<void> {
   return new Promise((resolve, reject) => {
     // 解构回调函数，提供空函数作为默认值
     const { signal, onMessage, onError, onDone } = options || {}

     // 构建请求头
     const headers: Record<string, string> = {
       'Content-Type': 'application/json',
     }

     // 从Cookie获取访问令牌
     const access_token = getCookieValue('sso_0voice_access_token')
     if (access_token)
       headers.Authorization = access_token

     // 发送Fetch请求
     fetch(url, {
       method: 'POST',
       headers,
       body: JSON.stringify(data),
       signal,
     })
       // 处理响应
       .then(response => {
         // 检查HTTP状态码
         if (!response.ok) {
           throw new Error(`HTTP ${response.status}: ${response.statusText}`)
         }

         // 获取响应体的读取器
         const reader = response.body?.getReader()
         const decoder = new TextDecoder()
         let buffer = ''

         // 递归读取数据流
         const read = () => {
           reader?.read().then(({ done, value }) => {
             // 流结束
             if (done) {
               // 处理剩余缓冲数据
               if (buffer.trim()) {
                 const parsed = parseSSELine(buffer)
                 if (parsed && parsed.event === 'message') {
                   onMessage?.(parsed.data)
                 }
               }
               onDone?.()
               resolve()
               return
             }

             // 解码并追加到缓冲区
             buffer += decoder.decode(value, { stream: true })

             // 按双换行符分割（每个SSE消息以\n\n结束）
             const messages = buffer.split('\n\n')
             buffer = messages.pop() || ''

             // 处理每条消息
             for (const message of messages) {
               const parsed = parseSSELine(message)
               if (!parsed) continue

               // 根据事件类型处理
               switch (parsed.event) {
                 case 'start':
                   // 开始事件
                   break
                 case 'done':
                   // 完成事件
                   onDone?.()
                   resolve()
                   return
                 case 'error':
                   // 错误事件
                   onError?.(parsed.data)
                   break
                 case 'message':
                 default:
                   // 消息事件
                   onMessage?.(parsed.data)
               }
             }

             // 继续读取下一块数据
             read()
           })
         }

         read()
       })
       // 错误处理
       .catch(err => {
         // 如果是取消请求，不当作错误处理
         if (err.name === 'AbortError') {
           onDone?.()
           resolve()
         } else {
           onError?.(err)
           reject(err)
         }
       })
   })
 }

 // ==================== SSE消息解析 ====================
 /**
  * 解析单条SSE消息
  *
  * SSE格式：
  * event: message
  * data: {"text": "Hello", "id": "123"}
  *
  * @param line - 原始消息字符串
  * @returns 解析后的事件类型和数据，或null（解析失败）
  */
 function parseSSELine(line: string): { event: string; data: any } | null {
   let event = 'message'  // 默认事件类型
   let dataStr = ''

   // 解析每行
   for (const l of line.split('\n')) {
     // 解析event行
     if (l.startsWith('event:')) {
       event = l.slice(6).trim()
     }
     // 解析data行
     else if (l.startsWith('data:')) {
       dataStr = l.slice(5).trim()
     }
   }

   // 没有数据
   if (!dataStr) return null

   // 尝试解析JSON
   try {
     return {
       event,
       data: JSON.parse(dataStr),
     }
   } catch {
     return null
   }
 }
