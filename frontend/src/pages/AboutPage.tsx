import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { ICON } from '../lib/icons'
import { FadeIn, StaggerContainer } from '../components/Animations'
import { CardSkeleton } from '../components/Skeleton'

interface SourceInfo {
  name: string
  category: string
  status: string
  last_success: string
  article_count_last: number
}

const PIPELINE_STEPS = [
  { icon: ICON.satelliteDish, title: '采集 (Scanner)', desc: '每 6 小时从 16 个信源抓取 RSS/API，含 arXiv、顶级 AI 实验室博客、Hacker News、Reddit、中文技术媒体' },
  { icon: ICON.filter, title: '去重 & 评分 (Dedup + Scorer)', desc: '标题语义去重 + 四维打分：权威度、时效性、深度、相关性，每篇 0-100 分' },
  { icon: ICON.robot, title: '精选 & 翻译 (Curator)', desc: 'LLM 从 Top 20 中精选 10-15 篇，生成中文标题、摘要和「为什么重要」解读' },
  { icon: ICON.upload, title: '发布 (Publisher)', desc: '导出 JSON → 提交 GitHub → GitHub Pages 自动部署，全程 < 2 分钟' },
]

const TECH_STACK = [
  { label: '前端', value: 'React 19 + TypeScript + Tailwind CSS v4 + Vite' },
  { label: '图表', value: 'Recharts' },
  { label: '后端 Pipeline', value: 'Python 3 + SQLite' },
  { label: 'LLM', value: 'DeepSeek (策展) / 可替换' },
  { label: '部署', value: 'GitHub Pages + Cloudflare DNS' },
  { label: '定时任务', value: 'Hermes Cron (每 6h 扫描，每 24h 周报)' },
]

const CAT_LABELS: Record<string, string> = {
  'AI Lab': 'AI 实验室',
  'Paper': '学术论文',
  'Blog': '技术博客',
  'Community': '社区动态',
  'Discussion': '技术讨论',
  '中文媒体': '中文媒体',
}

export function AboutPage() {
  const [sources, setSources] = useState<SourceInfo[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/stats.json`)
      .then(r => r.json())
      .then(data => setSources(data.source_health || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const cats = [...new Set(sources.map(s => s.category))]
  const healthy = sources.filter(s => s.status === 'healthy').length

  return (
    <div className="space-y-10 max-w-3xl mx-auto">
      {/* Hero */}
      <FadeIn>
        <div className="text-center py-6">
          <h1 className="text-3xl font-bold text-text-primary">关于 AllOfAI</h1>
          <p className="mt-3 text-text-secondary max-w-xl mx-auto leading-relaxed">
            一个自动化的 AI 技术情报站点。
            每天从全球 16 个信源抓取最新动态，由 LLM 精选最重要的内容并翻译成中文，
            帮你 5 分钟了解 AI 行业正在发生什么。
          </p>
        </div>
      </FadeIn>

      {/* Pipeline */}
      <FadeIn delay={0.05}>
        <section>
          <h2 className="text-xl font-semibold text-text-primary mb-5 flex items-center gap-2">
            <FontAwesomeIcon icon={ICON.gear} className="text-accent" />
            工作流程
          </h2>
          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-border-muted hidden md:block" />
            <div className="space-y-4">
              {PIPELINE_STEPS.map((step, i) => (
                <div key={i} className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-accent-muted border border-accent/20 flex items-center justify-center z-10">
                    <FontAwesomeIcon icon={step.icon} className="text-accent text-xs" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-text-primary text-sm">{step.title}</h3>
                    <p className="mt-1 text-sm text-text-secondary leading-relaxed">{step.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </FadeIn>

      {/* Update frequency */}
      <FadeIn delay={0.1}>
        <div className="bg-bg-card border border-border-muted rounded-xl p-5">
          <h2 className="text-lg font-semibold text-text-primary mb-3 flex items-center gap-2">
            <FontAwesomeIcon icon={ICON.timeline} className="text-accent" />
            更新频率
          </h2>
          <div className="space-y-2 text-sm text-text-secondary">
            <p><span className="text-text-primary font-medium">文章扫描：</span>每 6 小时一次（00:00 / 06:00 / 12:00 / 18:00 UTC）</p>
            <p><span className="text-text-primary font-medium">LLM 精选：</span>每次扫描后自动执行</p>
            <p><span className="text-text-primary font-medium">周报：</span>每周一生成，回顾过去 7 天重点</p>
            <p><span className="text-text-primary font-medium">GitHub Top 5：</span>每日 08:30 更新</p>
            <p><span className="text-text-primary font-medium">模型排行榜：</span>每日随扫描更新</p>
          </div>
        </div>
      </FadeIn>

      {/* Sources */}
      <FadeIn delay={0.15}>
        <section>
          <h2 className="text-xl font-semibold text-text-primary mb-1 flex items-center gap-2">
            <FontAwesomeIcon icon={ICON.satelliteDish} className="text-accent" />
            信源列表
          </h2>
          <p className="text-sm text-text-muted mb-4">
            {loading ? '加载中...' : `${sources.length} 个信源 · ${healthy} 个健康`}
          </p>

          {loading ? (
            <div className="space-y-3">
              <CardSkeleton /><CardSkeleton />
            </div>
          ) : (
            <StaggerContainer className="space-y-5">
              {cats.map(cat => {
                const catSources = sources.filter(s => s.category === cat)
                if (!catSources.length) return null
                const catHealthy = catSources.filter(s => s.status === 'healthy').length
                return (
                  <div key={cat}>
                    <h3 className="text-sm font-medium text-text-primary mb-2 flex items-center gap-2">
                      <FontAwesomeIcon icon={ICON.folder} className="text-text-muted text-xs" />
                      {CAT_LABELS[cat] || cat}
                      <span className="text-xs text-text-muted">
                        {catSources.length} 源 · {catHealthy} 正常
                      </span>
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                      {catSources.map(s => (
                        <div
                          key={s.name}
                          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-bg-secondary/50 text-sm"
                        >
                          <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                            s.status === 'healthy' ? 'bg-green' :
                            s.status === 'degraded' ? 'bg-amber' : 'bg-red'
                          }`} />
                          <span className="text-text-primary truncate">{s.name}</span>
                          <span className="text-xs text-text-muted ml-auto flex-shrink-0">
                            {s.article_count_last ?? 0}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
            </StaggerContainer>
          )}
        </section>
      </FadeIn>

      {/* Tech Stack */}
      <FadeIn delay={0.2}>
        <div className="bg-bg-card border border-border-muted rounded-xl p-5">
          <h2 className="text-lg font-semibold text-text-primary mb-3 flex items-center gap-2">
            <FontAwesomeIcon icon={ICON.code} className="text-accent" />
            技术栈
          </h2>
          <dl className="space-y-2 text-sm">
            {TECH_STACK.map(t => (
              <div key={t.label} className="flex gap-3">
                <dt className="text-text-muted w-24 flex-shrink-0">{t.label}</dt>
                <dd className="text-text-secondary">{t.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </FadeIn>

      {/* Footer note */}
      <FadeIn delay={0.25}>
        <p className="text-center text-sm text-text-muted pb-8">
          项目开源在{' '}
          <a
            href="https://github.com/badb0ttle/fine-grained"
            target="_blank"
            rel="noopener noreferrer"
            className="text-accent hover:underline"
          >
            GitHub
          </a>
          {' · '}
          <a href="/rss.xml" className="text-accent hover:underline">RSS 订阅</a>
        </p>
      </FadeIn>
    </div>
  )
}
