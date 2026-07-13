# 公开演示站点爬虫框架使用指南

本指南基于 `crawler_spa_demo` 项目，提供一套可扩展的浏览器自动化爬虫框架说明。
当前默认目标站点为明确允许爬虫练习的公开站点：[books.toscrape.com](https://books.toscrape.com/)。

> 请遵守目标站点的 `robots.txt`、用户协议及适用法律法规，仅用于学习和技术验证。

---

## 1. 项目结构

```
crawler_spa_demo/
├── requirements.txt
├── src/
│   ├── settings.py
│   ├── browser/
│   │   └── page.py
│   ├── extractors/
│   │   └── schema.py
│   ├── models/
│   │   └── item.py
│   ├── pipelines/
│   │   ├── csv_pipeline.py
│   │   └── json_pipeline.py
│   └── run_spider.py
└── output/
    ├── books.csv
    └── books.jsonl
```

核心模块职责：
- `src/browser/page.py`：封装 Playwright 浏览器、页面跳转、限速控制
- `src/extractors/schema.py`：列表页和详情页字段抽取
- `src/models/item.py`：统一数据模型
- `src/pipelines/`：数据导出（CSV / JSONL）
- `src/settings.py`：基础配置项

---

## 2. 环境准备

- Python 3.10+
- pip
- Playwright Chromium

安装依赖：

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

---

## 3. 运行方式

推荐使用模块方式运行，避免 `src` 导入路径问题：

```bash
cd F:\GOMaster\agent\crawler_spa_demo
python -m src.run_spider
```

---

## 4. 配置说明

文件：`src/settings.py`

| 字段 | 说明 | 默认值 |
| --- | --- | --- |
| `BASE_URL` | 目标站点根地址 | `https://books.toscrape.com/` |
| `START_CATEGORY` | 要抓取的主/小页签分类名 | `Travel` |
| `MAX_PAGES` | 该分类下最大分页数 | `2` |
| `OUTPUT_DIR` | 输出目录 | `output` |
| `POLITENESS_DELAY_SECONDS` | 请求间隔秒数 | `1.0` |

建议先调小 `MAX_PAGES` 做验证，再逐步扩大范围。

---

## 5. 输出字段

默认导出两种格式：

- `output/books.csv`
- `output/books.jsonl`

每条记录字段：

- `title`：书名
- `price`：价格
- `availability`：库存状态
- `rating`：评分
- `product_url`：详情页地址
- `source_category`：来源分类
- `source_url`：来源列表页
- `crawled_at`：抓取时间（UTC ISO8601）
- `description`：书籍描述
- `upc`：UPC
- `product_type`：产品类型
- `tax`：税费
- `number_of_reviews`：评论数

---

## 6. 扩展指南

### 6.1 切换分类

修改 `src/settings.py`：

```python
START_CATEGORY = "Fiction"
MAX_PAGES = 5
```

若需抓取多个分类，可在 `src/run_spider.py` 内改为遍历配置列表。

### 6.2 更换目标站点

当前框架为“列表页 + 详情页”结构设计。更换站点时通常需要修改：
- `src/extractors/schema.py` 中的选择器
- `src/settings.py` 中的 URL 和分页规则
- 若站点为 SPA 或需要等待特定请求，可扩展 `src/browser/page.py`

### 6.3 增加导出格式

在 `src/pipelines/` 新增 pipeline 类，并在 `src/run_spider.py` 中接入。

### 6.4 增加重试与容错

当前已有基于 `tenacity` 的基础重试；可继续扩展：
- 增加字段缺失兜底逻辑
- 增加页面超时后的刷新/跳过策略
- 增加失败样本写入单独文件

### 6.5 断点续爬

可在 `src/models/item.py` 增加 `status` / `retry_count`，并结合输出目录实现已抓 URL 去重。

---

## 7. 常见问题

- **`ModuleNotFoundError: No module named 'src'`**
  - 请使用 `python -m src.run_spider`，不要直接 `python src/run_spider.py`。

- **浏览器下载慢或失败**
  - 可设置镜像源或代理后重试 `python -m playwright install chromium`。

- **列表页分页规则变化**
  - 请检查 `next_page_exists` 和 `extract_list_items` 的选择器是否仍适用。

---

## 8. 合规与建议

- 仅用于可公开访问且明确允许爬取的站点。
- 控制请求频率，避免对站点造成压力。
- 如目标站点提供官方 API，优先使用 API。
