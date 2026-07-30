# SARSA 与 Q 学习：一份零基础友好讲解

> 本文档面向**完全没接触过强化学习**的读者，目标是把 `deep-learning-from-scratch-4`（《ゼロから作るDeep Learning ❹ 強化学習編》）第 6 章中两个最重要的 TD（时间差分）算法 —— **SARSA** 和 **Q 学习（Q-Learning）** —— 讲清楚、讲明白，并且能让你直接读懂 `ch06/sarsa.py` 和 `ch06/q_learning.py` 这两份源码。

---

## 目录

1. [前置知识：什么是强化学习](#1-前置知识什么是强化学习)
2. [奖励、状态、动作：三个最关键的概念](#2-奖励状态动作三个最关键的概念)
3. [Q 表：智能体的大脑](#3-q-表智能体的大脑)
4. [探索与利用（ε-greedy）](#4-探索与利用ε-greedy)
5. [时间差分（TD）的思想](#5-时间差分td的思想)
6. [SARSA：谨慎的小狐狸](#6-sarsa谨慎的小狐狸)
7. [Q 学习：乐观的小狐狸](#7-q-学习乐观的小狐狸)
8. [SARSA 与 Q 学习：核心差异一览](#8-sarsa-与-q-学习核心差异一览)
9. [结合 ch06 项目代码逐行对照](#9-结合-ch06-项目代码逐行对照)
10. [在 GridWorld 上跑一遍：会看到什么](#10-在-gridworld-上跑一遍会看到什么)
11. [什么时候用哪个？](#11-什么时候用哪个)
12. [常见疑问 Q&A](#12-常见疑问-qa)
13. [自检题](#13-自检题)

---

## 1. 前置知识：什么是强化学习

强化学习（Reinforcement Learning, RL）研究的是这样一类问题：

> 一个**智能体（Agent）** 在一个**环境（Environment）** 中不断**做动作（Action）**，环境会反馈**奖励（Reward）** 和新的**状态（State）**。智能体的目标是学到一套**策略（Policy）**，让它在长期累计能拿到的奖励最大化。

一句话总结：**试错学习**。做对了给糖，做错了挨打，慢慢学会怎么做能拿更多糖。

在本书第 6 章中，我们把环境设成了一个**网格世界（GridWorld）**—— `common/gridworld.py`。它长这样：

```
奖励矩阵 (reward_map):
[[ 0. ,  0. ,  0. ,  1.0],   ← (0,3) 是目标 +1
 [ 0. , None,  0. , -1.0],   ← (1,1) 是墙，  (1,3) 是陷阱 -1
 [ 0. ,  0. ,  0. ,  0. ]]   ← (2,0) 是起点

动作：0=上, 1=下, 2=左, 3=右
```

智能体（一只小狐狸，源代码里就叫 agent）从 `(2,0)` 出发，要绕过墙、躲开陷阱、走到右上角的 `(0,3)` 拿到 +1 的奖励。

---

## 2. 奖励、状态、动作：三个最关键的概念

| 概念 | 英文 | 在 GridWorld 里的含义 |
| --- | --- | --- |
| 状态 | State `s` | 小狐狸当前在哪个格子，例如 `(2,0)` |
| 动作 | Action `a` | 它能往哪走：上/下/左/右（编号 0/1/2/3） |
| 奖励 | Reward `r` | 落到目标格得 +1，掉到陷阱得 -1，其它格得 0 |

智能体走的轨迹（trajectory）就是一条**状态–动作–奖励**的链子：

```
s₀ → a₀ → r₁, s₁ → a₁ → r₂, s₂ → a₂ → r₃, s₃ → ... → sT（终点）
```

目标：让 `G = r₁ + γ·r₂ + γ²·r₃ + ...` 最大化。其中 `γ ∈ [0,1]` 叫做**折扣因子**，表示「明天的糖比今天的糖打多少折」。γ 越接近 1，越有远见；越接近 0，越短视。

---

## 3. Q 表：智能体的大脑

智能体需要回答的核心问题是：

> **我在状态 s，做动作 a，长期来看能拿多少分？**

我们用 `Q(s, a)` 来表示这个数。`Q` 的英文是 **Quality**（价值）。所有 `Q(s, a)` 组成的表就叫 **Q 表**。

在 `sarsa.py` 和 `q_learning.py` 里，Q 表都是这样定义的：

```python
self.Q = defaultdict(lambda: 0)
```

这是一个**默认值为 0** 的字典。键是 `(state, action)` 二元组，值是浮点数。一开始 Q 表全是 0，相当于一张白纸，智能体什么都不知道。

> 关键直觉：**Q 表里的每个数字都是「经验」的沉淀**。智能体走得越多，Q 表就被填得越准确，于是它就越会选高分动作。

---

## 4. 探索与利用（ε-greedy）

在学习阶段，智能体既要去**探索（exploration）**没走过的路，也要**利用（exploitation）**已经发现的好路。最简单的做法是 **ε-greedy**：

```text
掷一个 0~1 之间的随机数 p：
   p < ε   → 随机选一个动作（探索）
   p ≥ ε   → 选 Q 值最大的动作（利用）
```

ε 一般设成 0.1，意味着 10% 的概率随便走、90% 的概率走最优。代码里的实现藏在这个函数里（`common/utils.py`）：

```python
def greedy_probs(Q, state, epsilon=0, action_size=4):
    qs = [Q[(state, action)] for action in range(action_size)]
    max_action = argmax(qs)
    base_prob = epsilon / action_size
    action_probs = {action: base_prob for action in range(action_size)}
    action_probs[max_action] += (1 - epsilon)
    return action_probs
```

解读：

- `base_prob = ε / 4`：每个动作先拿到一份「保底概率」`ε/4`。
- `action_probs[max_action] += (1 - epsilon)`：Q 值最大的那个动作**额外**加 `(1 − ε)`，最终它的概率是 `1 − ε + ε/4 = 1 − 3ε/4`。

举例 ε=0.1：最优动作概率 = 0.925，其它每个动作 = 0.025。

在 `sarsa.py` 中：

```python
self.pi = defaultdict(lambda: random_actions)  # 策略 π（最终用的）
...
self.pi[state] = greedy_probs(self.Q, state, self.epsilon)  # ← ε-greedy
```

⚠️ 注意：`SarsaAgent` 中策略 `pi` 和用来采样的策略是**同一个**（都带 ε-greedy）。而 `QLearningAgent` 中，行为策略 `b` 用 ε-greedy 用于采样；目标策略 `pi` 用 ε=0 的纯贪心用于评估——这正是 Q 学习**离策略**的关键，详见后文。

---

## 5. 时间差分（TD）的思想

TD = **Temporal Difference**，中文「时间差分」。

我们想更新 `Q(s, a)`。最朴素的想法是：等一轮跑完，把整条轨迹的奖励加总得到真实回报 `G`，然后让 `Q(s, a)` 向 `G` 靠拢。这就是**蒙特卡洛（Monte Carlo, MC）**的方法。

但 MC 有个致命缺点：**必须等到回合结束**才能更新。如果任务长得跑几个小时，我们中间啥也学不到。

TD 的聪明之处：**不等回合结束，每走一步就用「我估计的未来得分」来更新当前估计**。这个「我估计的未来得分」就是 `Q(s', a')`——下一步的状态动作对应的 Q 值。

核心公式（一个非常通用的「TD 目标」）：

$$
\text{TD 目标} = r + \gamma \cdot Q(s', a')
$$

$$
Q(s, a) \leftarrow Q(s, a) + \alpha \cdot \big( \text{TD 目标} - Q(s, a) \big)
$$

其中：

- `α`（alpha）：学习率，控制新经验覆盖旧经验的速度。
- `γ`（gamma）：折扣因子，前面说过。
- `TD 目标 - Q(s, a)` 称为 **TD 误差**。

用大白话说：

> **「我原本以为这个状态做这个动作值这么多分；走完一步发现，下一步的状态值这么多分，加上刚拿到的奖励 r，新估计比旧估计多了/少了这么多。我就照这个差距的 α 比例修正一下我的旧估计。」**

到这里，SARSA 和 Q 学习已经是同一类算法的不同变种了。它们的差别只有一个：

> **「下一步用来估计未来的那个 `Q(s', ?)`，到底挑哪个动作去查？」**

---

## 6. SARSA：谨慎的小狐狸

### 名字由来

SARSA 五个字母来自一次转移涉及的**五个元素**：

$$
S_t,\ A_t,\ R_{t+1},\ S_{t+1},\ A_{t+1}
$$

读作「SARS-A」。

### 算法

1. 在状态 `S_t`，**用当前策略 π**（带 ε-greedy）选动作 `A_t`。
2. 执行 `A_t`，环境给出奖励 `R_{t+1}` 和新状态 `S_{t+1}`。
3. 在新状态 `S_{t+1}`，**再用同一个策略 π**（带 ε-greedy）选下一个动作 `A_{t+1}`。
4. 用这五元组做更新：

$$
Q(S_t, A_t) \leftarrow Q(S_t, A_t) + \alpha \big[ R_{t+1} + \gamma \cdot Q(S_{t+1}, A_{t+1}) - Q(S_t, A_t) \big]
$$

5. 真正去执行 `A_{t+1}`，重复。

> **关键：SARSA 在更新时使用的 `Q(S_{t+1}, A_{t+1})` 中的 `A_{t+1}`，就是 ε-greedy 实际采到的动作——可能不是当前 Q 值最大的那个，可能是个随机动作。**

这就是 SARSA 被称作「**在策略（on-policy）**」的原因：

> **它学的是「我当前正在使用的、带着探索的策略 π」的价值。**

### 代码对应

`sarsa.py` 的 `update` 方法（去掉前面收集两帧的逻辑后）核心是这几行：

```python
state, action, reward, done = self.memory[0]
next_state, next_action, _, _ = self.memory[1]
next_q = 0 if done else self.Q[next_state, next_action]   # ← 这里用的是 next_action

target = reward + self.gamma * next_q
self.Q[state, action] += (target - self.Q[state, action]) * self.alpha
self.pi[state] = greedy_probs(self.Q, state, self.epsilon)
```

- `self.memory` 是个容量为 2 的双端队列（`deque(maxlen=2)`），保存最近两步的 `(state, action, reward, done)`，正好凑齐 SARSA 的五元组。
- 如果到终点了（`done=True`），下一步没有 Q 值，`next_q = 0`。

### 一个比喻

SARSA 像一个**谨慎的小狐狸**：

> 「我现在站在悬崖边，根据我过往的经验，下一步应该往左拐。但万一 ε 让我手一抖往右走了呢？我也得把『万一手抖掉下悬崖』这件事考虑进我对『现在这一步』的评价里。」

所以它学到的是**「带着抖动」的最优策略**——会选择**离悬崖边远一点的安全路径**。

---

## 7. Q 学习：乐观的小狐狸

### 算法

Q 学习的更新公式只有一个地方和 SARSA 不同：

$$
Q(S_t, A_t) \leftarrow Q(S_t, A_t) + \alpha \big[ R_{t+1} + \gamma \cdot \max_{a} Q(S_{t+1}, a) - Q(S_t, A_t) \big]
$$

差别就在 `Q(S_{t+1}, A_{t+1})` 被换成了：

$$
\max_{a} Q(S_{t+1}, a)
$$

——也就是「在下一个状态 `S_{t+1}`，**所有动作中 Q 值最大的那一个**」。**不管你 ε-greedy 下一步实际会走哪条**。

> **关键：Q 学习「假装」在下一步做了一个最好的动作——哪怕你实际上是个手抖选手，它也按你「不抖」的最优值来打分。**

这就是 Q 学习被称作「**离策略（off-policy）**」的原因：

> **它学的是「目标策略 π（纯贪心）」的价值，而用「行为策略 b（带 ε-greedy）」去采数据。两者可以分开。**

### 代码对应

`q_learning.py` 的 `update` 方法：

```python
if done:
    next_q_max = 0
else:
    next_qs = [self.Q[next_state, a] for a in range(self.action_size)]
    next_q_max = max(next_qs)                              # ← 这里取 max！

target = reward + self.gamma * next_q_max
self.Q[state, action] += (target - self.Q[state, action]) * self.alpha

self.pi[state] = greedy_probs(self.Q, state, epsilon=0)    # π 是纯贪心
self.b[state] = greedy_probs(self.Q, state, self.epsilon)  # b 是 ε-greedy
```

- `self.pi`：目标策略，ε=0，永远选 Q 最大的那个动作。**这是 Q 学习真正想学到的策略。**
- `self.b`：行为策略，ε=0.1，带探索，用来从环境里采数据。

二者分开，正是 off-policy 的标志。

### 一个比喻

Q 学习像一个**乐观的小狐狸**：

> 「我现在站在悬崖边，根据我过往的经验，下一步应该往左拐。我就假设我**真的**会往左拐（按最优来）。哪怕我手抖走错了，下次再修正，反正我评价的是『不抖的我』。」

所以它学到的最终策略 π 会**贴着悬崖边走最优路径**——它不在乎训练时偶尔抖一下。

---

## 8. SARSA 与 Q 学习：核心差异一览

| 维度 | SARSA | Q 学习 |
| --- | --- | --- |
| 全称 | State-Action-Reward-State-Action | Quality Learning（Q 表示动作价值） |
| 更新目标中的下一动作 | ε-greedy 实际采到的 `A_{t+1}` | `max_a Q(S_{t+1}, a)`，与实际动作无关 |
| 策略类型 | **On-policy（在策略）** | **Off-policy（离策略）** |
| 学习的策略价值 | 「带探索抖动」的策略价值 | 目标策略（纯贪心）的最优价值 |
| 风险环境中的表现 | 更**保守**，会绕开悬崖 | 更**激进**，会贴着悬崖走 |
| 同一段代码里的实现 | `next_q = Q[next_state, next_action]` | `next_q_max = max(Q[next_state, a] for a in actions)` |
| 收敛速度 | 相对慢（噪声更大） | 通常更快（目标更稳定） |
| 项目对应文件 | `ch06/sarsa.py` | `ch06/q_learning.py` |
| 项目对应进阶版 | `ch06/sarsa_off_policy.py` | （无，本质上 Q 学习本身就是 off-policy） |

### 一张图总结

```
                  SARSA                          Q Learning
                  =====                          =========

  S_t --π(ε-greedy)--> A_t      S_t --π(ε-greedy)--> A_t
   │                     │       │                     │
   │                     ▼       │                     ▼
   │                  env 执行   │                  env 执行
   │                     │       │                     │
   │                     ▼       │                     ▼
   │             (R_{t+1}, S_{t+1})                (R_{t+1}, S_{t+1})
   │                     │       │                     │
   ▼                     ▼       ▼                     ▼
  S_{t+1} --π(ε-greedy)--> A_{t+1}                  max_a Q(S_{t+1}, a)
   │                     │       │                     │
   └────► Q(S_{t+1}, A_{t+1})    └────► max_a Q(S_{t+1}, a)
   ↑        ↑                     ↑        ↑
 用了真实采样动作                用了"假设最优"动作
```

---

## 9. 结合 ch06 项目代码逐行对照

### 9.1 SARSA 代码逐行注释（`ch06/sarsa.py`）

```python
class SarsaAgent:
    def __init__(self):
        self.gamma = 0.9      # 折扣因子 γ
        self.alpha = 0.8      # 学习率 α
        self.epsilon = 0.1    # ε-greedy 探索率
        self.action_size = 4  # 4 个动作：上下左右

        random_actions = {0: 0.25, 1: 0.25, 2: 0.25, 3: 0.25}
        self.pi = defaultdict(lambda: random_actions)  # 策略 π（ε-greedy）
        self.Q = defaultdict(lambda: 0)                # Q 表，初值全 0
        self.memory = deque(maxlen=2)                  # 容量 2 的滑动窗口，凑齐 SARS,A

    def get_action(self, state):
        # 按当前策略 π 的概率分布采样一个动作
        action_probs = self.pi[state]
        actions = list(action_probs.keys())
        probs = list(action_probs.values())
        return np.random.choice(actions, p=probs)

    def reset(self):
        self.memory.clear()  # 每个回合开始清空

    def update(self, state, action, reward, done):
        self.memory.append((state, action, reward, done))
        if len(self.memory) < 2:
            return  # 还不到两步，凑不齐 SARSA 五元组，先返回

        # 取最近两步
        state, action, reward, done = self.memory[0]
        next_state, next_action, _, _ = self.memory[1]
        # 注意：next_action 是策略 π 实际采到的（ε-greedy 采样结果）

        # 核心更新
        next_q = 0 if done else self.Q[next_state, next_action]  # SARSA 的灵魂
        target = reward + self.gamma * next_q
        self.Q[state, action] += (target - self.Q[state, action]) * self.alpha

        # 用最新的 Q 表更新该状态的策略
        self.pi[state] = greedy_probs(self.Q, state, self.epsilon)
```

主循环：

```python
env = GridWorld()
agent = SarsaAgent()

episodes = 10000
for episode in range(episodes):
    state = env.reset()
    agent.reset()

    while True:
        action = agent.get_action(state)              # 1) 采样动作
        next_state, reward, done = env.step(action)   # 2) 环境执行

        agent.update(state, action, reward, done)     # 3) 用 SARS,A 更新 Q

        if done:
            agent.update(next_state, None, None, None)  # 4) 回合末：再调一次让 memory 处理收尾
            break
        state = next_state
```

> 第 4 步 `agent.update(next_state, None, None, None)` 会让 `memory` 里有 `(next_state, None, None, None)` 这一条，最终 SARSA 更新时拿到 `done=True`，于是 `next_q=0`，对应「走到终点，不再有未来收益」。

### 9.2 Q 学习代码逐行注释（`ch06/q_learning.py`）

```python
class QLearningAgent:
    def __init__(self):
        self.gamma = 0.9
        self.alpha = 0.8
        self.epsilon = 0.1
        self.action_size = 4

        random_actions = {0: 0.25, 1: 0.25, 2: 0.25, 3: 0.25}
        self.pi = defaultdict(lambda: random_actions)  # 目标策略（ε=0，纯贪心）
        self.b  = defaultdict(lambda: random_actions)  # 行为策略（ε-greedy，用来采样）
        self.Q = defaultdict(lambda: 0)
        # 注意：Q 学习没有 memory，因为它不需要等下一步的动作

    def get_action(self, state):
        # 用行为策略 b 采样动作
        action_probs = self.b[state]
        actions = list(action_probs.keys())
        probs = list(action_probs.values())
        return np.random.choice(actions, p=probs)

    def update(self, state, action, reward, next_state, done):
        if done:
            next_q_max = 0
        else:
            # 在 next_state 上看所有动作，取 Q 最大值 —— 不在乎实际会走哪个
            next_qs = [self.Q[next_state, a] for a in range(self.action_size)]
            next_q_max = max(next_qs)

        target = reward + self.gamma * next_q_max
        self.Q[state, action] += (target - self.Q[state, action]) * self.alpha

        self.pi[state] = greedy_probs(self.Q, state, epsilon=0)   # 目标策略纯贪心
        self.b[state]  = greedy_probs(self.Q, state, self.epsilon)  # 行为策略带探索
```

主循环（**注意 update 的参数不同——Q 学习要立刻拿到 next_state**）：

```python
while True:
    action = agent.get_action(state)
    next_state, reward, done = env.step(action)

    agent.update(state, action, reward, next_state, done)  # 多传一个 next_state
    if done:
        break
    state = next_state
```

### 9.3 对照表：相同点与不同点

| 代码片段 | SARSA | Q 学习 |
| --- | --- | --- |
| Q 表定义 | `self.Q = defaultdict(lambda: 0)` | 一模一样 |
| 行为策略 | `self.pi`（既是采样策略也是更新用的） | `self.b`（仅采样用） |
| 目标策略 | `self.pi`（同上） | `self.pi`，ε=0 |
| 缓存 | `deque(maxlen=2)` 存两步 | 无，直接传 `next_state` |
| 下一动作取值 | `self.Q[next_state, next_action]` | `max(self.Q[next_state, a] for a in ...)` |
| `done` 时 | `next_q = 0` | `next_q_max = 0` |

---

## 10. 在 GridWorld 上跑一遍：会看到什么

在 `common/gridworld.py` 里终点是 `(0,3)` +1，陷阱是 `(1,3)` −1，墙在 `(1,1)`。Q 表学完之后画箭头（`render_q` 会画每个格子上每个动作的 Q 值），你能直接看到小狐狸的策略。

直觉上 SARSA 学到的策略长这样（箭头表示 Q 值最大的方向）：

```
→  →  →  ★(goal)
↑  墙   ↑  ✗(trap)
→  →  →  ↑
```

——**绕开陷阱那一列**。因为它考虑到了「万一 ε 让我不小心掉下去」。

而 Q 学习学到的策略：

```
→  →  →  ★
→  墙  →  ✗
→  →  →  ↑
```

——**贴着陷阱上方走过去**。因为它假设自己会走最优、不抖。

> 这正是「在悬崖边上 SARSA 更保守，Q 学习更激进」的具象化。

---

## 11. 什么时候用哪个？

| 场景 | 推荐 |
| --- | --- |
| 探索阶段出错代价很大（真实机器人、医疗） | **SARSA**，更安全 |
| 仿真环境、采样便宜、追求最快收敛 | **Q 学习**，通常更快 |
| 想复用过往经验（replay buffer）做学习 | **Q 学习**（off-policy 天然支持） |
| 需要严谨的收敛性证明 | **Q 学习**（在表格情形有强收敛保证） |
| 想模拟「人/动物在环境中谨慎试错」 | **SARSA**（更符合心理学直觉） |
| 想做大规模深度 RL | 通常是 Q 学习的衍生品（DQN 等） |

⚠️ SARSA 不是「差」的算法，它和 Q 学习是同一思路下的两个 trade-off：

- **Q 学习：激进优化（可能更快但风险大）**
- **SARSA：保守优化（更稳但可能慢一点）**

---

## 12. 常见疑问 Q&A

### Q1：为什么 Q 学习有 `pi` 和 `b` 两个策略，SARSA 只有一个？

因为 Q 学习是 **off-policy**——它用一个策略（`b`，带探索）去环境里收集数据，但学的是另一个策略（`pi`，纯贪心）的价值。SARSA 是 **on-policy**——它用一个策略（`pi`，带探索）去收集数据，学的也是同一个策略的价值，所以不需要分开。

### Q2：为什么 Q 学习的代码不需要 `deque`？

SARSA 需要等下一步**实际采到的动作** `A_{t+1}` 才能算 `Q(S_{t+1}, A_{t+1})`，所以要把两步 `(S_t, A_t, R, S_{t+1}, A_{t+1})` 攒齐。Q 学习用的是 `max_a Q(S_{t+1}, a)`，只需要 `S_{t+1}`，不需要 `A_{t+1}`，所以单步就能更新。

### Q3：`max` 操作会不会让 Q 学习「过于乐观」？

会。这就是著名的 **max 偏差（max bias）**：

> 「我对 `S_{t+1}` 的每个动作的 Q 值都只是估计，可能有的被高估、有的被低估。但我偏偏选最大值，等于自动把所有动作的高估误差都集中到我学到的 Q 值上。」

解决方法是 **Double Q 学习**——用两个 Q 表交替选动作和评估，把 max 偏差拆开。本书后续章节（DQN）用一些技巧缓解了这个问题。

### Q4：SARSA 也能做成 off-policy 吗？

可以。看项目里的 `ch06/sarsa_off_policy.py`，它引入了**重要性采样比**：

$$
\rho = \frac{\pi(A_{t+1}|S_{t+1})}{b(A_{t+1}|S_{t+1})}
$$

用来纠正「用 b 采的数据估计 π 的价值」的偏差。但实践中效果通常不如直接用 Q 学习。

### Q5：学习率 α、折扣因子 γ、探索率 ε 应该怎么调？

经验值（仅供参考）：

- **α** 在表格情形下可以从 0.5 起步，慢慢降到 0.1 左右。
- **γ** 一般 0.9 ~ 0.99，任务越「长期」越接近 1。
- **ε** 一般 0.05 ~ 0.2；训练后期可以把它**衰减**到 0.01（常用 ϵ-decay 策略）。

---

## 13. 自检题

读完文档，你应该能用自己的话回答：

1. SARSA 名字里五个字母分别代表什么？
2. SARSA 和 Q 学习在更新公式上**唯一**的区别在哪里？
3. 什么叫 on-policy？什么叫 off-policy？分别对应哪个算法？
4. 为什么 Q 学习不需要像 SARSA 那样缓存最近两步？
5. 在悬崖边上，SARSA 和 Q 学习分别会学出什么形状的策略？为什么？
6. `ch06/sarsa.py` 中的 `self.memory = deque(maxlen=2)` 是干什么用的？
7. `ch06/q_learning.py` 中的 `self.pi` 和 `self.b` 的 ε 分别是多少？这反映了什么？
8. 如果你训练一个真实机器人，希望它不要撞墙，你会优先选 SARSA 还是 Q 学习？为什么？

---

## 附：继续学习路线

- **第 5 章 蒙特卡洛（MC）**：另一种不依赖 TD 的方法，要等回合结束才能更新。
- **第 7 章 神经网络 + Q 学习**：Q 表换成神经网络 = DQN 的前身。
- **第 8 章 DQN**：用经验回放和目标网络解决神经网络的「不稳定」问题。
- **第 9 章 策略梯度法**：不再学 Q 表，直接学策略 π。

最后一句话送给你：

> **SARSA 是「一边学自己一边学走路」；Q 学习是「想象一个完美的自己，向它看齐」。两种都是强化学习，但侧重点不同 —— 看你想要什么样的「自己」。**
