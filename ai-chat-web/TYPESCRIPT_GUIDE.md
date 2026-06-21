# TypeScript 语法入门指南

> 基于 ai-chat-web 项目总结 | 适用对象：TypeScript 新手

---

## 目录

1. [项目概述](#1-项目概述)
2. [类型基础](#2-类型基础)
3. [泛型](#3-泛型)
4. [类型守卫](#4-类型守卫)
5. [工具类型](#5-工具类型)
6. [函数类型](#6-函数类型)
7. [模块声明](#7-模块声明)
8. [Vue 3 + TypeScript](#8-vue-3--typescript)
9. [容易混淆的点](#9-容易混淆的点)
10. [新手建议](#10-新手建议)

---

## 1. 项目概述

### 技术栈

- **框架**: Vue 3
- **语言**: TypeScript 4.9.5
- **状态管理**: Pinia
- **构建工具**: Vite
- **UI 库**: Naive UI
- **配置**: 开启严格模式 (`"strict": true`)

### 项目结构

```
src/
├── api/              # API 请求
├── components/        # Vue 组件
├── hooks/            # 组合式函数 (Composables)
├── locales/          # 国际化
├── router/           # 路由
├── store/            # Pinia 状态管理
│   └── modules/      # Store 模块
├── typings/          # 类型声明 (.d.ts)
├── utils/            # 工具函数
│   ├── is/           # 类型判断
│   ├── format/       # 格式化
│   ├── request/      # HTTP 请求
│   └── storage/      # 存储
└── views/            # 页面
```

---

## 2. 类型基础

### 2.1 Interface（接口）

**是什么**: 定义对象结构的契约

```typescript
// src/typings/chat.d.ts
interface Chat {
  dateTime: string      // 必需属性
  text: string
  inversion?: boolean   // 可选属性
  error?: boolean
  loading?: boolean
}
```

**使用示例**:

```typescript
const chat: Chat = {
  dateTime: '2024-01-01',
  text: 'Hello'
}
```

**新手注意**:
- `?:` 表示可选属性（可以不存在）
- `: ` 表示必需属性（必须存在）

---

### 2.2 Type Alias（类型别名）

**是什么**: 给类型起别名，可以定义更灵活的类型

```typescript
// src/store/modules/app/helper.ts
export type Theme = 'light' | 'dark' | 'auto'
export type Language = 'zh-CN' | 'zh-TW' | 'en-US'
```

**使用示例**:

```typescript
const theme: Theme = 'dark'        // ✅ 合法
const theme: Theme = 'purple'     // ❌ 错误，只能是 light/dark/auto
```

---

### 2.3 Enum（枚举）

**是什么**: 一组命名的常量值

```typescript
// 项目中较少使用，这里展示语法
enum Direction {
  Up = 'UP',
  Down = 'DOWN',
  Left = 'LEFT',
  Right = 'RIGHT'
}

const dir: Direction = Direction.Up
```

---

### 2.4 联合类型

**是什么**: 值可以是多种类型之一

```typescript
// 字符串或数字
type StringOrNumber = string | number

// 多个字面量类型
type Status = 'pending' | 'success' | 'error'

// 接口联合
interface SuccessResponse {
  status: 'success'
  data: any
}

interface ErrorResponse {
  status: 'error'
  message: string
}

type Response = SuccessResponse | ErrorResponse
```

---

### 2.5 交叉类型

**是什么**: 将多个类型合并为一个

```typescript
interface A {
  name: string
}

interface B {
  age: number
}

// 合并 A 和 B
type Person = A & B

const person: Person = {
  name: '张三',
  age: 25
}
```

---

### 2.6 Interface vs Type 区别

| 对比项 | interface | type |
|--------|----------|------|
| 定义对象结构 | ✅ | ✅ |
| 定义联合类型 | ❌ | ✅ |
| 定义交叉类型 | ⚠️ 较少用 | ✅ |
| 声明合并 | ✅ | ❌ |
| 可读性 | 更像 OO | 更灵活 |

**建议**:
- 对象结构 → 用 `interface`
- 联合/交叉类型 → 用 `type`

---

## 3. 泛型

### 3.1 泛型函数

**是什么**: 函数参数类型在使用时指定

```typescript
// src/api/index.ts
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

// 使用时指定类型
const result = await fetchChatAPI<ChatResponse>('你好')
// result 的类型是 ChatResponse
```

---

### 3.2 泛型接口

```typescript
// src/utils/storage/local.ts
interface StorageData<T = any> {
  data: T           // data 的类型是 T
  expire: number | null
}

// 使用
const storage: StorageData<string> = {
  data: 'hello',
  expire: null
}
```

---

### 3.3 泛型约束

**是什么**: 限制泛型必须满足某些条件

```typescript
// src/utils/is/index.ts
// T extends number 表示 T 必须是 number 的子类型
export function isNumber<T extends number>(value: T | unknown): value is number {
  return Object.prototype.toString.call(value) === '[object Number]'
}

// 约束必须包含某属性
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key]
}

const name = getProperty({ name: '张三', age: 25 }, 'name')  // string
const age = getProperty({ name: '张三', age: 25 }, 'age')   // number
```

---

### 3.4 泛型默认值

```typescript
// T = any 表示默认值是 any
function identity<T = any>(arg: T): T {
  return arg
}

identity(123)       // T 推断为 number
identity('hello')  // T 推断为 string
identity(true)     // T 推断为 boolean
```

---

## 4. 类型守卫

### 4.1 什么是类型守卫

**类型守卫** 是运行时检查类型的方法，让 TypeScript 能够精确推断类型。

### 4.2 内置类型守卫

```typescript
// typeof - 原始类型
if (typeof value === 'string') {
  console.log(value.toUpperCase())  // value 在这里是 string
}

// instanceof - 类实例
if (obj instanceof Date) {
  console.log(obj.toISOString())    // obj 在这里是 Date
}

// in - 属性存在
if ('name' in obj) {
  console.log(obj.name)             // obj 有 name 属性
}
```

### 4.3 自定义类型守卫

```typescript
// src/utils/is/index.ts
export function isString<T extends string>(value: T | unknown): value is string {
  return Object.prototype.toString.call(value) === '[object String]'
}

export function isArray<T extends any[]>(value: T | unknown): value is T {
  return Object.prototype.toString.call(value) === '[object Array]'
}

export function isFunction<T extends (...args: any[]) => any>(value: T | unknown): value is T {
  return Object.prototype.toString.call(value) === '[object Function]'
}

// 使用
function process(value: string | number | boolean) {
  if (isString(value)) {
    // value 在这里被识别为 string
    console.log(value.toUpperCase())
  }
}
```

---

## 5. 工具类型

### 5.1 Partial\<T\> - 所有属性变可选

```typescript
// src/store/modules/settings/index.ts
interface SettingsState {
  theme: string
  language: string
  fontSize: number
}

// 使用 Partial 定义更新参数
function updateSettings(settings: Partial<SettingsState>) {
  // settings 的所有属性都是可选的
}

updateSettings({ theme: 'dark' })           // 只更新 theme
updateSettings({ theme: 'light', fontSize: 14 })  // 更新多个
```

### 5.2 Required\<T\> - 所有属性变必需

```typescript
interface Config {
  apiUrl?: string
  timeout?: number
}

type FullConfig = Required<Config>
// 等价于
interface FullConfig {
  apiUrl: string
  timeout: number
}
```

### 5.3 Pick\<T, K\> - 选取属性

```typescript
interface User {
  id: number
  name: string
  email: string
  password: string
}

// 只保留 id 和 name
type UserPreview = Pick<User, 'id' | 'name'>
// 等价于
interface UserPreview {
  id: number
  name: string
}
```

### 5.4 Omit\<T, K\> - 排除属性

```typescript
// 排除 password
type UserPublic = Omit<User, 'password'>
// 等价于
interface UserPublic {
  id: number
  name: string
  email: string
}
```

### 5.5 Record\<K, V\> - 键值映射

```typescript
// src/api/index.ts
const headers: Record<string, string> = {
  'Content-Type': 'application/json',
}

headers['Authorization'] = 'Bearer token'  // 任意字符串键
```

### 5.6 Readonly\<T\> - 只读

```typescript
interface Point {
  x: number
  y: number
}

const point: Readonly<Point> = { x: 0, y: 0 }
point.x = 1  // ❌ 错误，不能修改
```

### 5.7 ReturnType\<T\> - 获取函数返回值类型

```typescript
function createUser() {
  return { id: 1, name: '张三' }
}

type User = ReturnType<typeof createUser>
// 等价于
type User = { id: number; name: string }
```

### 5.8 Parameters\<T\> - 获取函数参数类型

```typescript
function greet(name: string, age: number) {
  return `Hello, ${name}, you are ${age}`
}

type GreetParams = Parameters<typeof greet>
// 等价于
type GreetParams = [name: string, age: number]
```

---

## 6. 函数类型

### 6.1 函数类型声明

```typescript
// src/views/chat/hooks/useScroll.ts
interface ScrollReturn {
  scrollRef: Ref<ScrollElement>
  scrollToBottom: () => Promise<void>
  scrollToTop: () => Promise<void>
}

// scrollToBottom 是返回 Promise<void> 的函数
```

### 6.2 函数作为参数

```typescript
type Callback = (data: string) => void

function fetchData(callback: Callback) {
  callback('data')
}
```

### 6.3 箭头函数类型

```typescript
const add: (a: number, b: number) => number = (a, b) => a + b

const handler: (event: MouseEvent) => void = (e) => {
  console.log(e.clientX, e.clientY)
}
```

---

## 7. 模块声明

### 7.1 .d.ts 文件

`.d.ts` 文件用于声明类型，不会被编译成 JavaScript。

```typescript
// src/typings/env.d.ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_GLOB_API_URL: string;
  readonly VITE_APP_API_BASE_URL: string;
}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
```

### 7.2 全局声明

```typescript
// src/typings/global.d.ts
interface Window {
  $loadingBar?: LoadingBarProviderInst
  $dialog?: DialogProviderInst
  $message?: MessageProviderInst
}

// 之后可以直接使用 window.$message
```

### 7.3 declare namespace

```typescript
// src/typings/chat.d.ts
declare namespace Chat {
  interface Chat {
    dateTime: string
    text: string
  }

  interface History {
    title: string
    uuid: number
  }
}

// 使用
const chat: Chat.Chat = { dateTime: '', text: '' }
```

### 7.4 import type

```typescript
// 只导入类型，不导入值（编译时会被移除）
import type { AxiosResponse } from 'axios'
import type { Chat } from '@/typings/chat'

// 运行时导入（导入值）
import axios from 'axios'
```

---

## 8. Vue 3 + TypeScript

### 8.1 Ref 类型

```typescript
// src/views/chat/hooks/useScroll.ts
import { ref } from 'vue'

// 明确指定类型
const scrollRef = ref<HTMLDivElement | null>(null)

// 使用时自动推断
const count = ref(0)  // count 是 Ref<number>
```

### 8.2 Computed 类型

```typescript
// src/hooks/useLanguage.ts
import { computed } from 'vue'
import { useAppStore } from '@/store'

export function useLanguage() {
  const appStore = useAppStore()

  const language = computed(() => {
    switch (appStore.language) {
      case 'en-US':
        return 'English'
      default:
        return '中文'
    }
  })

  return { language }  // language 是 ComputedRef<string>
}
```

### 8.3 Watch 类型

```typescript
import { watch } from 'vue'

// 完整参数
watch(
  () => someRef.value,
  (newValue, oldValue) => {
    console.log(newValue, oldValue)
  },
  {
    immediate: true,    // 立即执行
    deep: true          // 深度监听
  }
)
```

### 8.4 Pinia Store

```typescript
// src/store/modules/chat/index.ts
import { defineStore } from 'pinia'

export const useChatStore = defineStore('chat-store', {
  state: (): Chat.ChatState => ({
    active: null,
    usingContext: true,
    history: [],
    chat: []
  }),

  getters: {
    getChatHistoryByCurrentActive(state: Chat.ChatState) {
      return state.history.find(item => item.uuid === state.active)
    }
  },

  actions: {
    updateChat(uuid: number, index: number, chat: Partial<Chat.Chat>) {
      // ...
    }
  }
})

// 使用
const chatStore = useChatStore()
chatStore.updateChat(1, 0, { text: 'Hello' })
```

### 8.5 Props 类型

```typescript
// Vue 组件
import { defineProps } from 'vue'

// 使用泛型定义 props
const props = defineProps<{
  title: string
  count?: number
  items: string[]
}>()

// 或者使用 withDefaults
const props = withDefaults(defineProps<{
  title: string
  count?: number
}>(), {
  count: 0
})
```

### 8.6 Emit 类型

```typescript
const emit = defineEmits<{
  (e: 'update', value: string): void
  (e: 'delete', id: number): void
}>()

emit('update', 'new value')
emit('delete', 123)
```

---

## 9. 容易混淆的点

### 9.1 `interface` vs `type`

| 场景 | 推荐 | 原因 |
|------|------|------|
| 定义对象结构 | `interface` | 更直观，支持声明合并 |
| 定义联合/交叉类型 | `type` | `interface` 无法实现 |
| 定义函数类型 | `type` | 更简洁 |

```typescript
// ✅ 推荐
interface User {
  name: string
  age: number
}

// ✅ 推荐
type Status = 'pending' | 'success' | 'error'

// ✅ 推荐
type Callback = (data: string) => void
```

---

### 9.2 `T | undefined` vs `T?`

| 写法 | 含义 | 场景 |
|------|------|------|
| `name?: string` | 属性可以不存在 | 对象属性可选 |
| `name: string \| undefined` | 属性存在但值可能是 undefined | 需要显式判断 |

```typescript
interface A {
  name?: string    // name 可以完全不存在
}

interface B {
  name: string | undefined  // name 必须存在，但值是 undefined
}

const a: A = {}              // ✅
const b: B = { name: undefined }  // ✅
```

---

### 9.3 `value is Type` vs `as Type`

| 语法 | 作用 | 场景 |
|------|------|------|
| `value is Type` | 类型守卫，返回 boolean | 条件分支中缩小类型 |
| `as Type` | 类型断言，强制转换 | 已知类型但编译器不知道 |

```typescript
// ✅ 推荐：使用类型守卫
if (isString(value)) {
  console.log(value.toUpperCase())  // value 是 string
}

// ⚠️ 谨慎使用：类型断言
const str = value as string  // 强制告诉编译器这是 string
```

---

### 9.4 `import` vs `import type`

```typescript
// 导入值（运行时需要）
import axios from 'axios'

// 导入类型（编译时删除）
import type { AxiosResponse } from 'axios'
import type { User } from '@/types'

// ✅ 推荐：同时使用
import axios from 'axios'
import type { AxiosResponse } from 'axios'
```

---

### 9.5 `any` vs `unknown` vs `never`

| 类型 | 含义 | 安全性 | 使用场景 |
|------|------|--------|----------|
| `any` | 任意类型，关闭类型检查 | ❌ 不安全 | 快速原型 |
| `unknown` | 未知类型，需检查后使用 | ✅ 安全 | 外部数据 |
| `never` | 不可能存在的类型 | ✅ 安全 | 类型穷举 |

```typescript
// any - 不安全
function processAny(value: any) {
  value.toString()  // ❌ 不报错但危险
}

// unknown - 安全
function processUnknown(value: unknown) {
  if (typeof value === 'string') {
    value.toString()  // ✅ 类型守卫后安全
  }
}

// never - 用于穷举
type Shape = Circle | Square | Triangle

function area(shape: Shape): number {
  switch (shape.kind) {
    case 'circle': return Math.PI * shape.radius ** 2
    case 'square': return shape.side ** 2
    case 'triangle': return 0.5 * shape.base * shape.height
    default:
      const _exhaustive: never = shape
      throw new Error('Unknown shape')
  }
}
```

---

## 10. 新手建议

### 10.1 开启严格模式

```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true
  }
}
```

**为什么要开启**:
- 强制检查 null/undefined
- 防止隐式 any
- 更安全的类型推断

---

### 10.2 避免 `any`，使用 `unknown`

```typescript
// ❌ 避免
function process(value: any) {
  return value.toString()
}

// ✅ 推荐
function process(value: unknown) {
  if (typeof value === 'object' && value !== null) {
    return String(value)
  }
  return ''
}
```

---

### 10.3 使用类型守卫而非断言

```typescript
// ❌ 避免
const name = (obj as { name: string }).name

// ✅ 推荐
function hasName(obj: any): obj is { name: string } {
  return 'name' in obj
}

if (hasName(obj)) {
  console.log(obj.name)
}
```

---

### 10.4 类型集中管理

```
src/
├── typings/           # 类型声明
│   ├── global.d.ts    # 全局声明
│   ├── env.d.ts       # 环境变量
│   └── chat.d.ts      # 业务类型
├── types/             # 类型定义
│   └── user.ts
└── store/             # Store 中也可定义类型
```

---

### 10.5 善用泛型默认值

```typescript
// ❌ 每次都要指定类型
function getFirst<T>(arr: T[]): T {
  return arr[0]
}
const num = getFirst<number>([1, 2, 3])

// ✅ 使用默认值
function getFirst<T = any>(arr: T[]): T {
  return arr[0]
}
const num = getFirst([1, 2, 3])  // 自动推断为 number
```

---

### 10.6 常用类型速查

```typescript
// 字符串
const name: string = '张三'

// 数字
const age: number = 25

// 布尔
const isActive: boolean = true

// 数组
const nums: number[] = [1, 2, 3]
const names: Array<string> = ['a', 'b']

// 对象
const user: { name: string; age: number } = { name: '张三', age: 25 }

// 函数
const add: (a: number, b: number) => number = (a, b) => a + b

// Promise
const fetchUser = (): Promise<User> => {
  return Promise.resolve({ name: '张三' })
}

// 回调
const onClick: (event: MouseEvent) => void = (e) => {
  console.log(e.clientX)
}
```

---

## 附录：项目 tsconfig.json 解读

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "module": "ESNext",
    "target": "ESNext",
    "lib": ["DOM", "ESNext"],
    "strict": true,                      // ✅ 严格模式
    "esModuleInterop": true,              // 允许合成默认导入
    "allowSyntheticDefaultImports": true,
    "jsx": "preserve",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "noUnusedLocals": true,              // 检查未使用变量
    "strictNullChecks": true,            // 严格 null 检查
    "forceConsistentCasingInFileNames": true,
    "skipLibCheck": true,                // 跳过库类型检查
    "paths": {
      "@/*": ["./src/*"]                 // 路径别名
    },
    "types": ["vite/client", "node", "naive-ui/volar"]
  }
}
```

---

## 总结

| 分类 | 核心概念 | 关键字 |
|------|----------|--------|
| 类型基础 | 接口、类型别名、联合类型 | `interface`, `type`, `\|`, `&` |
| 泛型 | 通用类型参数 | `<T>`, `<T = any>`, `extends` |
| 类型守卫 | 运行时类型检查 | `value is Type`, `typeof`, `instanceof` |
| 工具类型 | 内置类型转换 | `Partial`, `Pick`, `Omit`, `Record` |
| 函数类型 | 参数和返回值类型 | `(a: T) => U` |
| 模块声明 | 全局类型定义 | `declare`, `.d.ts` |
| Vue + TS | 组合式 API 类型 | `ref<T>()`, `computed()` |

---

*文档生成时间: 2026-06-21*
*基于 ai-chat-web 项目分析*
