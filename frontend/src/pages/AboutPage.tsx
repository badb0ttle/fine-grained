import { useEffect, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { ICON } from '../lib/icons'
import { FadeIn, StaggerContainer } from '../components/Animations'
import { CardSkeleton } from '../components/Skeleton'
import { useLocale } from '../lib/LocaleContext'

interface SourceInfo {
  name: string; category: string; status: string
  last_success: string; article_count_last: number
}

const T = {
  aboutAllOfAI: { zh: '关于 AllOfAI', en: 'About AllOfAI' },
  aboutDesc: {
    zh: '一个自动化的 AI 技术情报站点。每天从全球 16 个信源抓取最新动态，由 LLM 精选最重要的内容并翻译成中文，帮你 5 分钟了解 AI 行业正在发生什么。',
    en: 'An automated AI intelligence site. We scan 16+ global sources daily, curate the most important stories with LLM analysis, and help you stay informed about AI in 5 minutes.',
  },
  workflow:    { zh: '工作流程',  en: 'How It Works' },
  frequency:   { zh: '更新频率',  en: 'Update Frequency' },
  sources:     { zh: '信源列表',  en: 'Sources' },
  techStack:   { zh: '技术栈',    en: 'Tech Stack' },
  loading:     { zh: '加载中...', en: 'Loading...' },
  sourcesN:    { zh: '个信源',    en: 'sources' },
  healthy:     { zh: '个健康',    en: 'healthy' },
  sourceUnit:  { zh: '源',        en: 'sources' },
  normal:      { zh: '正常',      en: 'ok' },
  openSource:  { zh: '项目开源在', en: 'Open source on' },
  rssFeed:     { zh: 'RSS 订阅',  en: 'RSS Feed' },
  steps: [
    { zh_title: '采集 (Scanner)',   en_title: 'Scan (Scanner)',
      zh_desc: '每 6 小时从 16 个信源抓取 RSS/API，含 arXiv、顶级 AI 实验室博客、Hacker News、Reddit、中文技术媒体',
      en_desc: 'Every 6 hours, fetch from 16 sources via RSS/API — arXiv, top AI lab blogs, Hacker News, Reddit, Chinese tech media' },
    { zh_title: '去重 & 评分 (Dedup + Scorer)', en_title: 'Dedup & Score',
      zh_desc: '标题语义去重 + 四维打分：权威度、时效性、深度、相关性，每篇 0-100 分',
      en_desc: 'Semantic dedup + four-dimension scoring: authority, timeliness, depth, relevance. Each article scored 0-100' },
    { zh_title: '精选 & 翻译 (Curator)', en_title: 'Curate & Translate',
      zh_desc: 'LLM 从 Top 20 中精选 10-15 篇，生成中文标题、摘要和「为什么重要」解读',
      en_desc: 'LLM picks top 10-15 from 20 candidates, generates titles, summaries and "why it matters" analysis' },
    { zh_title: '发布 (Publisher)', en_title: 'Publish',
      zh_desc: '导出 JSON → 提交 GitHub → GitHub Pages 自动部署，全程 < 2 分钟',
      en_desc: 'Export JSON → commit to GitHub → GitHub Pages auto-deploy, all under 2 minutes' },
  ],
  freqItems: [
    { zh_label: '文章扫描：', en_label: 'Article Scan: ',     zh_v: '每 6 小时一次（00:00 / 06:00 / 12:00 / 18:00 UTC）', en_v: 'Every 6 hours (00:00 / 06:00 / 12:00 / 18:00 UTC)' },
    { zh_label: 'LLM 精选：', en_label: 'LLM Curation: ',    zh_v: '每次扫描后自动执行',  en_v: 'After every scan' },
    { zh_label: '周报：',     en_label: 'Weekly Report: ',    zh_v: '每周一生成，回顾过去 7 天重点', en_v: 'Every Monday, recaps the past 7 days' },
    { zh_label: 'GitHub Top 5：', en_label: 'GitHub Top 5: ', zh_v: '每日 08:30 更新',     en_v: 'Daily at 08:30' },
    { zh_label: '模型排行榜：',   en_label: 'Leaderboard: ',   zh_v: '每日随扫描更新',      en_v: 'Updated with every scan' },
  ],
  techItems: [
    { zh_label: '前端',           en_label: 'Frontend',      value: 'React 19 + TypeScript + Tailwind CSS v4 + Vite' },
    { zh_label: '图表',           en_label: 'Charts',        value: 'Recharts' },
    { zh_label: '后端 Pipeline',  en_label: 'Backend Pipeline', value: 'Python 3 + SQLite' },
    { zh_label: 'LLM',            en_label: 'LLM',           value: 'DeepSeek (curation) / swappable' },
    { zh_label: '部署',           en_label: 'Deployment',    value: 'GitHub Pages + Cloudflare DNS' },
    { zh_label: '定时任务',       en_label: 'Scheduler',     value: 'Hermes Cron (scan every 6h, weekly report every 24h)' },
  ],
  catLabels: {
    'AI Lab':     { zh: 'AI 实验室', en: 'AI Labs' },
    'Paper':      { zh: '学术论文',   en: 'Papers' },
    'Blog':       { zh: '技术博客',   en: 'Tech Blogs' },
    'Community':  { zh: '社区动态',   en: 'Community' },
    'Discussion': { zh: '技术讨论',   en: 'Discussion' },
    '中文媒体':    { zh: '中文媒体',   en: 'Chinese Media' },
  } as Record<string, { zh: string; en: string }>,
}

function tt(obj: { zh: string; en: string }, l: 'zh' | 'en') { return obj[l] }

export function AboutPage() {
  const [sources, setSources] = useState<SourceInfo[]>([])
  const [loading, setLoading] = useState(true)
  const { locale } = useLocale()

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
      <FadeIn>
        <div className="text-center py-6">
          <h1 className="text-3xl font-bold text-text-primary">{tt(T.aboutAllOfAI, locale)}</h1>
          <p className="mt-3 text-text-secondary max-w-xl mx-auto leading-relaxed">
            {tt(T.aboutDesc, locale)}
          </p>
        </div>
      </FadeIn>

      {/* Pipeline */}
      <FadeIn delay={0.05}>
        <section>
          <h2 className="text-xl font-semibold text-text-primary mb-5 flex items-center gap-2">
            <FontAwesomeIcon icon={ICON.gear} className="text-accent" />
            {tt(T.workflow, locale)}
          </h2>
          <div className="relative">
            <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-border-muted hidden md:block" />
            <div className="space-y-4">
              {T.steps.map((step, i) => (
                <div key={i} className="flex gap-4">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-accent-muted border border-accent/20 flex items-center justify-center z-10">
                    <FontAwesomeIcon icon={[ICON.satelliteDish, ICON.filter, ICON.robot, ICON.upload][i]} className="text-accent text-xs" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-medium text-text-primary text-sm">{locale === 'en' ? step.en_title : step.zh_title}</h3>
                    <p className="mt-1 text-sm text-text-secondary leading-relaxed">{locale === 'en' ? step.en_desc : step.zh_desc}</p>
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
            {tt(T.frequency, locale)}
          </h2>
          <div className="space-y-2 text-sm text-text-secondary">
            {T.freqItems.map((item, i) => (
              <p key={i}>
                <span className="text-text-primary font-medium">{locale === 'en' ? item.en_label : item.zh_label}</span>
                {locale === 'en' ? item.en_v : item.zh_v}
              </p>
            ))}
          </div>
        </div>
      </FadeIn>

      {/* Sources */}
      <FadeIn delay={0.15}>
        <section>
          <h2 className="text-xl font-semibold text-text-primary mb-1 flex items-center gap-2">
            <FontAwesomeIcon icon={ICON.satelliteDish} className="text-accent" />
            {tt(T.sources, locale)}
          </h2>
          <p className="text-sm text-text-muted mb-4">
            {loading ? tt(T.loading, locale)
              : `${sources.length} ${tt(T.sourcesN, locale)} · ${healthy} ${tt(T.healthy, locale)}`}
          </p>

          {loading ? (
            <div className="space-y-3"><CardSkeleton /><CardSkeleton /></div>
          ) : (
            <StaggerContainer className="space-y-5">
              {cats.map(cat => {
                const catSources = sources.filter(s => s.category === cat)
                if (!catSources.length) return null
                const catHealthy = catSources.filter(s => s.status === 'healthy').length
                const catLabel = T.catLabels[cat] || { zh: cat, en: cat }
                return (
                  <div key={cat}>
                    <h3 className="text-sm font-medium text-text-primary mb-2 flex items-center gap-2">
                      <FontAwesomeIcon icon={ICON.folder} className="text-text-muted text-xs" />
                      {tt(catLabel, locale)}
                      <span className="text-xs text-text-muted">
                        {catSources.length} {tt(T.sourceUnit, locale)} · {catHealthy} {tt(T.normal, locale)}
                      </span>
                    </h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                      {catSources.map(s => (
                        <div key={s.name} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-bg-secondary/50 text-sm">
                          <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                            s.status === 'healthy' ? 'bg-green' : s.status === 'degraded' ? 'bg-amber' : 'bg-red'
                          }`} />
                          <span className="text-text-primary truncate">{s.name}</span>
                          <span className="text-xs text-text-muted ml-auto flex-shrink-0">{s.article_count_last ?? 0}</span>
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
            {tt(T.techStack, locale)}
          </h2>
          <dl className="space-y-2 text-sm">
            {T.techItems.map(t => (
              <div key={t.value} className="flex gap-3">
                <dt className="text-text-muted w-28 flex-shrink-0">{locale === 'en' ? t.en_label : t.zh_label}</dt>
                <dd className="text-text-secondary">{t.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </FadeIn>

      <FadeIn delay={0.25}>
        <p className="text-center text-sm text-text-muted pb-8">
          {tt(T.openSource, locale)}{' '}
          <a href="https://github.com/badb0ttle/fine-grained" target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">GitHub</a>
          {' · '}
          <a href="/rss.xml" className="text-accent hover:underline">{tt(T.rssFeed, locale)}</a>
        </p>
      </FadeIn>
    </div>
  )
}
