# TypeScript 编程练习题

> 适合 TypeScript 新手的实战练习 | 难度递进

---

## 目录

- [第一阶段：类型基础](#第一阶段类型基础)
- [第二阶段：泛型](#第二阶段泛型)
- [第三阶段：接口与类型](#第三阶段接口与类型)
- [第四阶段：高级类型](#第四阶段高级类型)
- [第五阶段：综合实战](#第五阶段综合实战)

---

## 第一阶段：类型基础

### 练习 1.1：基础类型推断

```typescript
// 问题：以下代码会报错吗？如果会，请修复

const name = "张三"
const age = 25
const isActive = true
const score = [98, 87, 92]
const user = { name: "李四", age: 30 }

// 添加你的代码

console.log(name, age, isActive, score, user)
```

<details>
<summary>参考答案</summary>

```typescript
// 以上代码都不会报错，TypeScript 会自动推断类型
// name: string
// age: number
// isActive: boolean
// score: number[]
// user: { name: string; age: number }
```
</details>

---

### 练习 1.2：显式类型声明

```typescript
// 问题：给以下变量添加类型注解

const title = "TypeScript 教程"
const version = 4.9
const isPublished = true
const tags = ["typescript", "javascript", "web"]
const author = { name: "张三", email: "zhang@example.com" }
const scores = { math: 95, english: 88, chinese: 92 }

// 你的代码
let title: string = "TypeScript 教程"
let version: number = 4.9
let isPublished: boolean = true
let tags: string[] = ["typescript", "javascript", "web"]
let author: { name: string; email: string } = { name: "张三", email: "zhang@example.com" }
let scores: Record<string, number> = { math: 95, english: 88, chinese: 92 }
```

---

### 练习 1.3：函数类型

```typescript
// 问题：补全函数类型

// 1. 求和函数
function sum(a: number, b: number): number {
  return a + b
}

// 2. 打印字符串函数
function printMessage(message: string): void {
  console.log(message)
}

// 3. 回调函数
function fetchData(callback: (data: string) => void) {
  callback("数据加载完成")
}

// 4. 异步函数
async function getUser(): Promise<{ name: string; age: number }> {
  return { name: "张三", age: 25 }
}

// 5. 可选参数和默认参数
function greet(name: string, greeting: string = "你好"): string {
  return `${greeting}, ${name}!`
}
```

---

### 练习 1.4：联合类型

```typescript
// 问题：实现一个函数，参数可以是 string 或 number

function processValue(value: string | number): string {
  // 如果是字符串，转大写
  // 如果是数字，返回其平方

  if (typeof value === "string") {
    return value.toUpperCase()
  }
  return String(value * value)
}

// 测试
console.log(processValue("hello"))  // "HELLO"
console.log(processValue(5))         // "25"
```

---

## 第二阶段：泛型

### 练习 2.1：泛型函数

```typescript
// 问题：实现一个返回数组第一个元素的函数

function firstElement<T>(arr: T[]): T | undefined {
  return arr[0]
}

// 测试
console.log(firstElement([1, 2, 3]))           // 1
console.log(firstElement(["a", "b", "c"]))     // "a"
console.log(firstElement([]))                   // undefined
```

---

### 练习 2.2：泛型约束

```typescript
// 问题：实现一个获取对象属性的函数

function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key]
}

const user = { name: "张三", age: 25, email: "zhang@example.com" }

// 测试
const name = getProperty(user, "name")      // string
const age = getProperty(user, "age")        // number
// getProperty(user, "address")             // 错误：address 不存在
```

---

### 练习 2.3：泛型接口

```typescript
// 问题：定义一个泛型 API 响应接口

interface ApiResponse<T> {
  status: number
  message: string
  data: T
  timestamp: number
}

// 使用
interface User {
  id: number
  name: string
}

const response: ApiResponse<User> = {
  status: 200,
  message: "success",
  data: { id: 1, name: "张三" },
  timestamp: Date.now()
}

console.log(response.data.name)  // "张三"
```

---

### 练习 2.4：泛型类

```typescript
// 问题：实现一个简单的 Stack（栈）类

class Stack<T> {
  private items: T[] = []

  push(item: T): void {
    this.items.push(item)
  }

  pop(): T | undefined {
    return this.items.pop()
  }

  peek(): T | undefined {
    return this.items[this.items.length - 1]
  }

  isEmpty(): boolean {
    return this.items.length === 0
  }

  size(): number {
    return this.items.length
  }
}

// 测试
const numberStack = new Stack<number>()
numberStack.push(1)
numberStack.push(2)
numberStack.push(3)
console.log(numberStack.pop())    // 3
console.log(numberStack.peek())    // 2
console.log(numberStack.size())    // 2

const stringStack = new Stack<string>()
stringStack.push("a")
stringStack.push("b")
console.log(stringStack.pop())    // "b"
```

---

## 第三阶段：接口与类型

### 练习 3.1：接口定义

```typescript
// 问题：定义一个 Person 接口，包含以下属性

interface Person {
  // 姓名（必需）
  // 年龄（必需）
  // 邮箱（可选）
  // 自我介绍方法（返回字符串）
}

const person: Person = {
  name: "张三",
  age: 25,
  introduce(): string {
    return `我是${this.name}，今年${this.age}岁`
  }
}

console.log(person.introduce())  // "我是张三，今年25岁"
```

<details>
<summary>参考答案</summary>

```typescript
interface Person {
  name: string
  age: number
  email?: string
  introduce(): string
}
```
</details>

---

### 练习 3.2：接口继承

```typescript
// 问题：基于 Animal 接口，创建 Dog 接口

interface Animal {
  name: string
  age: number
}

// Dog 继承 Animal，并添加 breed（品种）和 bark() 方法

interface Dog extends Animal {
  breed: string
  bark(): string
}

const dog: Dog = {
  name: "旺财",
  age: 3,
  breed: "金毛",
  bark(): string {
    return "汪汪汪！"
  }
}

console.log(`${dog.name}是${dog.breed}，它会${dog.bark()}`)
// "旺财是金毛，它会汪汪汪！"
```

---

### 练习 3.3：类型别名 vs 接口

```typescript
// 问题：判断以下场景更适合用 type 还是 interface

// 场景1：定义一个坐标点
// 场景2：定义一个可能是一天中某个时段
// 场景3：定义一个用户登录请求
// 场景4：定义一个可能返回字符串或数字的函数

// 你的答案：

// 场景1：interface（对象结构）
interface Point {
  x: number
  y: number
}

// 场景2：type（联合类型）
type TimeOfDay = "morning" | "afternoon" | "evening" | "night"

// 场景3：interface（对象结构，通常需要扩展）
interface LoginRequest {
  username: string
  password: string
}

// 场景4：type（函数类型）
type StringOrNumber = string | number
type TransformFunction = (input: string) => StringOrNumber
```

---

### 练习 3.4：枚举

```typescript
// 问题：定义一个订单状态枚举，并实现状态转换

enum OrderStatus {
  Pending = "PENDING",
  Processing = "PROCESSING",
  Completed = "COMPLETED",
  Cancelled = "CANCELLED"
}

function getStatusText(status: OrderStatus): string {
  switch (status) {
    case OrderStatus.Pending:
      return "待处理"
    case OrderStatus.Processing:
      return "处理中"
    case OrderStatus.Completed:
      return "已完成"
    case OrderStatus.Cancelled:
      return "已取消"
  }
}

// 测试
console.log(getStatusText(OrderStatus.Pending))      // "待处理"
console.log(getStatusText(OrderStatus.Completed))    // "已完成"
```

---

## 第四阶段：高级类型

### 练习 4.1：工具类型 - Partial

```typescript
// 问题：使用 Partial 实现部分更新

interface User {
  id: number
  name: string
  email: string
  age: number
}

// 创建一个更新用户的函数，只更新提供的字段
function updateUser(user: User, updates: Partial<User>): User {
  return { ...user, ...updates }
}

// 测试
const user: User = { id: 1, name: "张三", email: "zhang@example.com", age: 25 }

const updated1 = updateUser(user, { name: "李四" })
console.log(updated1)
// { id: 1, name: "李四", email: "zhang@example.com", age: 25 }

const updated2 = updateUser(user, { email: "li@example.com", age: 30 })
console.log(updated2)
// { id: 1, name: "张三", email: "li@example.com", age: 30 }
```

---

### 练习 4.2：工具类型 - Pick 和 Omit

```typescript
// 问题：使用 Pick 和 Omit

interface Article {
  id: number
  title: string
  content: string
  author: string
  createdAt: Date
  updatedAt: Date
}

// 1. 使用 Pick 创建只包含 id, title, author 的类型
type ArticlePreview = Pick<Article, "id" | "title" | "author">

// 2. 使用 Omit 排除 createdAt 和 updatedAt
type ArticleBase = Omit<Article, "createdAt" | "updatedAt">

// 测试
const preview: ArticlePreview = {
  id: 1,
  title: "TypeScript 入门",
  author: "张三"
}

const base: ArticleBase = {
  id: 2,
  title: "React 指南",
  content: "React 是...",
  author: "李四"
}
```

---

### 练习 4.3：自定义工具类型

```typescript
// 问题：创建一个只读的工具类型 ReadonlyDeep

type ReadonlyDeep<T> = {
  readonly [P in keyof T]: T[P] extends object ? ReadonlyDeep<T[P]> : T[P]
}

interface User {
  name: string
  address: {
    city: string
    street: string
  }
}

type ReadonlyUser = ReadonlyDeep<User>

const user: ReadonlyUser = {
  name: "张三",
  address: {
    city: "北京",
    street: "中关村大街"
  }
}

// user.name = "李四"                    // 错误
// user.address.city = "上海"            // 错误（深层只读）
```

---

### 练习 4.4：条件类型

```typescript
// 问题：实现一个类型，如果 T 是 string 返回 boolean，否则返回 T

type IsString<T> = T extends string ? boolean : T

type A = IsString<string>   // boolean
type B = IsString<number>   // number
type C = IsString<"hello">  // boolean（字面量类型是 string 的子类型）

// 测试
const a: A = true
const b: B = 42
const c: C = true
```

---

### 练习 4.5：类型守卫

```typescript
// 问题：创建类型守卫函数

interface Cat {
  meow(): void
  hunt(): void
}

interface Dog {
  bark(): void
  hunt(): void
}

type Animal = Cat | Dog

// 1. 判断是否是猫
function isCat(animal: Animal): animal is Cat {
  return (animal as Cat).meow !== undefined
}

// 2. 判断是否是狗
function isDog(animal: Animal): animal is Dog {
  return "bark" in animal
}

// 3. 使用类型守卫
function makeSound(animal: Animal) {
  if (isCat(animal)) {
    animal.meow()   // animal 在这里是 Cat
  } else {
    animal.bark()   // animal 在这里是 Dog
  }
}
```

---

## 第五阶段：综合实战

### 练习 5.1：实现一个简易的 HTTP 客户端

```typescript
// 问题：实现一个类型安全的 HTTP 请求函数

interface RequestConfig {
  url: string
  method?: "GET" | "POST" | "PUT" | "DELETE"
  headers?: Record<string, string>
  body?: any
}

interface ApiResponse<T> {
  data: T
  status: number
  message: string
}

// 实现 fetchData 函数
async function fetchData<T>(
  config: RequestConfig
): Promise<ApiResponse<T>> {
  const { url, method = "GET", headers = {}, body } = config

  // 模拟请求
  const response = await fetch(url, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...headers
    },
    body: body ? JSON.stringify(body) : undefined
  })

  const data = await response.json()
  return {
    data: data as T,
    status: response.status,
    message: response.ok ? "success" : "error"
  }
}

// 使用示例
interface User {
  id: number
  name: string
  email: string
}

async function getUser() {
  const response = await fetchData<User>({
    url: "/api/users/1",
    method: "GET"
  })

  console.log(response.data.name)  // 类型安全！
}

async function createUser() {
  const response = await fetchData<User>({
    url: "/api/users",
    method: "POST",
    body: { name: "张三", email: "zhang@example.com" }
  })

  console.log(response.data.id)    // 类型安全！
}
```

---

### 练习 5.2：实现一个事件系统

```typescript
// 问题：实现一个类型安全的事件发射器

type EventMap = Record<string, any>

class EventEmitter<T extends EventMap> {
  private listeners: Partial<{ [K in keyof T]: Array<(data: T[K]) => void> }> = {}

  // 订阅事件
  on<K extends keyof T>(event: K, listener: (data: T[K]) => void): void {
    if (!this.listeners[event]) {
      this.listeners[event] = []
    }
    this.listeners[event]!.push(listener)
  }

  // 发射事件
  emit<K extends keyof T>(event: K, data: T[K]): void {
    const listeners = this.listeners[event]
    if (listeners) {
      listeners.forEach(listener => listener(data))
    }
  }

  // 取消订阅
  off<K extends keyof T>(event: K, listener: (data: T[K]) => void): void {
    const listeners = this.listeners[event]
    if (listeners) {
      const index = listeners.indexOf(listener)
      if (index > -1) {
        listeners.splice(index, 1)
      }
    }
  }
}

// 使用示例
interface AppEvents {
  userLogin: { userId: number; username: string }
  userLogout: { userId: number }
  message: { from: string; content: string }
}

const emitter = new EventEmitter<AppEvents>()

emitter.on("userLogin", (data) => {
  console.log(`${data.username} 登录了`)
})

emitter.on("message", (data) => {
  console.log(`${data.from}: ${data.content}`)
})

emitter.emit("userLogin", { userId: 1, username: "张三" })
// "张三 登录了"

emitter.emit("message", { from: "李四", content: "你好！" })
// "李四: 你好！"
```

---

### 练习 5.3：实现一个表单验证器

```typescript
// 问题：实现一个链式调用的表单验证器

interface ValidationRule<T> {
  validate: (value: T) => boolean
  message: string
}

class FormValidator<T extends Record<string, any>> {
  private rules: Partial<{ [K in keyof T]: ValidationRule<T[K]>[] }> = {}

  // 添加验证规则
  addRule<K extends keyof T>(field: K, rule: ValidationRule<T[K]>): this {
    if (!this.rules[field]) {
      this.rules[field] = []
    }
    this.rules[field]!.push(rule)
    return this
  }

  // 验证表单
  validate(data: T): { valid: boolean; errors: Partial<Record<keyof T, string>> } {
    const errors: Partial<Record<keyof T, string>> = {}

    for (const field in this.rules) {
      const fieldRules = this.rules[field as keyof T]
      const value = data[field]

      for (const rule of fieldRules!) {
        if (!rule.validate(value)) {
          errors[field as keyof T] = rule.message
          break
        }
      }
    }

    return {
      valid: Object.keys(errors).length === 0,
      errors
    }
  }
}

// 使用示例
interface LoginForm {
  username: string
  password: string
  email?: string
}

const validator = new FormValidator<LoginForm>()
  .addRule("username", {
    validate: (v) => v.length >= 3,
    message: "用户名至少3个字符"
  })
  .addRule("username", {
    validate: (v) => /^[a-zA-Z]/.test(v),
    message: "用户名必须以字母开头"
  })
  .addRule("password", {
    validate: (v) => v.length >= 6,
    message: "密码至少6个字符"
  })
  .addRule("email", {
    validate: (v) => !v || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v),
    message: "邮箱格式不正确"
  })

// 测试
const result1 = validator.validate({
  username: "john",
  password: "123456"
})
console.log(result1)
// { valid: true, errors: {} }

const result2 = validator.validate({
  username: "2john",
  password: "123"
})
console.log(result2)
// { valid: false, errors: { username: "用户名必须以字母开头", password: "密码至少6个字符" } }
```

---

## 答案汇总

<details>
<summary>点击查看所有参考答案</summary>

### 1.1 答案
```typescript
// 不会报错，TypeScript 自动推断类型
```

### 1.2 答案
```typescript
let title: string = "TypeScript 教程"
let version: number = 4.9
let isPublished: boolean = true
let tags: string[] = ["typescript", "javascript", "web"]
let author: { name: string; email: string } = { name: "张三", email: "zhang@example.com" }
let scores: Record<string, number> = { math: 95, english: 88, chinese: 92 }
```

### 3.1 答案
```typescript
interface Person {
  name: string
  age: number
  email?: string
  introduce(): string
}
```

### 4.3 答案
```typescript
type ReadonlyDeep<T> = {
  readonly [P in keyof T]: T[P] extends object ? ReadonlyDeep<T[P]> : T[P]
}
```

</details>

---

## 附加挑战

学有余力？可以尝试以下挑战：

1. **实现一个 Promise.all 类型的函数**
2. **实现一个深拷贝工具类型**
3. **实现一个 Discriminated Union 的类型守卫集合**
4. **实现一个响应式状态管理（类似 Pinia）**

---

## 学习资源

- [TypeScript 官方文档](https://www.typescriptlang.org/docs/)
- [TypeScript Deep Dive](https://basarat.gitbook.io/typescript/)
- [TypeScript Playground](https://www.typescriptlang.org/play/)

---

*练习题生成时间: 2026-06-21*
