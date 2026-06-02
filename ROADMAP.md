# 🤖 AI 情报站 — 升级路线图

> 共 18 项，按依赖关系和价值密度分为 6 个阶段。

---

## 📋 总览

```
Phase 1: 工程基座     ██████████░░░░░░░░░░  (3 项, ~2 周)
Phase 2: 内容深度     ░░░░░░░░░░████████░░░░  (5 项, ~3 周)
Phase 3: 知识图谱     ░░░░░░░░░░░░░░░░████░░  (2 项, ~2 周)
Phase 4: 信源扩展     ░░░░░░░░░░░░░░░░░░░░██  (2 项, ~2 周)
Phase 5: 前端升级     ░░░░░░░░░░░░░░░░░░░░██  (5 项, ~3 周)
Phase 6: 分发运营     ░░░░░░░░░░░░░░░░░░░░░█  (1 项, ~1 周)
```

---

## Phase 1: 工程基础设施 🏗️

> **目标：** 为所有后续功能打好数据地基。当前 `raw.json → latest.json` 是一条隐式的单线，需要变成可控、可观测、可扩展的 Pipeline。

### #26 多阶段 Pipeline

**现状：** 采集 → LLM 精选+翻译 → 发布，三个步骤耦合在一个 cron job 里。

**改造：** 拆成独立可复用的阶段，每个阶段有明确的输入/输出：

```
采集 → 清洗 → 去重 → 分类打分 → 精选 → 翻译 → 发布
  │       │       │        │        │        │        │
  └─── raw.json ──┘        │        │        │        │
                           └── scored.json ──┘        │
                                    └── curated.json ──┘
                                              └── latest.json
```

- 每个阶段一个 Python 模块，接受 stdin/文件输入，输出到下一阶段
- 可单独运行、单独调试
- cron job 串联所有阶段

### #10 SQLite / 向量数据库

**现状：** 全量 JSON 文件，没有查询能力。

**改造：**
- 用 SQLite 存储所有文章（`title, link, summary, source, category, published, content_hash`）
- FTS5 全文索引（中英文混合搜索）
- 可选：sqlite-vec 做轻量向量存储（用于语义搜索 + 话题聚类）
- 保留 JSON 导出（给前端消费），SQLite 是主存储

**技术选型：**
- `sqlite-utils` — 建表/导入/查询的 Python 工具
- `sqlite-vec` — 免编译的向量扩展，在 SQLite 内做 embedding 搜索

### #30 数据仪表盘

**目标：** 一个内部 HTML 页面（或者直接接在现有站点 `/dashboard`），展示：

- 每日采集量趋势折线图
- 信源健康度（成功率、延迟）
- 各分类文章分布
- 精选覆盖率
- Pipeline 各阶段耗时

**技术选型：** Chart.js（和前端技术栈一致），数据从 SQLite 查询 JSON API。

---

## Phase 2: 内容深度升级 ✍️ ✅ (2026-06-02)

> **目标：** 从「翻译搬运」变成「分析洞察」，建立内容壁垒。
> **状态：** ✅ 完成

### #27 质量评分 ✅

**评分维度：** (Phase 1 已实现于 `scripts/pipeline/scorer.py`)

| 维度 | 权重 | 说明 |
|------|------|------|
| 信源权威度 | 25% | ArXiv / OpenAI Blog > TechCrunch > 雷锋网 |
| 时效性 | 20% | 越新分越高，超过 7 天衰减 |
| 技术深度 | 30% | 字数、技术术语密度 |
| 相关性 | 25% | 标题/摘要与 AI 核心领域的语义匹配度 |

- 评分在 Pipeline 的 scorer 阶段完成
- 精选阶段用评分 Top 20 作为候选

### #5 「这为什么重要」 ✅

- curator.py prompt 增加 `why_it_matters` 字段
- 前端 `.article-why` 样式展示（💡 橙色高亮）
- cron job 每日自动生成

### #3 论文深度解读 ✅

- Scanner 自动识别 ArXiv 论文链接，标记 `is_paper` + 提取 `paper_id`
- `scripts/pipeline/paper_analyzer.py` — 结构化提取 prompt
- DB 字段：`paper_method`, `paper_benchmark`, `paper_takeaway`
- cron job Step 3 每日处理新论文

### #2 每周深度简报 ✅

- `scripts/pipeline/weekly_report.py` — 每周数据汇总 + LLM prompt 生成
- Cron job: 每周日 10:00 自动运行
- 输出：`data/weekly/{date}.md` Markdown 分析文章

### #1 趋势分析 ✅

- `scripts/pipeline/trends.py` — 35 个 AI 关键词频率追踪
- 7 天滑动窗口，对比上周期 → 计算变化百分比
- 分类：🚀飙升 / 📈上升 / 📉下降 / 🔻下滑 / ➡️平稳
- 仪表盘新增 `🔥 关键词趋势` 模块

**实现：** 统计层 + 展示层

- 统计：SQLite 查询近 7/30 天的热词频率（从标题+摘要提取关键词）
- 对比：本周 vs 上周关键词变化，自动标注「飙升」「下降」「新出现」
- 展示：前端首页增加一个「趋势热力图」模块（关键词云 + 趋势箭头）

---

## Phase 3: 知识图谱 & 追踪 🕸️ ✅ (2026-06-02)

> **目标：** 让数据之间建立关联，从「文章列表」变成「可查询的知识网络」。
> **状态：** ✅ 完成

### #7 模型追踪器 ✅

- `models` + `model_benchmarks` 两张新表
- `scripts/pipeline/model_tracker.py` — LLM 从文章中提取模型名称、提供方、Benchmark 分数、参数规模
- `leaderboard.html` — 排行榜页面，按模型展示 Benchmark 分数
- `data/leaderboard.json` — 前端数据源，publisher 自动导出
- cron job Step 4 每日自动提取

### #8 论文-代码链接 ✅

- `scripts/pipeline/paper_code_link.py` — GitHub Search API 双策略匹配
  - 策略 1: 精确搜索 ArXiv ID
  - 策略 2: 关键词搜索论文标题
- 结果写入 `articles.github_repo` 字段
- 支持 GitHub token 认证（提高速率限制）
- cron job Step 5 每日自动关联
- 匹配结果存入 SQLite（`paper_id → repo_url, stars, last_commit`）
- 前端论文卡片显示「💻 代码仓库」链接

---

## Phase 4: 信源扩展 📡

> **目标：** 扩充信息覆盖面，尤其是中文和开源动态。

### #16 微信公众号

**目标源：** 机器之心、量子位、新智元、AI 科技评论等

**技术挑战：** 微信没有公开 RSS。方案：

1. **WeRSS / Feeddd** — 第三方 RSS 桥接服务（有现成的公众号 RSS）
2. **搜狗微信搜索** — 抓取搜索结果页（不稳定，不推荐）
3. **手动 RSS 维护** — 找一个稳定提供公众号 RSS 的服务，配置进 SOURCES 列表

**推荐方案 1**，集成进 `rss_scanner.py` 和普通 RSS 源统一处理。

### #20 GitHub Trending

- 对 GitHub Trending 的 AI/ML 仓库做每日快照
- 方法：`https://github.com/trending?since=daily` 抓取，筛选语言和 topics（python, machine-learning, deep-learning, llm）
- 存入 SQLite 的独立表
- 与论文-代码链接交叉关联：如果一篇 ArXiv 论文的代码仓库上了 Trending，高亮标记

---

## Phase 5: 前端体验升级 🎨

> **目标：** 从「能看」变成「好用、好看、想收藏」。

### #11 全文搜索

- SQLite FTS5 提供后端搜索能力
- 前端搜索框，支持中英文
- 搜索范围：标题 + 摘要 + 来源
- 结果按相关度排序，高亮匹配词
- 可以用 `pagefind` 做静态站内搜索（零后端，搜索索引在构建时生成）

**技术选型：** Pagefind — 专为静态站设计的全文搜索，构建索引导入 HTML 即可。

### #12 时间线视图

- 可视化展示文章发布时间线
- 水平时间轴 + 文章卡片
- 可拖动、缩放（类似 Google News 时间线）
- 颜色按分类区分

**技术选型：** vis-timeline 或自建 light 版本（Chart.js 也可以做时间线）。

### #13 话题聚类可视化

- 用 embedding（sqlite-vec）对文章做聚类
- 降维到 2D（t-SNE / UMAP）
- D3.js 或 ECharts 散点图，颜色=分类，大小=热度
- 悬停显示文章标题

### #14 阅读历史 + 偏好

- localStorage 存储用户点击过的文章 ID
- 已读文章在列表中淡化显示
- 「继续阅读」模块 — 快速回到上次浏览位置
- 可选：「收藏」功能

### #15 移动端 PWA

- 添加 `manifest.json` + Service Worker
- 离线缓存：已加载的文章可离线阅读
- 可添加到手机主屏幕，体验接近原生 App
- 图标 + 启动画面

---

## Phase 6: 分发 & 运营 🚀

### #22 Telegram 频道

- 创建 Telegram 频道（如 `@ai_intel_daily`）
- 每日 cron 任务完成后自动推送：
  - **模式 A（简洁版）：** 推送 10 条精选的标题 + 链接（适合频道）
  - **模式 B（深度版）：** 推送 Top 3 + 深度解读摘要
- 利用现有的 `send_message` 能力，直接发到 Telegram

**实现：** 在 Pipeline 的「发布」阶段增加 Telegram 推送步骤。

---

## 📅 建议时间线

| 周次 | 阶段 | 交付物 |
|------|------|--------|
| W1-2 | Phase 1 | SQLite 存储 + Pipeline 重构 + 内部仪表盘 |
| W3-5 | Phase 2 | 质量评分上线 + Why it matters + 论文深度解读 + 趋势热力图 |
| W5-6 | Phase 2 收尾 | 每周简报自动生成 |
| W7-8 | Phase 3 | 模型追踪器 + 论文-代码关联 |
| W9-10 | Phase 4 | 微信公众号 + GitHub Trending |
| W11-13 | Phase 5 | 全文搜索 + 时间线 + 聚类图 + PWA + 阅读历史 |
| W14 | Phase 6 | Telegram 频道推送 |

**总计：约 14 周（3.5 个月）**，每周投入取决于你的节奏，可按需压缩或拉长。

---

## 🎯 核心原则

- **渐进式交付：** 每完成一个阶段就上线，不搞大爆炸发布
- **数据驱动：** 所有新功能的数据基础是 Phase 1 的 SQLite + Pipeline
- **复用第一：** 前端尽量用原生 JS + 少量库，保持 GitHub Pages 的零后端优势
- **中文优先：** 所有 LLM 生成的摘要、解读、简报输出中文
