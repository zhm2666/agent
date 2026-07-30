# 第 6 章：TD / SARSA / Q 学习 — 学习文档

本目录除了源代码，还配套了**中文友好学习文档**：

| 文件 | 说明 |
| --- | --- |
| `ch06说明文档.md` | 零基础友好讲解，含大量自检题 |
| `SARSA与Q学习详解.md` | 上一轮专门讲解 SARSA vs Q 学习的旧文档 |
| `td_eval.py` | 时间差分（TD）评估状态价值 V |
| `sarsa.py` | on-policy TD：SARSA |
| `q_learning.py` | off-policy TD：Q 学习 |
| `q_learning_simple.py` | 极简版 Q 学习 |
| `sarsa_off_policy.py` | off-policy SARSA（带重要性权重）|

👉 **建议从 `ch06说明文档.md` 开始学习。**

## 关键收获

- **TD 自举（bootstrapping）**是核心思想
- **SARSA（谨慎）** vs **Q 学习（乐观）**：悬崖对比
- **on-policy / off-policy** 的区别
- 每步更新 + 不需要模型 = 实用

## 自检题

文档中包含 15 道题，从基础到思考，帮你确认自己真的懂了。
